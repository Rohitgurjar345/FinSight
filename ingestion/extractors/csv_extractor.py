import pandas as pd


def extract(filepath: str) -> pd.DataFrame:
    """Reads a CSV, tolerant of encoding issues."""
    try:
        return pd.read_csv(filepath)
    except UnicodeDecodeError:
        return pd.read_csv(filepath, encoding="latin1")
