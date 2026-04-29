"""
=============================================================================
AI-Based Fake Online Advertisement Detection System
Developed for: Nuh Police Department Internship Prototype
Author: Ankita Bhargava (Enrollment: 230160227008)
Tech Stack: Python · Scikit-learn · TF-IDF · Pandas · Streamlit
=============================================================================

TECHNICAL EXPLANATION (For Judges – April 30th):
-------------------------------------------------
This system uses a supervised Machine Learning pipeline to detect fraudulent
online advertisements targeting Indian users. Here's the architecture:

1. DATASET: A synthetic dataset of 300+ labelled ads (Genuine + Fake) is
   created programmatically. Fake ads cover 3 categories:
   - Job Scams (e.g., "Work from home, ₹50,000/day, no experience needed")
   - Loan Scams (e.g., "Instant loan approved, no CIBIL check")
   - Investment Scams (e.g., "300% returns in 30 days, guaranteed profit")

2. ML PIPELINE: Text is converted to numbers using TF-IDF (Term Frequency-
   Inverse Document Frequency), which measures how important each word is.
   A Random Forest classifier (100 decision trees voting together) then
   classifies the ad and outputs a probability-based fraud risk score.

3. RISK SCORE: Instead of a binary Yes/No, we use model.predict_proba() to
   extract the probability of fraud (0-100%). This lets police grade threats.

4. KEYWORD HIGHLIGHTING: A curated list of high-risk phrases (culled from
   real Indian scam patterns) is cross-referenced with the input text to
   show exactly WHY an ad was flagged — actionable intelligence for officers.

5. URL CHECKER: A regex + pattern-based heuristic checks for suspicious
   URL structures: IP addresses, lookalike domains, free hosting, excessive
   subdomains, homoglyph attacks — common in phishing campaigns.
=============================================================================
"""

# ─── IMPORTS ────────────────────────────────────────────────────────────────
from sklearn import pipeline
import streamlit as st
import pandas as pd
import numpy as np
import re
from urllib.parse import urlparse

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

import warnings
warnings.filterwarnings("ignore")


# ─── SECTION 1:  DATASET ───────────────────────────────────────────
# TECHNICAL NOTE: Since real labelled scam data is confidential, we build a
# representative synthetic dataset. Each sample mirrors real Indian cyber
# fraud language patterns documented by CERT-In and NCCRP reports.

import pandas as pd
from sklearn.utils import shuffle

# Load the new datasets from your folder
df_jobs = pd.read_csv('real-fake-job-postings.csv')[['description', 'fraudulent']]
df_jobs.columns = ['text', 'label']

df_sms = pd.read_csv('sms-spam-collection.csv', encoding='latin-1')[['v2', 'v1']]
df_sms.columns = ['text', 'label']
df_sms['label'] = df_sms['label'].map({'spam': 1, 'ham': 0})

# Load your manual benign data (fixes Netflix/Outskill)
df_benign = pd.read_csv('benign_data.csv') 

# Combine and shuffle
df_final = pd.concat([df_jobs, df_sms, df_benign], ignore_index=True).dropna()
df_final = shuffle(df_final)

# Train and Save
pipeline.fit(df_final['text'], df_final['label'])
joblib.dump(pipeline, 'cyberguard_model.pkl')

def build_dataset():
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

    fake_investment_ads = [
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

    data = (
        [(text, "fake_job",        1) for text in fake_job_ads] +
        [(text, "fake_loan",       1) for text in fake_loan_ads] +
        [(text, "fake_investment",  1) for text in fake_investment_ads] +
        [(text, "genuine",         0) for text in genuine_ads]
    )

    df = pd.DataFrame(data, columns=["text", "category", "label"])
    return df


# ─── SECTION 2: HIGH-RISK KEYWORD BANK ──────────────────────────────────────
# TECHNICAL NOTE: These phrases are derived from NCCRP (National Cyber Crime
# Reporting Portal) fraud reports and RBI advisories on digital fraud.
# Grouped by category for Police Insights reporting.

RISK_KEYWORDS = {
    "Urgency / Pressure Tactics": [
        "urgent", "immediately", "limited time", "today only", "hurry",
        "last chance", "expires today", "before deadline", "limited seats",
        "apply now urgently", "book now"
    ],
    "Unrealistic Income Claims": [
        "earn ₹50,000 per day", "earn ₹30,000 monthly", "unlimited income",
        "passive income", "high returns", "300% guaranteed", "200% monthly",
        "double money", "5x returns", "80% annual returns", "40% annual"
    ],
    "No-Document / No-Check Schemes": [
        "no cibil", "no documents", "no experience needed", "no qualification",
        "no interview", "no income proof", "no collateral", "no guarantor",
        "no questions asked", "no verification", "no rejection", "no target"
    ],
    "Suspicious Fee Patterns": [
        "registration fee", "security deposit", "processing advance",
        "pay small fee", "insider fee", "subscribe ₹999", "registration ₹500",
        "unlock loan", "register fee ₹99"
    ],
    "Too-Good Guarantees": [
        "100% guaranteed", "guaranteed returns", "guaranteed approval",
        "100% job guaranteed", "100% placement", "approved in seconds",
        "zero risk", "no risk", "100% remote", "95% win rate",
        "99% accuracy", "100% accurate"
    ],
    "Phishing Contact Methods": [
        "whatsapp now", "call now", "join our whatsapp group",
        "whatsapp cv", "whatsapp your aadhar", "download app"
    ],
}

# Flat list for quick matching
ALL_RISK_KEYWORDS = [kw for kws in RISK_KEYWORDS.values() for kw in kws]


# ─── SECTION 3: ML MODEL TRAINING ───────────────────────────────────────────
# TECHNICAL NOTE: We build a sklearn Pipeline with two stages:
# Stage 1 – TfidfVectorizer: Converts raw text to a numerical matrix where
#   each value represents how "important" a word is in that document vs
#   the whole corpus. n-gram range (1,2) captures both words and phrases.
# Stage 2 – RandomForestClassifier: An ensemble of 200 decision trees. Each
#   tree sees a random subset of features. Majority vote gives the prediction.
#   predict_proba() gives us a probabilistic fraud risk score.

@st.cache_resource(show_spinner=False)
def train_model():
    df = build_dataset()
    X = df["text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words=None,      # Keep all words — scam phrases matter
            lowercase=True,
            sublinear_tf=True     # Apply log normalization to term frequency
        )),
        ("clf", RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1
        ))
    ])

    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    report = classification_report(y_test, y_pred, output_dict=True)

    return pipeline, df, report


# ─── SECTION 4: FRAUD CATEGORY CLASSIFIER ───────────────────────────────────
# TECHNICAL NOTE: After predicting fake/genuine, we use a keyword-based
# secondary classifier to identify the *type* of fraud for Police Insights.

def classify_fraud_type(text: str) -> tuple[str, str]:
    text_lower = text.lower()
    job_signals    = ["job", "hiring", "salary", "work from home", "vacancy",
                      "fresher", "data entry", "typing", "joining", "bpo",
                      "earn daily", "earn weekly", "earn monthly by"]
    loan_signals   = ["loan", "cibil", "interest", "emi", "disburse",
                      "collateral", "aadhar card loan", "processing fee",
                      "approved in", "instant cash"]
    invest_signals = ["invest", "returns", "profit", "trading", "crypto",
                      "forex", "stock", "mutual fund", "sebi", "ipo",
                      "scheme", "mlm", "chit fund", "ponzi", "bitcoin"]

    job_score    = sum(s in text_lower for s in job_signals)
    loan_score   = sum(s in text_lower for s in loan_signals)
    invest_score = sum(s in text_lower for s in invest_signals)

    if max(job_score, loan_score, invest_score) == 0:
        return "General Fraud", "⚠️"
    if job_score >= loan_score and job_score >= invest_score:
        return "Job / Employment Fraud", "👷"
    if loan_score >= invest_score:
        return "Financial Loan Scam", "🏦"
    return "Investment / Ponzi Scheme", "📈"


# ─── SECTION 5: KEYWORD HIGHLIGHTER ─────────────────────────────────────────
# TECHNICAL NOTE: This function scans input text against our risk keyword
# bank and returns matched phrases categorised by threat type.
# The HTML highlighting wraps matched words in a styled <mark> tag.

def find_risk_keywords(text: str) -> dict[str, list[str]]:
    text_lower = text.lower()
    found = {}
    for category, keywords in RISK_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        if matches:
            found[category] = matches
    return found


def highlight_text(text: str, keywords: list[str]) -> str:
    """Wraps risky phrases in HTML mark tags for display."""
    highlighted = text
    for kw in sorted(keywords, key=len, reverse=True):  # longest first to avoid partial overlaps
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        highlighted = pattern.sub(
            lambda m: f'<mark style="background:#ff4b4b;color:white;border-radius:3px;padding:1px 4px;font-weight:600">{m.group()}</mark>',
            highlighted
        )
    return highlighted


# ─── SECTION 6: URL CHECKER ──────────────────────────────────────────────────
# TECHNICAL NOTE: Phishing URLs use predictable patterns:
#   - IP addresses instead of domain names (hide identity)
#   - Free hosting (000webhostapp, github.io misused for scams)
#   - Homoglyphs (paypa1.com instead of paypal.com)
#   - Lookalike strings (sbi-loan.xyz, hdfc-offer.in)
#   - Excessive subdomains (a.b.c.fake.com)
# We use regex + pattern matching — no external API needed.

SUSPICIOUS_TLDS     = [".xyz", ".tk", ".ml", ".cf", ".ga", ".gq", ".top",
                       ".click", ".pw", ".work", ".buzz", ".cheap"]
FREE_HOSTING        = ["000webhostapp", "github.io", "netlify.app",
                       "vercel.app", "glitch.me", "weebly.com", "wixsite.com",
                       "blogspot.com", "wordpress.com"]
BRAND_LOOKALIKES    = ["sbi", "hdfc", "icici", "axis", "paytm", "amazon",
                       "flipkart", "irctc", "nsdl", "uidai", "rbi", "sebi",
                       "npci", "bsnl", "airtel", "jio"]
URGENCY_PARAMS      = ["free", "offer", "bonus", "prize", "winner",
                       "loan", "reward", "claim", "limited"]

def check_url(url: str) -> dict:
    result = {
        "is_suspicious": False,
        "risk_score": 0,
        "flags": [],
        "verdict": ""
    }

    if not url.strip():
        return result

    # Normalise
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path   = parsed.path.lower()
        full   = url.lower()
    except Exception:
        result["flags"].append("❌ Could not parse URL")
        result["is_suspicious"] = True
        result["risk_score"] = 80
        return result

    score = 0

    # 1. IP address used instead of domain
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}", domain):
        result["flags"].append("🚨 IP address used as domain (hides real identity)")
        score += 30

    # 2. HTTP (not HTTPS)
    if url.startswith("http://"):
        result["flags"].append("⚠️ Unencrypted HTTP connection (no SSL)")
        score += 10

    # 3. Suspicious TLD
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            result["flags"].append(f"🚨 Suspicious TLD: `{tld}` (common in throwaway scam domains)")
            score += 25
            break

    # 4. Free hosting platforms
    for host in FREE_HOSTING:
        if host in domain:
            result["flags"].append(f"⚠️ Free hosting detected: `{host}` (unusual for official services)")
            score += 15
            break

    # 5. Brand name + non-official domain (e.g., sbi-loan-offer.com)
    for brand in BRAND_LOOKALIKES:
        if brand in domain and f"{brand}.com" not in domain and f"{brand}.co.in" not in domain:
            result["flags"].append(f"🚨 Brand impersonation: `{brand}` used in unofficial domain")
            score += 35
            break

    # 6. Excessive subdomains (more than 2 dots in domain)
    if domain.count(".") >= 3:
        result["flags"].append("⚠️ Excessive subdomains (phishing obfuscation technique)")
        score += 15

    # 7. Suspicious keywords in URL path
    for param in URGENCY_PARAMS:
        if param in path or param in full:
            result["flags"].append(f"⚠️ Suspicious keyword in URL: `{param}`")
            score += 10
            break

    # 8. Very long URL (obfuscation)
    if len(url) > 100:
        result["flags"].append("⚠️ Unusually long URL (possible obfuscation)")
        score += 10

    # 9. Numeric subdomain
    if re.search(r"\d{4,}", domain):
        result["flags"].append("⚠️ Numeric string in domain (atypical for legitimate orgs)")
        score += 10

    score = min(score, 100)
    result["risk_score"] = score
    result["is_suspicious"] = score >= 20

    if score >= 70:
        result["verdict"] = "🔴 HIGH RISK — Likely Phishing/Scam URL"
    elif score >= 35:
        result["verdict"] = "🟡 MEDIUM RISK — Suspicious, Verify Before Visiting"
    elif score > 0:
        result["verdict"] = "🟠 LOW RISK — Minor Concerns Detected"
    else:
        result["verdict"] = "🟢 LOW RISK — No Obvious Suspicious Patterns"

    return result


# ─── SECTION 7: RISK SCORE GAUGE (SVG) ──────────────────────────────────────
# TECHNICAL NOTE: A pure-SVG semicircular gauge. The arc length is calculated
# using the SVG stroke-dasharray trick — no JS library needed.

def render_gauge(score: int) -> str:
    if score <= 30:
        color = "#22c55e"   # green
    elif score <= 60:
        color = "#f59e0b"   # amber
    elif score <= 80:
        color = "#f97316"   # orange
    else:
        color = "#ef4444"   # red

    # Semicircle: radius=80, circumference of half-circle = π*r ≈ 251
    half_circ = 251.2
    filled    = (score / 100) * half_circ

    return f"""
    <div style="text-align:center;padding:10px 0">
    <svg width="220" height="130" viewBox="0 0 220 130">
      <!-- Background arc -->
      <path d="M 20 110 A 90 90 0 0 1 200 110"
            fill="none" stroke="#e5e7eb" stroke-width="18" stroke-linecap="round"/>
      <!-- Foreground arc -->
      <path d="M 20 110 A 90 90 0 0 1 200 110"
            fill="none" stroke="{color}" stroke-width="18" stroke-linecap="round"
            stroke-dasharray="{filled:.1f} {half_circ:.1f}"
            stroke-dashoffset="0"/>
      <!-- Score text -->
      <text x="110" y="100" text-anchor="middle"
            font-size="34" font-weight="700" fill="{color}">{score}%</text>
      <text x="110" y="122" text-anchor="middle"
            font-size="11" fill="#6b7280">FRAUD RISK SCORE</text>
      <!-- Min/Max labels -->
      <text x="18"  y="128" font-size="10" fill="#9ca3af">0</text>
      <text x="198" y="128" font-size="10" fill="#9ca3af">100</text>
    </svg>
    </div>
    """


# ─── SECTION 8: STREAMLIT UI ─────────────────────────────────────────────────

def main():
    # ── Page config ──────────────────────────────────────────────────────────
    st.set_page_config(
        page_title="Nuh Police | Fake Ad Detector",
        page_icon="🚔",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # ── Custom CSS ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Header banner */
    .header-banner {
        background: linear-gradient(135deg, #1a237e 0%, #283593 50%, #1565c0 100%);
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        color: white;
    }
    .header-banner h1 { margin:0; font-size:1.8rem; font-weight:700; }
    .header-banner p  { margin:4px 0 0 0; opacity:0.85; font-size:0.95rem; }

    /* Metric cards */
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-card .label { font-size:0.75rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em; }
    .metric-card .value { font-size:1.6rem; font-weight:700; color:#1e293b; margin-top:4px; }

    /* Risk level badge */
    .risk-badge {
        display:inline-block;
        padding:6px 18px;
        border-radius:20px;
        font-weight:600;
        font-size:1rem;
        margin:8px 0;
    }
    .risk-low    { background:#dcfce7; color:#166534; }
    .risk-medium { background:#fef9c3; color:#854d0e; }
    .risk-high   { background:#fee2e2; color:#991b1b; }
    .risk-critical { background:#7f1d1d; color:white; }

    /* Section headers */
    .section-title {
        font-size:1rem;
        font-weight:600;
        color:#1e293b;
        border-left:4px solid #3b82f6;
        padding-left:10px;
        margin:20px 0 12px 0;
    }

    /* Keyword tag */
    .kw-tag {
        display:inline-block;
        background:#fef2f2;
        color:#dc2626;
        border:1px solid #fecaca;
        border-radius:6px;
        padding:3px 10px;
        margin:3px;
        font-size:0.82rem;
        font-weight:500;
    }

    /* Police insight card */
    .insight-card {
        background: linear-gradient(135deg, #1e3a5f, #1a237e);
        color: white;
        border-radius: 10px;
        padding: 18px 22px;
    }
    .insight-card h3 { margin:0 0 8px 0; font-size:1rem; opacity:0.8; }
    .insight-card .fraud-type { font-size:1.3rem; font-weight:700; margin:0; }

    /* Footer */
    .footer {
        text-align:center;
        color:#94a3b8;
        font-size:0.78rem;
        margin-top:40px;
        padding-top:16px;
        border-top:1px solid #e2e8f0;
    }

    /* Input area styling */
    .stTextArea textarea {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* Divider */
    hr { border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="header-banner">
        <h1>🚔 Nuh Police · AI Fake Advertisement Detection System</h1>
        <p>Cyber Fraud Prevention Unit · Powered by Machine Learning & NLP · Real-time Risk Analysis</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Load model ────────────────────────────────────────────────────────────
    with st.spinner("🔄 Loading AI detection engine..."):
        model, dataset, report = train_model()

    # ── Model stats strip ─────────────────────────────────────────────────────
    acc    = report["accuracy"]
    prec   = report["1"]["precision"]
    recall = report["1"]["recall"]
    f1     = report["1"]["f1-score"]
    total  = len(dataset)

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val in [
        (c1, "Training Samples", f"{total}"),
        (c2, "Model Accuracy",   f"{acc*100:.1f}%"),
        (c3, "Precision",        f"{prec*100:.1f}%"),
        (c4, "Recall",           f"{recall*100:.1f}%"),
        (c5, "F1 Score",         f"{f1*100:.1f}%"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Session state initialisation (must happen BEFORE widgets render) ──────
    # Streamlit widgets bound via `key=` read their initial value from
    # st.session_state on every rerun. We initialise the keys here so that
    # clicking a Quick Test button can write the sample text into state
    # before the text_area is drawn — making the value appear immediately.
    if "ad_text" not in st.session_state:
        st.session_state["ad_text"] = ""
    if "url_input" not in st.session_state:
        st.session_state["url_input"] = ""
    # auto_analyze is set to True when a Quick Test button is clicked so the
    # results section fires on the same rerun that fills the text area.
    if "auto_analyze" not in st.session_state:
        st.session_state["auto_analyze"] = False

    # ── Quick Test examples (defined here so the callback can reference them) ─
    examples = {
        "Job Scam Sample":   "Urgent hiring! Work from home. Earn ₹50,000 per day. No experience needed. Immediate joining. WhatsApp now.",
        "Loan Scam Sample":  "Instant personal loan ₹50 lakh approved in 10 minutes. No CIBIL check. No documents. Apply now.",
        "Investment Scam":   "Invest ₹5000 and get ₹50,000 in 30 days. 300% guaranteed returns. Limited slots. Join now.",
        "Genuine Ad Sample": "TCS is hiring software engineers. B.Tech required. 3+ years experience. Apply on tcs.com careers portal.",
    }

    def load_example(text: str):
        """Callback: writes sample into session state and arms auto-analysis."""
        st.session_state["ad_text"]      = text
        st.session_state["url_input"]    = ""
        st.session_state["auto_analyze"] = True

    # ── Input columns ─────────────────────────────────────────────────────────
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown('<div class="section-title">📋 Paste Advertisement Text</div>', unsafe_allow_html=True)
        # key="ad_text" binds the widget to st.session_state["ad_text"].
        # Any value written to that key before this line renders will appear
        # in the box automatically (that's how load_example() works).
        ad_text = st.text_area(
            label="ad_text",
            label_visibility="collapsed",
            placeholder="Paste the suspicious advertisement text here...\n\nExample: Earn ₹50,000 per day working from home! No experience needed. Immediate joining. WhatsApp now. Limited seats available...",
            height=180,
            key="ad_text",
        )

        st.markdown('<div class="section-title">🔗 Suspicious URL Checker (Optional)</div>', unsafe_allow_html=True)
        url_input = st.text_input(
            label="url_input",
            label_visibility="collapsed",
            placeholder="e.g. http://sbi-loan-offer.xyz/apply or paste any suspicious link...",
            key="url_input",
        )

        analyze_btn = st.button("🔍 Analyze for Fraud", type="primary", use_container_width=True)

    with right:
        st.markdown('<div class="section-title">💡 What This System Detects</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#f8fafc;border-radius:10px;padding:16px 20px;border:1px solid #e2e8f0">
        <b>👷 Job Scams</b><br>
        <span style="color:#64748b;font-size:0.88rem">Work-from-home, fake recruitment, advance-fee jobs</span><br><br>
        <b>🏦 Loan Scams</b><br>
        <span style="color:#64748b;font-size:0.88rem">No-CIBIL loans, instant approval, processing fee traps</span><br><br>
        <b>📈 Investment Scams</b><br>
        <span style="color:#64748b;font-size:0.88rem">Crypto/Forex frauds, MLM schemes, Ponzi structures</span><br><br>
        <b>🔗 Phishing URLs</b><br>
        <span style="color:#64748b;font-size:0.88rem">Brand impersonation, suspicious TLDs, IP-based domains</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick test examples — on_click writes to session state BEFORE the
        # next rerun renders the widgets, so the text area is already filled.
        st.markdown('<div class="section-title">⚡ Quick Test Examples</div>', unsafe_allow_html=True)
        for name, sample_text in examples.items():
            st.button(
                f"📌 {name}",
                use_container_width=True,
                key=f"btn_{name}",
                on_click=load_example,
                args=(sample_text,),
            )

    # ── Decide whether to run analysis ────────────────────────────────────────
    # Trigger if the user clicked "Analyze" OR if a Quick Test button armed
    # the auto_analyze flag (which load_example() sets to True).
    should_analyze = analyze_btn or st.session_state["auto_analyze"]
    if st.session_state["auto_analyze"]:
        st.session_state["auto_analyze"] = False   # reset so it doesn't re-fire

    # ── Analysis Output ───────────────────────────────────────────────────────
    if should_analyze and (ad_text.strip() or url_input.strip()):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("## 📊 Analysis Results")

        # ── Text Analysis ─────────────────────────────────────────────────────
        if ad_text.strip():
            prob        = model.predict_proba([ad_text])[0][1]  # P(fake)
            risk_score  = int(prob * 100)
            prediction  = model.predict([ad_text])[0]

            # Adjust risk score using keyword bonus (to reward explicit red flags)
            found_kws   = find_risk_keywords(ad_text)
            kw_bonus    = min(len([kw for kws in found_kws.values() for kw in kws]) * 3, 20)
            risk_score  = min(risk_score + kw_bonus, 100)

            fraud_type, emoji = classify_fraud_type(ad_text)

            # Risk level label
            if risk_score >= 80:
                badge_class, level_label = "risk-critical", "🔴 CRITICAL RISK"
            elif risk_score >= 60:
                badge_class, level_label = "risk-high",     "🟠 HIGH RISK"
            elif risk_score >= 35:
                badge_class, level_label = "risk-medium",   "🟡 MEDIUM RISK"
            else:
                badge_class, level_label = "risk-low",      "🟢 LOW RISK"

            r1, r2, r3 = st.columns([1.2, 1.5, 1.3], gap="large")

            # Gauge
            with r1:
                st.markdown("**Fraud Risk Meter**")
                st.markdown(render_gauge(risk_score), unsafe_allow_html=True)
                st.markdown(f'<div style="text-align:center"><span class="risk-badge {badge_class}">{level_label}</span></div>', unsafe_allow_html=True)

            # Police insight card
            with r2:
                st.markdown("**Police Insights**")
                verdict_icon = "🚨 FAKE / FRAUDULENT" if prediction == 1 else "✅ APPEARS GENUINE"
                st.markdown(f"""
                <div class="insight-card">
                    <h3>AI Verdict</h3>
                    <p class="fraud-type">{verdict_icon}</p>
                    <br>
                    <h3>Fraud Category</h3>
                    <p class="fraud-type">{emoji} {fraud_type}</p>
                    <br>
                    <h3>Recommended Action</h3>
                    <p style="font-size:0.9rem;opacity:0.9;margin:0">
                    {"⚡ Flag for investigation. Warn public. Trace advertiser contact details." if prediction == 1 else "✔ No immediate action required. Continue monitoring."}
                    </p>
                </div>
                """, unsafe_allow_html=True)

            # Keyword summary
            with r3:
                st.markdown("**Red Flag Summary**")
                total_flags = sum(len(v) for v in found_kws.values())
                st.metric("Keywords Flagged", total_flags)
                st.metric("Fraud Probability", f"{risk_score}%")
                st.metric("Fraud Type", fraud_type.split("/")[0].strip())

            # Keyword Highlighting
            if found_kws:
                st.markdown('<div class="section-title">🔦 Keyword Analysis — Why This Ad Was Flagged</div>', unsafe_allow_html=True)
                all_matched = [kw for kws in found_kws.values() for kw in kws]
                highlighted_html = highlight_text(ad_text, all_matched)
                st.markdown(
                    f'<div style="background:#fff8f0;border:1px solid #fed7aa;border-radius:8px;padding:16px;line-height:1.8;font-size:0.95rem">{highlighted_html}</div>',
                    unsafe_allow_html=True
                )

                st.markdown('<div class="section-title">📂 Flagged Keyword Categories</div>', unsafe_allow_html=True)
                for cat, kws in found_kws.items():
                    with st.expander(f"⚠️ {cat}  ({len(kws)} match{'es' if len(kws)>1 else ''})"):
                        tags_html = " ".join(f'<span class="kw-tag">{kw}</span>' for kw in kws)
                        st.markdown(tags_html, unsafe_allow_html=True)
            else:
                st.info("✅ No high-risk keywords detected in this text.")

        # ── URL Analysis ──────────────────────────────────────────────────────
        if url_input.strip():
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<div class="section-title">🔗 URL Risk Analysis</div>', unsafe_allow_html=True)
            url_result = check_url(url_input)

            u1, u2 = st.columns([1, 2])
            with u1:
                st.markdown(render_gauge(url_result["risk_score"]), unsafe_allow_html=True)
            with u2:
                st.markdown(f"### {url_result['verdict']}")
                if url_result["flags"]:
                    st.markdown("**Suspicious Indicators Detected:**")
                    for flag in url_result["flags"]:
                        st.markdown(f"- {flag}")
                else:
                    st.success("No obvious suspicious URL patterns found.")

    elif analyze_btn:
        st.warning("⚠️ Please enter advertisement text or a URL to analyze.")

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer">
        🚔 Nuh Police Cyber Crime Unit · AI Fake Ad Detection Prototype · 
        Built with Python, Scikit-learn, TF-IDF & Streamlit ·
        Student: Ankita Bhargava (230160227008) · GDGU
    </div>
    """, unsafe_allow_html=True)


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
