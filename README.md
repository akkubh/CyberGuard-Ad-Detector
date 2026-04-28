# 🚔 AI-Based Fake Advertisement Detection System
**Cyber Crime Detection and Prevention Unit • Nuh Police Department Prototype**

### 🎯 Overview
[cite_start]This project is an automated AI-based detection system designed to identify the fraudulent online advertisements related to job, loan, and investment scams[cite: 2, 4]. [cite_start]It provides real-time risk scoring to help prevent citizens from falling victim to attractive but misleading offers[cite: 5, 15].

### 🛠️ Technical Architecture
* [cite_start]**Frontend:** Streamlit (Real-time Web Dashboard) [cite: 27]
* [cite_start]**Backend:** Python, Pandas, NumPy [cite: 17]
* [cite_start]**Machine Learning:** Random Forest Classifier & Logistic Regression [cite: 19]
* [cite_start]**NLP Pipeline:** TF-IDF Vectorization (capturing unigrams and bigrams) [cite: 18]
* [cite_start]**Logic:** Hybrid detection combining ML predictions with rule-based URL analysis.

### 🚀 Key Features
- [cite_start]**Fraud Risk Score:** Generates a 0-100% probability of fraud[cite: 15].
- [cite_start]**Threat Categorization:** Classifies ads into Job, Loan, or Investment scams[cite: 13, 21].
- [cite_start]**URL Analysis:** Flags suspicious TLDs, IP-based domains, and brand impersonation.
- [cite_start]**Explainable AI:** Highlights "Red Flag" keywords to explain why an ad was flagged[cite: 15].

### 💻 Installation
1. Clone the repo: `git clone https://github.com/AnkitaBhargava/CyberGuard-Ad-Detector.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `streamlit run fake_ad_detector.py`
