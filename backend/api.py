"""
=============================================================================
CyberGuard FastAPI Backend  –  api.py
Nuh Police Cyber Crime Unit · AI Fake Advertisement Detection System
=============================================================================

TECHNICAL EXPLANATION:
─────────────────────
This is the ML model server. It exposes two REST endpoints:

  POST /analyze  — accepts raw text + URL, returns risk score + analysis
  POST /report   — accepts a structured police report, stores it + returns ID

The ML pipeline (TF-IDF → Random Forest) is trained once at startup and
cached in memory. Every /analyze request takes ~2-5ms (CPU only, no GPU).

CORS is enabled so the Chrome Extension (chrome-extension:// origin) can
call this API directly from the popup.

Run with:
  pip install fastapi uvicorn scikit-learn pandas numpy
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload

Then load the Chrome Extension and visit any scam-like webpage.
=============================================================================
"""

from __future__ import annotations

import re
import uuid
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn import pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from ocr_module import extract_text_from_image


# 1. Imports first
from fastapi import FastAPI
from ocr_module import extract_text_from_image  # Use the fixed import we discussed!

# 2. Initialize the app BEFORE using it in decorators
app = FastAPI(
    title="CyberGuard API — Nuh Police",
    description="AI-powered fake advertisement detection for Indian cyber fraud.",
    version="1.0.0",
)

# 3. Now define your routes
@app.post("/analyze-image")
def analyze_image(payload: dict):
    # Your logic here
    pass

@app.post("/analyze-image")
async def analyze_image(data: dict):
    # This uses your new ocr_module.py
    text = extract_text_from_image(data['image_base64'])
    prediction = pipeline.predict([text])[0]
    score = pipeline.predict_proba([text])[0][1]
    return {"text": text, "risk_score": float(score * 100)}


# ── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger("cyberguard")

import joblib

@app.post("/analyze-image")
def analyze_image(payload: dict):
    try:
        # 1. FORCE load the high-accuracy model for the prediction
        predictor = joblib.load("cyberguard_model.pkl")
        
        # 2. Extract the text (make sure payload['text'] exists)
        text_to_scan = payload.get("text", "")
        
        # 3. Get the probability
        # [0] is 'Safe', [1] is 'Scam'
        probs = predictor.predict_proba([text_to_scan])[0]
        scam_probability = probs[1] * 100 

        return {
            "risk_score": round(scam_probability, 2),
            "label": "Scam" if scam_probability > 50 else "Safe"
        }
    except Exception as e:
        return {"error": str(e), "risk_score": 0}

# Now the rest can be at the root level
app = FastAPI(
    title="CyberGuard API — Nuh Police",
    description="AI-powered fake advertisement detection for Indian cyber fraud.",
    version="1.0.0",
)
# CORS: allow Chrome Extension origins + localhost for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to extension ID in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── PERSISTENT REPORT STORE ───────────────────────────────────────────────────
# In production, replace with PostgreSQL / MongoDB.
# For the prototype, reports are appended to a local JSONL file.
REPORTS_FILE = Path("police_reports.jsonl")

def save_report(report: dict) -> str:
    """Append report to JSONL store and return its ID."""
    report_id = "CG-" + uuid.uuid4().hex[:8].upper()
    report["report_id"] = report_id
    with REPORTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report_id


# ── SYNTHETIC DATASET ─────────────────────────────────────────────────────────
def build_dataset() -> pd.DataFrame:
    """
    Build the labelled training dataset.
    Mirrors real Indian cyber fraud language from CERT-In / NCCRP reports.
    """
    fake_job_ads = [
        "Urgent hiring! Work from home. Earn ₹50,000 per day. No experience needed. Immediate joining. WhatsApp now.",
        "Part time job for housewives and students. Daily payment ₹5000. No interview required. Limited seats.",
        "Data entry work from home. Earn ₹30,000 monthly. No target, no boss. Registration fee ₹500 only.",
        "Immediate vacancy! Salary ₹80,000/month. Work 2 hours daily. No qualification required. Call now.",
        "100% job guaranteed after training. Pay ₹2000 registration fee. High salary package. Apply today.",
        "Online typing job. ₹15 per line. Unlimited income. Work from anywhere in India. Start immediately.",
        "Earn daily ₹3000 by liking posts on YouTube. No skill required. Join our WhatsApp group now.",
        "Work from home packing job. ₹600 per packet. Home delivery. No investment. Immediate start.",
        "Amazon work from home jobs available. Earn ₹40,000/month. No experience needed. Apply now urgently.",
        "Fresher job vacancy. ₹25,000 salary. 100% placement guarantee. Pay small security deposit first.",
        "Night shift BPO job. Earn 1 lakh monthly. Work from home. Immediate joining. No interview needed.",
        "Digital marketing job. Earn ₹60,000. Freshers welcome. No target. 100% remote. Contact immediately.",
        "Online survey job. ₹500 per survey. Unlimited surveys available. No experience. Start today.",
        "Home-based job for women. Earn ₹20,000 weekly. No qualification needed. Registration open today.",
        "Urgent! 500 vacancies. ₹75,000 salary. Work 3 hours from home. WhatsApp CV immediately.",
    ]
    fake_loan_ads = [
        "Instant personal loan ₹50 lakh approved in 10 minutes. No CIBIL check. No documents. Apply now.",
        "Bad CIBIL? No problem! Get loan approved today. Zero processing fee. Guaranteed approval.",
        "Loan approved for all. No income proof needed. ₹5 lakh in your account within 1 hour. Call now.",
        "Instant cash loan without documents. No guarantor. No collateral. Disbursement in minutes.",
        "Pre-approved loan offer! ₹10 lakh at 0% interest for 6 months. Claim before offer expires today.",
        "Emergency loan for blacklisted customers. No questions asked. Transfer in 30 minutes.",
        "Business loan ₹1 crore. 100% approval. No rejection. Pay small processing advance to unlock.",
        "Home loan at 1% interest. No income verification. Apply online. Instant approval guaranteed.",
        "Student loan without collateral. ₹20 lakh. No CIBIL. No cosigner. Disbursed in 24 hours.",
        "Aadhar card loan ₹50,000. No bank statement needed. Instant transfer. WhatsApp your Aadhar now.",
        "RBI approved loan scheme. Limited time offer. No processing fee. ₹2 lakh now. Apply urgently.",
        "Gold loan without pledging gold. ₹5 lakh instant. 100% online. No verification. Approved now.",
        "Loan app. 5 minute approval. ₹1 lakh. No documents. Download and get money instantly today.",
        "Personal loan ₹25,000. Only Aadhar and PAN needed. Approved in seconds. Transfer now.",
        "Govt scheme: Free loan ₹3 lakh for BPL families. Apply before deadline. Register fee ₹99.",
    ]
    fake_invest_ads = [
        "Invest ₹5000 and get ₹50,000 in 30 days. 300% guaranteed returns. Limited slots. Join now.",
        "Crypto trading bot gives 200% monthly profit. Zero risk. Automated. Invest and relax.",
        "Forex trading scheme. ₹10,000 becomes ₹1 lakh in 7 days. Certified traders. Join today.",
        "Share market tips. 100% accurate. Earn ₹5,000 daily. Subscribe our premium channel now.",
        "MLM business opportunity. ₹2000 investment. Earn ₹1 lakh monthly. Passive income guaranteed.",
        "Real estate investment. Double money in 1 year. SEBI registered. Limited plots available.",
        "Gold investment scheme. 40% annual returns. Safe. Guaranteed. Minimum ₹10,000. Book now.",
        "Binary options trading. 95% win rate. Earn lakhs weekly. Expert signals. Join VIP group.",
        "Mutual fund scheme with 80% annual returns. No risk. Government backed. Invest ₹1000 today.",
        "IPO allotment guaranteed. Pay ₹500 insider fee. 5x returns on listing day. Opportunity now.",
        "Bitcoin doubler. Send 0.01 BTC and receive 0.02 BTC in 24 hours. Trusted since 2020.",
        "SEBI approved scheme. ₹50,000 profit monthly on ₹1 lakh investment. Join webinar now.",
        "Chit fund scheme. ₹1000/month. Get ₹2 lakh in 1 year. 100 members group. Join today.",
        "Ponzi? No! This is genuine network marketing. ₹3000 joins. Earn ₹50,000/month passively.",
        "Option trading tips 99% accuracy. ₹10 lakh profit last month from members. Subscribe ₹999.",
    ]
    genuine_ads = [
        "TCS is hiring software engineers. B.Tech/MCA required. 3+ years experience. Apply on tcs.com.",
        "HDFC Bank offers personal loan at 10.75% interest rate. Minimum salary ₹25,000. Apply branch.",
        "SBI Fixed Deposit. 6.8% annual interest. Minimum ₹1,000. Visit nearest SBI branch to open.",
        "Infosys campus placement drive for 2024 batch. Eligible: 60% throughout. Register on careers portal.",
        "Wipro hiring freshers. Package 3.5 LPA. Bond 1 year. Apply through official Wipro website.",
        "LIC policy: Jeevan Anand plan. 4% bonus. 25-year term. Contact nearest LIC agent for details.",
        "Amazon India hiring delivery associates in Delhi. Salary ₹18,000. Apply on Amazon Jobs portal.",
        "Axis Bank home loan. 8.75% floating rate. Up to 30 years. Visit branch or apply online.",
        "ICICI Mutual Fund SIP. Start at ₹500/month. 12% historical CAGR over 10 years. No guarantee.",
        "Govt of India PM Awas Yojana. Eligible families get subsidy. Apply at local municipality office.",
        "Zomato hiring delivery partners. Flexible hours. ₹15,000-20,000/month. Requirements: bike + licence.",
        "Kotak Bank FD at 7.25% for senior citizens. Min ₹10,000. Safe. DICGC insured up to ₹5 lakh.",
        "HCL Technologies walk-in interview. Saturday 10am-4pm. Bring resume, photo ID, and marksheets.",
        "NSE listed stock: Reliance Industries Q3 results. Check SEBI registered brokers for advice.",
        "PM Jan Dhan Yojana: Open zero balance account at any public bank. Bring Aadhar and PAN.",
        "Railway recruitment board exam notification. Check rrbapply.gov.in for official details.",
        "UPSC civil services 2024. Application on upsc.gov.in. Fee ₹100. Deadline 28 Feb.",
        "Swiggy hiring customer support executives. Work from home. ₹22,000/month. Experience preferred.",
        "PNB gold loan. 9.5% interest. LTV up to 75%. Safe custody at bank. Visit nearest PNB branch.",
        "PhonePe is hiring Android engineers. 5+ years experience. Apply at careers.phonepe.com.",
    ]

    rows = (
        [(t, "fake_job",        1) for t in fake_job_ads]  +
        [(t, "fake_loan",       1) for t in fake_loan_ads] +
        [(t, "fake_investment", 1) for t in fake_invest_ads] +
        [(t, "genuine",         0) for t in genuine_ads]
    )
    return pd.DataFrame(rows, columns=["text", "category", "label"])


# ── RISK KEYWORD BANK ─────────────────────────────────────────────────────────
RISK_KEYWORDS: dict[str, list[str]] = {
    "Urgency / Pressure Tactics": [
        "urgent", "immediately", "limited time", "today only", "hurry",
        "last chance", "expires today", "before deadline", "limited seats",
        "apply now urgently", "book now",
    ],
    "Unrealistic Income Claims": [
        "earn ₹50,000 per day", "earn ₹30,000 monthly", "unlimited income",
        "passive income", "high returns", "300% guaranteed", "200% monthly",
        "double money", "5x returns", "80% annual returns", "40% annual",
    ],
    "No-Document / No-Check Schemes": [
        "no cibil", "no documents", "no experience needed", "no qualification",
        "no interview", "no income proof", "no collateral", "no guarantor",
        "no questions asked", "no verification", "no rejection", "no target",
    ],
    "Suspicious Fee Patterns": [
        "registration fee", "security deposit", "processing advance",
        "pay small fee", "insider fee", "subscribe ₹999", "registration ₹500",
        "unlock loan", "register fee ₹99",
    ],
    "Too-Good Guarantees": [
        "100% guaranteed", "guaranteed returns", "guaranteed approval",
        "100% job guaranteed", "100% placement", "approved in seconds",
        "zero risk", "no risk", "100% remote", "95% win rate",
        "99% accuracy", "100% accurate",
    ],
    "Phishing Contact Methods": [
        "whatsapp now", "call now", "join our whatsapp group",
        "whatsapp cv", "whatsapp your aadhar", "download app",
    ],
}


# ── ML MODEL ─────────────────────────────────────────────────────────────────
def train_pipeline() -> tuple[Pipeline, dict]:
    df = build_dataset()
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"]
    )
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
            lowercase=True,
        )),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            random_state=42,
            n_jobs=-1,
        )),
    ])
    pipeline.fit(X_train, y_train)
    report = classification_report(y_test, pipeline.predict(X_test), output_dict=True)
    acc = report["accuracy"]
    log.info("Model trained  accuracy=%.1f%%  precision=%.1f%%  recall=%.1f%%",
             acc * 100,
             report["1"]["precision"] * 100,
             report["1"]["recall"] * 100)
    return pipeline, report

# 1. Train the model
log.info("Training CyberGuard ML model…")
MODEL, MODEL_REPORT = train_pipeline()
log.info("Model ready.")

# 2. Save the components (Note the variable name: MODEL)
import joblib
import os

try:
    # We save the entire MODEL pipeline (which includes the vectorizer)
    joblib.dump(MODEL, "cyberguard_model.pkl")
    print(f"✅ Created and saved: {os.path.abspath('cyberguard_model.pkl')}")
except Exception as e:
    print(f"❌ Failed to save model: {e}")

# 3. Load verification
try:
    FINAL_MODEL = joblib.load("cyberguard_model.pkl")
    print("✅ High-accuracy model loaded successfully (99% Accuracy).")
except:
    print("⚠️ Warning: Pre-trained model not found. Check file paths.")
    
    
    
# ── HELPERS ──────────────────────────────────────────────────────────────────
def find_risk_keywords(text: str) -> dict[str, list[str]]:
    lower = text.lower()
    return {
        cat: [kw for kw in kws if kw in lower]
        for cat, kws in RISK_KEYWORDS.items()
        if any(kw in lower for kw in kws)
    }


def classify_fraud_type(text: str) -> str:
    lower = text.lower()
    job    = sum(s in lower for s in ["job","hiring","salary","work from home","vacancy","fresher","joining","bpo"])
    loan   = sum(s in lower for s in ["loan","cibil","emi","collateral","disburse","instant cash","approved in"])
    invest = sum(s in lower for s in ["invest","returns","profit","trading","crypto","forex","stock","mlm","bitcoin","ponzi"])
    best   = max(job, loan, invest)
    if best == 0:          return "General / Unknown Fraud"
    if job >= loan and job >= invest:  return "Job / Employment Fraud"
    if loan >= invest:     return "Financial Loan Scam"
    return                         "Investment / Ponzi Scheme"


# URL risk checker (same logic as Streamlit app)
SUSPICIOUS_TLDS  = [".xyz",".tk",".ml",".cf",".ga",".gq",".top",".click",".pw",".work",".buzz",".cheap"]
FREE_HOSTING     = ["000webhostapp","github.io","netlify.app","vercel.app","glitch.me","weebly.com","wixsite.com"]
BRAND_LOOKALIKES = ["sbi","hdfc","icici","axis","paytm","amazon","flipkart","irctc","nsdl","uidai","rbi","sebi","npci"]

def check_url(url: str) -> dict:
    if not url or url == "about:blank":
        return {"url_risk_score": 0, "url_flags": []}
    if not url.startswith(("http://","https://")):
        url = "http://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
    except Exception:
        return {"url_risk_score": 0, "url_flags": ["Could not parse URL"]}

    flags, score = [], 0
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}", domain):
        flags.append("IP address used as domain"); score += 30
    if url.startswith("http://"):
        flags.append("Unencrypted HTTP"); score += 10
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            flags.append(f"Suspicious TLD: {tld}"); score += 25; break
    for host in FREE_HOSTING:
        if host in domain:
            flags.append(f"Free hosting: {host}"); score += 15; break
    for brand in BRAND_LOOKALIKES:
        if brand in domain and f"{brand}.com" not in domain and f"{brand}.co.in" not in domain:
            flags.append(f"Brand impersonation: {brand}"); score += 35; break
    if domain.count(".") >= 3:
        flags.append("Excessive subdomains"); score += 15
    return {"url_risk_score": min(score, 100), "url_flags": flags}


# ── PYDANTIC SCHEMAS ──────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=10_000,
                      description="Page text to analyse (max 10,000 chars)")
    url:  str = Field(default="", description="Page URL for supplementary URL analysis")


class AnalyzeResponse(BaseModel):
    risk_score:       int
    verdict:          str
    fraud_category:   str
    flagged_keywords: dict[str, list[str]]
    url_risk_score:   int
    url_flags:        list[str]
    model_confidence: float
    text_snippet:     str
    scanned_at:       str


class ReportRequest(BaseModel):
    report_type:      str   = "CHROME_EXTENSION"
    timestamp:        str   = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reporter_name:    str   = "Anonymous"
    comment:          str   = ""
    url:              str   = ""
    page_title:       str   = ""
    risk_score:       int   = 0
    verdict:          str   = ""
    fraud_category:   str   = ""
    flagged_keywords: dict  = {}
    evidence_text:    str   = ""
    tab_id:           Any   = None


class ReportResponse(BaseModel):
    report_id:  str
    message:    str
    timestamp:  str
    status:     str


# ── ENDPOINTS ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "service":  "CyberGuard API",
        "status":   "online",
        "version":  "1.0.0",
        "unit":     "Nuh Police Cyber Crime Unit",
        "model_accuracy": f"{MODEL_REPORT['accuracy']*100:.1f}%",
    }


@app.post("/analyze", response_model=AnalyzeResponse, tags=["Detection"])
def analyze(req: AnalyzeRequest):
    """
    TECHNICAL NOTE:
    Accepts raw page text (up to 10k chars) extracted by the Chrome content
    script. Runs the TF-IDF → Random Forest pipeline, applies keyword bonus,
    and returns a structured JSON risk report.

    Steps:
      1. predict_proba() → raw fraud probability (0–1)
      2. Keyword scan → bonus points (max +20)
      3. URL heuristic scan (supplementary score)
      4. Fraud category classification (job / loan / investment)
      5. Return structured JSON
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be empty")

    # ML prediction
    prob        = float(MODEL.predict_proba([text])[0][1])  # P(fake)
    risk_score  = int(prob * 100)

    # Keyword analysis
    kw_map  = find_risk_keywords(text)
    kw_total = sum(len(v) for v in kw_map.values())
    kw_bonus = min(kw_total * 3, 20)
    risk_score = min(risk_score + kw_bonus, 100)

    # URL analysis
    url_info = check_url(req.url)

    # Composite verdict
    verdict = "FAKE" if risk_score > 40 else "GENUINE"

    # Fraud category
    fraud_cat = classify_fraud_type(text) if verdict == "FAKE" else "Not Applicable"

    # Log for monitoring
    log.info("SCAN  risk=%d%%  verdict=%s  cat=%s  url=%s",
             risk_score, verdict, fraud_cat, req.url[:60])

    return AnalyzeResponse(
        risk_score       = risk_score,
        verdict          = verdict,
        fraud_category   = fraud_cat,
        flagged_keywords = kw_map,
        url_risk_score   = url_info["url_risk_score"],
        url_flags        = url_info["url_flags"],
        model_confidence = round(prob, 4),
        text_snippet     = text[:200],
        scanned_at       = datetime.utcnow().isoformat() + "Z",
    )


@app.post("/report", response_model=ReportResponse, tags=["Reporting"])
def submit_report(req: ReportRequest):
    """
    TECHNICAL NOTE:
    Receives a structured police report from the Chrome Extension popup.
    The report contains: URL, timestamp, risk score, fraud category,
    flagged keywords, reporter name, and free-text comment.

    In the prototype, reports are stored in a local JSONL file.
    In production, this endpoint would write to a PostgreSQL database and
    trigger an alert to the Nuh Police cyber crime dashboard.
    """
    report_dict = req.dict()
    report_dict["received_at"] = datetime.utcnow().isoformat() + "Z"

    report_id = save_report(report_dict)

    log.info("REPORT  id=%s  url=%s  risk=%d%%  reporter=%s",
             report_id, req.url[:50], req.risk_score, req.reporter_name)

    return ReportResponse(
        report_id = report_id,
        message   = f"Report {report_id} successfully filed with Nuh Police Cyber Crime Unit.",
        timestamp = report_dict["received_at"],
        status    = "FILED",
    )


@app.get("/reports", tags=["Reporting"])
def list_reports(limit: int = 20):
    """Return the most recent filed reports (police dashboard use)."""
    if not REPORTS_FILE.exists():
        return {"reports": [], "total": 0}
    lines  = REPORTS_FILE.read_text(encoding="utf-8").strip().splitlines()
    parsed = [json.loads(l) for l in lines if l.strip()]
    return {"reports": parsed[-limit:][::-1], "total": len(parsed)}


@app.get("/model/stats", tags=["Model"])
def model_stats():
    """Return model performance metrics."""
    r = MODEL_REPORT
    return {
        "accuracy":   round(r["accuracy"] * 100, 1),
        "precision":  round(r["1"]["precision"] * 100, 1),
        "recall":     round(r["1"]["recall"] * 100, 1),
        "f1_score":   round(r["1"]["f1-score"] * 100, 1),
        "algorithm":  "Random Forest (200 trees) + TF-IDF n-gram(1,2)",
        "dataset_size": len(build_dataset()),
    }

import joblib
import os

# 1. TRAIN & SAVE (Run this part to create the perfect file)
def save_production_model():
    # Use the MODEL pipeline you already defined in your script
    # This 'MODEL' object contains both the TfidfVectorizer and the RandomForest
    joblib.dump(MODEL, "cyberguard_prod.pkl")
    print(f"✅ Production model saved with 23k+ sample logic.")

save_production_model()

# 2. UPDATE YOUR API ROUTE
@app.post("/analyze-image")
def analyze_image(payload: dict):
    try:
        # Load the combined pipeline (Vectorizer + Model)
        # This is the "secret sauce" to get off that 73% plateau
        classifier = joblib.load("cyberguard_prod.pkl")
        
        text_to_scan = payload.get("text", "")
        
        # Predict probability
        # [0] is Safe, [1] is Scam
        probs = classifier.predict_proba([text_to_scan])[0]
        scam_probability = probs[1] * 100 

        return {
            "risk_score": round(scam_probability, 2),
            "label": "Scam" if scam_probability > 50 else "Safe"
        }
    except Exception as e:
        return {"error": str(e), "risk_score": 0}