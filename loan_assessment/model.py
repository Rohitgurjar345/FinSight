"""Loan Pre-Assessment: XGBoost (falls back to sklearn GradientBoostingClassifier
if xgboost isn't installed) classifier with SHAP explainability.

This is a PRE-ASSESSMENT tool only — see DISCLAIMER. It is not a real
underwriting decision and must never be presented as one.
"""
import numpy as np
import joblib

try:
    from xgboost import XGBClassifier
    _MODEL_BACKEND = "xgboost"
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier
    _MODEL_BACKEND = "sklearn_gbc"

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False

FEATURES = ["age", "income", "assets", "credit_score",
            "debt_to_income_ratio", "existing_loan", "criminal_record"]

DISCLAIMER = (
    "This is an automated pre-assessment for informational purposes only. "
    "It is NOT a loan approval, denial, or offer, and does not represent the "
    "decision of any lender. Real underwriting considers additional factors "
    "this model does not have access to. Consult a licensed lender for an "
    "actual loan decision."
)

# Three-tier readiness thresholds on predicted approval probability
TIER_THRESHOLDS = {"ready": 0.60, "borderline": 0.30}  # below borderline -> needs_improvement


def tier_from_probability(prob: float) -> str:
    if prob >= TIER_THRESHOLDS["ready"]:
        return "ready"
    if prob >= TIER_THRESHOLDS["borderline"]:
        return "borderline"
    return "needs_improvement"


class LoanAssessor:
    def __init__(self):
        if _MODEL_BACKEND == "xgboost":
            self.model = XGBClassifier(
                n_estimators=150, max_depth=4, learning_rate=0.1,
                scale_pos_weight=7,  # counter the ~89/11 class imbalance
                random_state=42, eval_metric="logloss",
            )
        else:
            self.model = XGBClassifier(
                n_estimators=150, max_depth=4, learning_rate=0.1, random_state=42
            )
        self.backend = _MODEL_BACKEND
        self._explainer = None

    def fit(self, X, y):
        self.model.fit(X[FEATURES], y)

    def predict_proba(self, X):
        return self.model.predict_proba(X[FEATURES])[:, 1]

    def assess(self, applicant: dict) -> dict:
        """Full pre-assessment for a single applicant: probability, tier,
        SHAP-based per-feature explanation, and the mandatory disclaimer."""
        import pandas as pd
        row = pd.DataFrame([{f: applicant.get(f, 0) for f in FEATURES}])
        prob = float(self.predict_proba(row)[0])
        tier = tier_from_probability(prob)
        explanation = self.explain(row)
        return {
            "approval_probability": round(prob, 4),
            "readiness_tier": tier,
            "feature_contributions": explanation,
            "disclaimer": DISCLAIMER,
        }

    def explain(self, row) -> dict:
        """Per-feature SHAP contribution for this single prediction.
        Falls back to global feature_importances_ if shap isn't installed
        (clearly labeled as a weaker, non-per-instance explanation)."""
        if _SHAP_AVAILABLE:
            if self._explainer is None:
                self._explainer = shap.TreeExplainer(self.model)
            shap_values = self._explainer.shap_values(row[FEATURES])
            values = shap_values[0] if isinstance(shap_values, np.ndarray) and shap_values.ndim == 2 else shap_values
            values = np.array(values).flatten()
            return {
                "method": "shap",
                "contributions": {f: round(float(v), 4) for f, v in zip(FEATURES, values)},
            }
        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            return {"method": "unavailable", "contributions": {}}
        return {
            "method": "global_feature_importance (shap not installed — this is NOT per-applicant)",
            "contributions": {f: round(float(v), 4) for f, v in zip(FEATURES, importances)},
        }

    def save(self, path):
        joblib.dump({"model": self.model, "backend": self.backend}, path)

    def load(self, path):
        d = joblib.load(path)
        self.model = d["model"]
        self.backend = d["backend"]
        self._explainer = None
        return self
