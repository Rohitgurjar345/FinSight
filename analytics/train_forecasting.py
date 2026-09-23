"""Trains the monthly expense forecaster and honestly compares it against a
naive 3-month moving-average baseline — per the synopsis requirement that
the ML model's improvement (or lack of it) be shown, not just claimed."""
import os
import numpy as np
from sklearn.metrics import mean_absolute_error
from analytics.forecasting import (
    load_monthly_series, build_features, naive_baseline_predict, ExpenseForecaster
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")
TEST_MONTHS = 12  # holdout: most recent 12 months, time-ordered (no shuffling)


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    series = load_monthly_series(
        f"{DATA_DIR}/monthly_spending_dataset_2020_2025-selected-columns__1_.csv"
    )
    print(f"Loaded {len(series)} months: {series.index.min().date()} to {series.index.max().date()}")

    feat_df = build_features(series)
    train_df = feat_df.iloc[:-TEST_MONTHS]
    test_df = feat_df.iloc[-TEST_MONTHS:]
    print(f"Train: {len(train_df)} months, Test (holdout, most recent): {len(test_df)} months")

    forecaster = ExpenseForecaster()
    forecaster.fit(train_df)
    ml_preds = forecaster.predict(test_df)
    ml_mae = mean_absolute_error(test_df["y"], ml_preds)

    baseline_preds = naive_baseline_predict(series, test_df.index)
    baseline_mae = mean_absolute_error(test_df["y"], baseline_preds)

    print(f"\nBackend used: {forecaster.backend}")
    print(f"Naive 3-month moving-average baseline MAE: {baseline_mae:,.2f}")
    print(f"{forecaster.backend} model MAE:                {ml_mae:,.2f}")
    improvement = (baseline_mae - ml_mae) / baseline_mae * 100
    if improvement > 0:
        print(f"-> ML model beats the baseline by {improvement:.1f}%")
    else:
        print(f"-> ML model does NOT beat the baseline (worse by {-improvement:.1f}%). "
              f"With only {len(train_df)} training months, this is a real, honest possibility, "
              f"not a bug — the baseline is a strong competitor on short series like this one.")

    forecaster.save(f"{MODEL_DIR}/forecast_model.joblib")
    print(f"\nModel saved to {MODEL_DIR}/forecast_model.joblib")


if __name__ == "__main__":
    main()
