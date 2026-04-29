"""
secure_reports.py
─────────────────
Replaces the plaintext .jsonl file with:
1. API key authentication (officers must have a key to submit/read reports)
2. SQLite database (proper querying, no data loss on append failures)
3. Report deduplication (same URL won't create 100 duplicate reports)
4. Rate limiting (prevents flooding the report endpoint)

TECHNICAL NOTE:
SQLite is a file-based SQL database — zero setup, no separate server process,
but supports full SQL queries, transactions, and indexing. For production,
swap the connection string to PostgreSQL (one line change with SQLAlchemy).

API Key auth uses HTTP Bearer tokens. In production, generate unique keys
per officer and store them hashed (bcrypt). For the prototype, we use a
single shared key defined in an environment variable.
"""

import hashlib
import json
import os
import sqlite3
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
DB_FILE        = Path("cyberguard_reports.db")
# In production: set this as an environment variable, never hardcode
API_KEY        = os.environ.get("CYBERGUARD_API_KEY", "nuh-police-2024-secret")
RATE_LIMIT_MAX = 20      # max reports per IP per hour
security       = HTTPBearer(auto_error=False)

# ── RATE LIMITER ──────────────────────────────────────────────────────────────
_rate_store: dict[str, list[float]] = defaultdict(list)

def check_rate_limit(client_ip: str):
    now    = time.time()
    window = 3600  # 1 hour
    hits   = [t for t in _rate_store[client_ip] if now - t < window]
    _rate_store[client_ip] = hits
    if len(hits) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 20 reports/hour.")
    _rate_store[client_ip].append(now)


# ── DATABASE SETUP ────────────────────────────────────────────────────────────
def init_db():
    """Create the reports table if it doesn't exist."""
    con = sqlite3.connect(DB_FILE)
    con.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id              TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            received_at     TEXT NOT NULL,
            reporter_name   TEXT,
            url             TEXT,
            url_hash        TEXT,          -- for deduplication
            page_title      TEXT,
            risk_score      INTEGER,
            verdict         TEXT,
            fraud_category  TEXT,
            flagged_keywords TEXT,         -- JSON string
            evidence_text   TEXT,
            comment         TEXT,
            status          TEXT DEFAULT 'FILED',
            reviewed_by     TEXT,
            reviewed_at     TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_url_hash  ON reports(url_hash)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_risk      ON reports(risk_score)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_status    ON reports(status)")
    con.commit()
    con.close()


def save_report_db(report: dict) -> str:
    """Save report to SQLite. Returns report ID."""
    init_db()
    con = sqlite3.connect(DB_FILE)

    report_id = "CG-" + uuid.uuid4().hex[:8].upper()
    url_hash  = hashlib.sha256(report.get("url", "").encode()).hexdigest()[:16]

    # Deduplication: if same URL reported in last 24h, return existing ID
    existing = con.execute(
        "SELECT id FROM reports WHERE url_hash=? AND datetime(received_at) > datetime('now', '-1 day')",
        (url_hash,)
    ).fetchone()

    if existing:
        con.close()
        return existing[0] + "-DUP"  # signal it's a duplicate

    con.execute("""
        INSERT INTO reports
        (id, timestamp, received_at, reporter_name, url, url_hash,
         page_title, risk_score, verdict, fraud_category,
         flagged_keywords, evidence_text, comment, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        report_id,
        report.get("timestamp", datetime.utcnow().isoformat()),
        datetime.utcnow().isoformat(),
        report.get("reporter_name", "Anonymous"),
        report.get("url", ""),
        url_hash,
        report.get("page_title", ""),
        report.get("risk_score", 0),
        report.get("verdict", ""),
        report.get("fraud_category", ""),
        json.dumps(report.get("flagged_keywords", {})),
        report.get("evidence_text", "")[:500],
        report.get("comment", ""),
        "FILED",
    ))
    con.commit()
    con.close()
    return report_id


def get_reports_db(limit: int = 50, min_risk: int = 0,
                   status: Optional[str] = None) -> list[dict]:
    """Query reports from SQLite with filters."""
    init_db()
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row

    query  = "SELECT * FROM reports WHERE risk_score >= ?"
    params = [min_risk]
    if status:
        query  += " AND status = ?"
        params.append(status)
    query += " ORDER BY received_at DESC LIMIT ?"
    params.append(limit)

    rows = con.execute(query, params).fetchall()
    con.close()

    result = []
    for row in rows:
        d = dict(row)
        try:
            d["flagged_keywords"] = json.loads(d["flagged_keywords"] or "{}")
        except Exception:
            d["flagged_keywords"] = {}
        result.append(d)
    return result


def get_stats_db() -> dict:
    """Return summary statistics for the police dashboard."""
    init_db()
    con = sqlite3.connect(DB_FILE)
    stats = {
        "total_reports":     con.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
        "high_risk":         con.execute("SELECT COUNT(*) FROM reports WHERE risk_score >= 70").fetchone()[0],
        "filed_today":       con.execute("SELECT COUNT(*) FROM reports WHERE date(received_at)=date('now')").fetchone()[0],
        "by_category":       dict(con.execute(
            "SELECT fraud_category, COUNT(*) FROM reports GROUP BY fraud_category"
        ).fetchall()),
        "avg_risk_score":    con.execute("SELECT AVG(risk_score) FROM reports").fetchone()[0] or 0,
    }
    con.close()
    stats["avg_risk_score"] = round(stats["avg_risk_score"], 1)
    return stats


# ── AUTH HELPER ───────────────────────────────────────────────────────────────
def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Validate Bearer token. Attach this as a dependency to protected endpoints.
    Usage:  @app.get("/reports", dependencies=[Depends(verify_api_key)])
    """
    if credentials is None or credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include 'Authorization: Bearer <key>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
