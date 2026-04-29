# CyberGuard-Ad-Detector
An AI-powered system designed to detect and classify fraudulent online advertisements (Job, Loan, and Investment scams) using NLP and Random Forest Classifiers. Developed as a prototype for the Nuh Police Department Cyber Crime internship.

# 🚔 AI-Based Fake Online Advertisement Detection System

### Project Overview
Developed for the **Nuh Police Department Internship Selection**. This tool automates the detection of cyber fraud ads related to job, loan, and investment scams.

### 🛠️ Technical Stack
* [cite_start]**Language:** Python [cite: 17]
* [cite_start]**ML Model:** Random Forest Classifier (Scikit-learn) [cite: 19]
* [cite_start]**Vectorization:** TF-IDF (Term Frequency-Inverse Document Frequency) [cite: 18]
* **UI Framework:** Streamlit
* [cite_start]**Hardware Requirements:** 8GB RAM Minimum [cite: 26]

### 🚀 Features
- [cite_start]**Real-time Classification:** Detects if an ad is "Genuine" or "Fake"[cite: 13].
- [cite_start]**Fraud Risk Scoring:** Provides a 0-100% risk probability[cite: 15].
- **Explainable AI:** Highlights "Red Flag" keywords used in Indian cyber scams.
- [cite_start]**URL Analysis:** Scans for suspicious domains and phishing patterns[cite: 14].

### 🛠️ Installation & Usage
1. Clone: `git clone <repo-url>`
2. Install: `pip install -r requirements.txt`
3. Run: `streamlit run app.py`


# CyberGuard Chrome Extension
### AI-Based Fake Advertisement Detection System  
**Nuh Police Cyber Crime Unit · Built by Ankita Bhargava (230160227008)**

---

## 📁 Project Structure

```
cyberguard/
├── extension/               ← Chrome Extension (Manifest V3)
│   ├── manifest.json        ← Extension config, permissions, entry points
│   ├── content.js           ← DOM scanner + floating risk badge
│   ├── content.css          ← Badge styles (injected into web pages)
│   ├── background.js        ← Service worker: API relay + badge icon
│   ├── popup.html           ← Extension popup UI
│   ├── popup.js             ← Popup logic: rendering + scan + report
│   └── icons/               ← Extension icons (16, 48, 128 px)
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
│
└── backend/
    ├── api.py               ← FastAPI server (ML model + report endpoint)
    └── requirements.txt     ← Python dependencies
```

---

## 🚀 Quick Start

### Step 1 — Start the Backend API

```bash
cd backend
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Verify it's running: open http://localhost:8000 in your browser.  
You should see: `{"service": "CyberGuard API", "status": "online", ...}`

---

### Step 2 — Load the Chrome Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer Mode** (toggle, top right)
3. Click **"Load unpacked"**
4. Select the `extension/` folder
5. The CyberGuard shield icon (🛡️) will appear in your toolbar

> **Note on icons:** Chrome requires real PNG files. If `icons/` is missing,  
> the extension will still load — Chrome will use a placeholder icon.  
> Create 16×16, 48×48, and 128×128 PNGs of your shield logo and put them there.

---

### Step 3 — Test It

1. Visit any page with scam-like content (or use the Quick Test in the Streamlit app)
2. Try pasting this URL into your browser:  
   `data:text/html,<body>Earn ₹50000 per day work from home no experience needed immediate joining whatsapp now 100% guaranteed returns</body>`
3. Click the CyberGuard toolbar icon — you should see the risk score

---

## 🏗️ Architecture (For Judges)

```
┌─────────────────────────────────────────────────────────────────┐
│                        WEB PAGE                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  content.js  (Content Script — runs in page context)     │   │
│  │                                                          │   │
│  │  1. Scans DOM text every 1.5s (MutationObserver)        │   │
│  │  2. Checks for ≥2 trigger keywords (fast regex)         │   │
│  │  3. Sends text to background.js via sendMessage()       │   │
│  │  4. Receives result → injects floating risk badge       │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────│─────────────────────────────────────┘
                            │  chrome.runtime.sendMessage()
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  background.js  (Service Worker — extension context)            │
│                                                                  │
│  1. Receives SCAN_TEXT message                                  │
│  2. POSTs { text, url } to FastAPI /analyze                    │
│  3. Updates toolbar badge icon (colour + number)               │
│  4. Caches result in chrome.storage.local                      │
│  5. Shows desktop notification for CRITICAL risk (>80%)        │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP POST  localhost:8000/analyze
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend  (api.py — Python process)                     │
│                                                                  │
│  /analyze                                                       │
│  ├── TfidfVectorizer (n-gram 1-2, 5000 features)              │
│  ├── RandomForestClassifier (200 trees)                        │
│  ├── predict_proba() → fraud probability                       │
│  ├── Keyword bank scan → bonus score                           │
│  ├── URL heuristic check                                       │
│  └── Returns: { risk_score, verdict, category, keywords }     │
│                                                                  │
│  /report                                                        │
│  └── Stores structured report → police_reports.jsonl          │
└─────────────────────────────────────────────────────────────────┘
                         ▲
                         │  chrome.runtime.sendMessage()
┌────────────────────────┴────────────────────────────────────────┐
│  popup.html + popup.js  (Extension Popup)                       │
│                                                                  │
│  1. Reads cached result from chrome.storage.local              │
│  2. Renders animated SVG gauge + keyword tags                  │
│  3. "Scan Now" button → forces fresh content.js scan           │
│  4. "Report to Police" form → sends to /report endpoint        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check + model accuracy |
| `/analyze` | POST | Analyse text, returns risk JSON |
| `/report` | POST | File a police report |
| `/reports` | GET | List recent reports (police dashboard) |
| `/model/stats` | GET | Model accuracy, precision, recall |

### Example `/analyze` Request:
```json
POST http://localhost:8000/analyze
{
  "text": "Urgent hiring work from home earn 50000 per day no experience needed",
  "url":  "http://sbi-loan-offer.xyz/apply"
}
```

### Example Response:
```json
{
  "risk_score": 91,
  "verdict": "FAKE",
  "fraud_category": "Job / Employment Fraud",
  "flagged_keywords": {
    "Urgency / Pressure Tactics": ["urgent"],
    "Unrealistic Income Claims": ["earn ₹50,000 per day"],
    "No-Document / No-Check Schemes": ["no experience needed"]
  },
  "url_risk_score": 80,
  "url_flags": ["Brand impersonation: sbi", "Suspicious TLD: .xyz"],
  "model_confidence": 0.915,
  "scanned_at": "2024-04-30T09:15:00Z"
}
```

---

## 🎤 Judge Talking Points

| Component | What to say |
|---|---|
| `manifest.json` | "Manifest V3 is the latest Chrome standard. It replaces persistent background pages with a Service Worker for better performance and security." |
| `content.js` | "This runs inside every web page. It uses a MutationObserver to detect dynamically loaded ad content — important for catching scams on Facebook, OLX, and Telegram web." |
| `background.js` | "Acts as the secure bridge. The content script can't make cross-origin requests, so it routes through the service worker which talks to our Python API." |
| `api.py` | "TF-IDF converts text to numbers. The Random Forest ensemble then votes: 200 trees each seeing a random feature subset. predict_proba() gives us the probability, not just a yes/no." |
| Report System | "Every report is timestamped, assigned a CG-XXXXXXXX ID, and written to a JSONL log. This creates an audit trail the police can use as evidence." |
