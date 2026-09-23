import os
import pandas as pd
from analytics.health_score import FinancialHealthScore

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(f"{DATA_DIR}/data.csv")
    print(f"Population reference: {len(df)} profiles")

    hs = FinancialHealthScore().fit(df)
    hs.save(f"{MODEL_DIR}/health_score_percentiles.joblib")
    print(f"Saved percentile reference to {MODEL_DIR}/health_score_percentiles.joblib")

    # Sanity check: score a couple of real rows from the population itself
    for i in [0, 1, 100]:
        row = df.iloc[i].to_dict()
        result = hs.score(row)
        print(f"\nRow {i} -> score {result['score']}/100")
        for metric, d in result["breakdown"].items():
            print(f"  {metric:26s} raw={d['raw_value']:>8} pctile={d['population_percentile']:>5}% "
                  f"weight={d['weight']} contrib={d['contribution']}")


if __name__ == "__main__":
    main()
