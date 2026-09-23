import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from loan_assessment.model import LoanAssessor, FEATURES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(f"{DATA_DIR}/Loan_Prediction.csv")
    print(f"Rows: {len(df)}, approval rate: {df['loan_approved'].mean():.1%} (imbalanced — using scale_pos_weight)")

    X = df[FEATURES]
    y = df["loan_approved"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    assessor = LoanAssessor()
    assessor.fit(X_train, y_train)

    probs = assessor.predict_proba(X_test)
    preds = (probs >= 0.5).astype(int)

    print(f"\nBackend: {assessor.backend}")
    print(f"ROC-AUC: {roc_auc_score(y_test, probs):.4f}")
    print(f"Confusion matrix:\n{confusion_matrix(y_test, preds)}")
    print(classification_report(y_test, preds, target_names=["not_approved", "approved"]))

    assessor.save(f"{MODEL_DIR}/loan_assessment_model.joblib")
    print(f"Model saved to {MODEL_DIR}/loan_assessment_model.joblib")

    # Sanity check: SHAP explanation on one real applicant
    sample = X_test.iloc[0].to_dict()
    result = assessor.assess(sample)
    print(f"\nSample assessment: {result}")


if __name__ == "__main__":
    main()
