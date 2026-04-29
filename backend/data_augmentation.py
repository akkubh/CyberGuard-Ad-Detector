"""
data_augmentation.py
────────────────────
Expands the synthetic dataset using:
1. Synonym replacement for common scam phrases
2. Random word order shuffling (preserves meaning, fools overfitting)
3. Number variation (₹50,000 → ₹45,000 / ₹60,000)
4. Loads external CSV datasets (Kaggle fraudulent jobs etc.)

Run: python data_augmentation.py
Output: augmented_dataset.csv  (ready to drop into api.py)
"""

import re
import random
import pandas as pd

random.seed(42)

# ── SYNONYM MAP ───────────────────────────────────────────────────────────────
# Replace key scam phrases with equivalents to teach the model generalisation
SYNONYMS = {
    "work from home":        ["home based job", "remote work", "work at home", "wfh opportunity"],
    "earn ₹50,000":          ["make ₹50000", "income ₹50,000", "salary 50k", "get paid ₹50000"],
    "no experience needed":  ["freshers welcome", "no experience required", "zero experience", "anyone can apply"],
    "immediate joining":     ["join today", "start immediately", "joining on same day", "instant joining"],
    "whatsapp now":          ["message on whatsapp", "ping on wa", "whatsapp us", "contact on whatsapp"],
    "100% guaranteed":       ["fully guaranteed", "assured 100%", "guarantee 100 percent", "complete guarantee"],
    "no cibil":              ["bad cibil ok", "cibil not required", "no credit check", "poor cibil accepted"],
    "guaranteed returns":    ["assured returns", "fixed returns guaranteed", "100% profit assured"],
    "registration fee":      ["joining fee", "small registration charge", "nominal fee to join"],
    "limited seats":         ["only few slots", "limited vacancies", "hurry limited openings"],
    "passive income":        ["earn while you sleep", "automatic income", "income without working"],
    "no documents":          ["paperless loan", "no paperwork", "documents not required"],
}

def synonym_replace(text: str) -> str:
    for phrase, alternatives in SYNONYMS.items():
        if phrase in text.lower():
            replacement = random.choice(alternatives)
            text = re.sub(re.escape(phrase), replacement, text, flags=re.IGNORECASE, count=1)
    return text

def number_variation(text: str) -> str:
    """Randomly vary rupee amounts by ±10-20% so model learns amounts not exact numbers."""
    def vary(m):
        val = int(m.group(1).replace(",", ""))
        delta = random.randint(-int(val * 0.15), int(val * 0.20))
        new_val = max(100, val + delta)
        return f"₹{new_val:,}"
    return re.sub(r'₹([\d,]+)', vary, text)

def shuffle_sentences(text: str) -> str:
    """Shuffle sentence order — scammers don't always write in the same order."""
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
    if len(sentences) > 2:
        random.shuffle(sentences)
    return ". ".join(sentences) + "."

def augment_sample(text: str, n: int = 3) -> list[str]:
    """Generate n augmented variants of a single text sample."""
    variants = []
    for _ in range(n):
        t = text
        r = random.random()
        if r < 0.4:
            t = synonym_replace(t)
        elif r < 0.7:
            t = number_variation(t)
        else:
            t = shuffle_sentences(synonym_replace(t))
        if t != text:
            variants.append(t)
    return variants


def load_kaggle_jobs_dataset(csv_path: str) -> pd.DataFrame:
    """
    Load the Kaggle 'fraudulent_job_postings' dataset.
    Download from: https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobpostings
    CSV columns: title, location, description, requirements, fraudulent (0/1)
    """
    try:
        df = pd.read_csv(csv_path)
        # Combine text fields
        df["text"] = (
            df.get("title", "").fillna("") + " " +
            df.get("description", "").fillna("") + " " +
            df.get("requirements", "").fillna("")
        ).str.strip()
        df["label"]    = df["fraudulent"].astype(int)
        df["category"] = df["label"].map({1: "fake_job_kaggle", 0: "genuine_kaggle"})
        return df[["text", "category", "label"]].dropna()
    except FileNotFoundError:
        print(f"Kaggle dataset not found at {csv_path}. Skipping.")
        return pd.DataFrame(columns=["text", "category", "label"])


def build_augmented_dataset(base_df: pd.DataFrame, augment_factor: int = 4) -> pd.DataFrame:
    """
    Takes the base dataset and returns an augmented version.
    augment_factor=4 means each sample generates 4 additional variants.
    """
    augmented_rows = []

    for _, row in base_df.iterrows():
        # Keep original
        augmented_rows.append(row.to_dict())

        # Only augment fake samples (genuine samples are already clean)
        if row["label"] == 1:
            for variant_text in augment_sample(row["text"], n=augment_factor):
                augmented_rows.append({
                    "text":     variant_text,
                    "category": row["category"],
                    "label":    1,
                })

    result = pd.DataFrame(augmented_rows).drop_duplicates(subset=["text"])
    result = result.sample(frac=1, random_state=42).reset_index(drop=True)
    return result


if __name__ == "__main__":
    # Import base dataset from existing module
    import sys
    sys.path.append("../backend")
    from api import build_dataset

    print("Loading base dataset...")
    base_df = build_dataset()
    print(f"Base dataset: {len(base_df)} samples")

    # Augment
    print("Augmenting...")
    augmented = build_augmented_dataset(base_df, augment_factor=5)
    print(f"Augmented dataset: {len(augmented)} samples")
    print(augmented["label"].value_counts())

    # Optionally load Kaggle data
    kaggle_df = load_kaggle_jobs_dataset("fake_job_postings.csv")
    if len(kaggle_df):
        combined = pd.concat([augmented, kaggle_df], ignore_index=True)
        print(f"Combined with Kaggle: {len(combined)} samples")
    else:
        combined = augmented

    combined.to_csv("augmented_dataset.csv", index=False)
    print("Saved to augmented_dataset.csv")

    # Quick model test on augmented data
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report

    X_train, X_test, y_train, y_test = train_test_split(
        combined["text"], combined["label"],
        test_size=0.2, random_state=42, stratify=combined["label"]
    )
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=8000, sublinear_tf=True)),
        ("clf",   RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
    ])
    pipe.fit(X_train, y_train)
    print("\nModel performance on augmented dataset:")
    print(classification_report(y_test, pipe.predict(X_test)))
