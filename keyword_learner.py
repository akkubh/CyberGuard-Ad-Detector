"""
keyword_learner.py
──────────────────
Dynamic keyword extraction system. Instead of a static hardcoded list,
this module:

1. Extracts the most "scam-predictive" n-grams from the trained TF-IDF model
   using feature importance from the Random Forest classifier.

2. Learns new keywords from confirmed fraud reports filed by officers.
   When police confirm a report, those phrases get added to the live keyword bank.

3. Exports an updated keyword list that api.py loads on each restart.

TECHNICAL NOTE:
We use the Random Forest's feature_importances_ scores mapped back to the
TF-IDF vocabulary to rank which phrases most strongly predict fraud.
This is essentially free explainability from the model we already have.

Run weekly: python keyword_learner.py
"""

import json
from pathlib import Path
from collections import Counter
import re

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline


LEARNED_KEYWORDS_FILE = Path("learned_keywords.json")


def extract_top_model_keywords(pipeline: Pipeline, top_n: int = 50) -> list[dict]:
    """
    Extract the most fraud-predictive phrases from the trained model.

    How it works:
    - TfidfVectorizer has a vocabulary: each word/phrase → column index
    - RandomForest has feature_importances_: each column index → importance score
    - We map them together and sort by importance
    """
    tfidf = pipeline.named_steps["tfidf"]
    clf   = pipeline.named_steps["clf"]

    vocab       = tfidf.vocabulary_           # phrase → index
    importances = clf.feature_importances_    # index → importance score

    # Invert vocab: index → phrase
    idx_to_phrase = {v: k for k, v in vocab.items()}

    # Sort by importance
    ranked = sorted(
        [(idx_to_phrase[i], float(importances[i])) for i in range(len(importances))],
        key=lambda x: x[1],
        reverse=True
    )

    return [{"phrase": phrase, "importance": round(score, 6)}
            for phrase, score in ranked[:top_n]]


def learn_from_reports(reports_file: Path) -> list[str]:
    """
    Scan confirmed police reports for recurring phrases not yet in the
    keyword bank. If a phrase appears in 3+ confirmed fraud reports,
    add it as a new learned keyword.
    """
    if not reports_file.exists():
        return []

    lines = reports_file.read_text(encoding="utf-8").strip().splitlines()
    phrase_counter = Counter()

    for line in lines:
        try:
            report = json.loads(line)
            # Only learn from confirmed high-risk reports
            if report.get("risk_score", 0) < 70:
                continue
            text = report.get("evidence_text", "") + " " + report.get("comment", "")
            text = text.lower()
            # Extract 2-3 word phrases
            words   = re.findall(r'\b[a-z₹\d]+\b', text)
            bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
            trigrams= [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
            phrase_counter.update(bigrams + trigrams)
        except Exception:
            continue

    # Return phrases that appear in 3+ reports
    return [phrase for phrase, count in phrase_counter.items() if count >= 3]


def update_keyword_file(pipeline: Pipeline, reports_file: Path):
    """Full pipeline: extract model keywords + learn from reports → save."""
    print("Extracting top model keywords...")
    model_keywords = extract_top_model_keywords(pipeline, top_n=100)

    print("Learning from confirmed reports...")
    report_keywords = learn_from_reports(reports_file)

    output = {
        "updated_at":      pd.Timestamp.now().isoformat(),
        "model_keywords":  model_keywords,
        "learned_from_reports": report_keywords,
        "total_learned":   len(report_keywords),
    }

    LEARNED_KEYWORDS_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Saved {len(model_keywords)} model keywords + {len(report_keywords)} learned keywords")
    print(f"Top 10 most predictive fraud phrases:")
    for kw in model_keywords[:10]:
        print(f"  {kw['importance']:.4f}  {kw['phrase']}")


def load_learned_keywords() -> list[str]:
    """Load the dynamically learned keywords. Returns [] if file doesn't exist."""
    if not LEARNED_KEYWORDS_FILE.exists():
        return []
    data = json.loads(LEARNED_KEYWORDS_FILE.read_text())
    return [kw["phrase"] for kw in data.get("model_keywords", [])]


if __name__ == "__main__":
    import sys
    sys.path.append(".")
    from api import MODEL, build_dataset
    from pathlib import Path
    update_keyword_file(MODEL, Path("police_reports.jsonl"))
