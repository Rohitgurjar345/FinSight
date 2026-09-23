"""Monthly expense forecasting. Tries xgboost, falls back to sklearn's
GradientBoostingRegressor (same gradient-boosted-tree family) if xgboost
isn't installed — so this runs anywhere and upgrades automatically once
xgboost is available (pip install xgboost)."""
import numpy as np
import pandas as pd
import joblib

try:
    from xgboost import XGBRegressor
    _BACKEND = "xgboost"
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor as XGBRegressor
    _BACKEND = "sklearn_gbr"

EXPENSE_COLS = ["Groceries (₹)", "Rent (₹)", "Transportation (₹)", "Gym (₹)",
                 "Utilities (₹)", "Healthcare (₹)", "EMI/Loans (₹)"]
N_LAGS = 3


def load_monthly_series(filepath: str) -> pd.Series:
    """Loads the monthly dataset, returns a total-expense time series indexed by month."""
    df = pd.read_csv(filepath)
    df["Month"] = pd.to_datetime(df["Month"])
    df = df.sort_values("Month").reset_index(drop=True)
    df["total_expense"] = df[EXPENSE_COLS].sum(axis=1)
    return df.set_index("Month")["total_expense"]


def build_features(series: pd.Series) -> pd.DataFrame:
    """Lag features + calendar features for each month, predicting that month's value."""
    df = pd.DataFrame({"y": series})
    for lag in range(1, N_LAGS + 1):
        df[f"lag_{lag}"] = df["y"].shift(lag)
    df["month_sin"] = np.sin(2 * np.pi * df.index.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df.index.month / 12)
    return df.dropna()


def naive_baseline_predict(series: pd.Series, test_index) -> pd.Series:
    """Baseline: 3-month moving average of prior months (not the ML model)."""
    preds = {}
    for ts in test_index:
        prior = series[series.index < ts].tail(3)
        preds[ts] = prior.mean()
    return pd.Series(preds)


class ExpenseForecaster:
    def __init__(self):
        # Shallow, few trees on purpose — only 54 training months are available,
        # deeper/more trees overfit noise and score worse on holdout (tested).
        extra = {"min_child_weight": 2} if _BACKEND == "xgboost" else {"min_samples_leaf": 2}
        self.model = XGBRegressor(n_estimators=50, max_depth=2, learning_rate=0.1,
                                   random_state=42, **extra)
        self.backend = _BACKEND
        self.feature_cols = None

    def fit(self, feat_df: pd.DataFrame):
        self.feature_cols = [c for c in feat_df.columns if c != "y"]
        self.model.fit(feat_df[self.feature_cols], feat_df["y"])

    def predict(self, feat_df: pd.DataFrame) -> pd.Series:
        preds = self.model.predict(feat_df[self.feature_cols])
        return pd.Series(preds, index=feat_df.index)

    def save(self, path):
        joblib.dump({"model": self.model, "feature_cols": self.feature_cols,
                     "backend": self.backend}, path)

    def load(self, path):
        d = joblib.load(path)
        self.model = d["model"]
        self.feature_cols = d["feature_cols"]
        self.backend = d["backend"]
        return self
