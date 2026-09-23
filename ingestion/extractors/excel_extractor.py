import pandas as pd


def extract(filepath: str) -> pd.DataFrame:
    """Reads the first sheet of an .xlsx/.xls file."""
    return pd.read_excel(filepath)
