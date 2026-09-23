from abc import ABC, abstractmethod
import pandas as pd
from ingestion.schema import Transaction


class BaseParser(ABC):
    bank_name = "GENERIC"

    @abstractmethod
    def matches(self, df: pd.DataFrame) -> bool:
        """Return True if this parser's expected column fingerprint is present."""
        ...

    @abstractmethod
    def parse(self, df: pd.DataFrame, source_file: str, source_format: str) -> list:
        """Return a list of Transaction objects."""
        ...

    @staticmethod
    def _to_float(val, default=0.0):
        try:
            if pd.isna(val) or val == "":
                return default
            return float(str(val).replace(",", "").strip())
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _to_iso_date(val):
        try:
            return pd.to_datetime(val, dayfirst=True, errors="coerce").strftime("%Y-%m-%d")
        except Exception:
            return None
