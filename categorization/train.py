import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from categorization.classifier import Classifier
from ingestion.cleaning.narration_cleaner import clean as clean_narration

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


def load_training_data():
    a = pd.read_csv(f"{DATA_DIR}/financial_transaction_test.csv")
    a = a.rename(columns={"Transaction_Text": "text", "Label": "category"})

    b = pd.read_csv(f"{DATA_DIR}/test_transactions.csv")
    b = b.rename(columns={"transaction_text": "text", "category": "category"})

    df = pd.concat([a[["text", "category"]], b[["text", "category"]]], ignore_index=True)
    df["category"] = df["category"].str.lower().str.strip()
    df["text"] = df["text"].apply(clean_narration)
    df = df.dropna(subset=["text", "category"])
    df = df[df["text"].str.len() > 0]
    return df


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = load_training_data()
    print(f"Training rows: {len(df)}, categories: {sorted(df['category'].unique())}")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["category"], test_size=0.2, random_state=42, stratify=df["category"]
    )

    clf = Classifier()
    clf.fit(X_train.tolist(), y_train.tolist())

    preds = clf.predict(X_test.tolist())
    pred_labels = [p[0] for p in preds]
    print(f"Test accuracy: {accuracy_score(y_test, pred_labels):.4f}")
    print(classification_report(y_test, pred_labels))

    clf.save(MODEL_DIR)
    print(f"Model saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
