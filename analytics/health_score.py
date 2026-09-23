"""Financial Health Score — explainable, weighted, calibrated against real
population percentiles from data.csv (20,000 individual profiles).

Design principle: no black box. Every score exposes the raw metric value,
where it sits in the population (percentile), the weight applied, and its
contribution to the final 0-100 score.
"""
import numpy as np
import pandas as pd
import joblib

EXPENSE_COLS = ["Rent", "Loan_Repayment", "Insurance", "Groceries", "Transport",
                 "Eating_Out", "Entertainment", "Utilities", "Healthcare",
                 "Education", "Miscellaneous"]
ESSENTIAL_COLS = ["Rent", "Groceries", "Utilities", "Healthcare"]

# Higher raw value = better financial health for these metrics
HIGHER_IS_BETTER = {"savings_rate": True, "debt_to_income": False,
                     "essential_expense_ratio": False, "category_diversification": True}

# NOTE: expense_to_income was dropped — it's mathematically 1 - savings_rate,
# so scoring both was double-counting the same signal at 60% combined weight.
# essential_expense_ratio (rent/groceries/utilities/healthcare only) is an
# independent measure of fixed-cost burden, not just the inverse of savings.
WEIGHTS = {"savings_rate": 0.40, "debt_to_income": 0.25,
           "essential_expense_ratio": 0.20, "category_diversification": 0.15}


def compute_raw_features(row: dict) -> dict:
    """row must have: Income, Loan_Repayment, and the EXPENSE_COLS."""
    income = max(float(row.get("Income", 0)), 1e-6)
    total_expenses = sum(float(row.get(c, 0)) for c in EXPENSE_COLS)
    loan = float(row.get("Loan_Repayment", 0))

    savings_rate = (income - total_expenses) / income
    debt_to_income = loan / income
    essential_expense_ratio = sum(float(row.get(c, 0)) for c in ESSENTIAL_COLS) / income

    # Herfindahl-based diversification: 1 - concentration index.
    # Spread across many categories -> higher diversification score.
    shares = np.array([max(float(row.get(c, 0)), 0) for c in EXPENSE_COLS])
    total = shares.sum()
    if total > 0:
        shares = shares / total
        herfindahl = (shares ** 2).sum()  # 1/n (diversified) .. 1 (concentrated)
        diversification = 1 - herfindahl
    else:
        diversification = 0.0

    return {
        "savings_rate": savings_rate,
        "debt_to_income": debt_to_income,
        "essential_expense_ratio": essential_expense_ratio,
        "category_diversification": diversification,
    }


class FinancialHealthScore:
    def __init__(self):
        self.percentile_refs = {}  # metric -> sorted np.array of population values

    def fit(self, population_df: pd.DataFrame):
        """Builds percentile reference distributions from population data."""
        rows = population_df.to_dict("records")
        feature_rows = [compute_raw_features(r) for r in rows]
        feat_df = pd.DataFrame(feature_rows)
        for metric in WEIGHTS:
            self.percentile_refs[metric] = np.sort(feat_df[metric].values)
        return self

    def _percentile(self, metric: str, value: float) -> float:
        ref = self.percentile_refs[metric]
        rank = np.searchsorted(ref, value, side="right")
        pct = rank / len(ref)  # 0..1
        if not HIGHER_IS_BETTER[metric]:
            pct = 1 - pct
        return float(np.clip(pct, 0, 1))

    def score(self, user_row: dict) -> dict:
        """Returns full breakdown: overall 0-100 score + per-metric detail."""
        raw = compute_raw_features(user_row)
        breakdown = {}
        total = 0.0
        for metric, weight in WEIGHTS.items():
            pct = self._percentile(metric, raw[metric])
            contribution = pct * weight * 100
            breakdown[metric] = {
                "raw_value": round(raw[metric], 4),
                "population_percentile": round(pct * 100, 1),
                "weight": weight,
                "contribution": round(contribution, 2),
            }
            total += contribution
        return {"score": round(total, 1), "breakdown": breakdown}

    def save(self, path):
        joblib.dump(self.percentile_refs, path)

    def load(self, path):
        self.percentile_refs = joblib.load(path)
        return self
