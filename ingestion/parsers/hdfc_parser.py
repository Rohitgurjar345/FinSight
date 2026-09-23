import pandas as pd
from ingestion.parsers.base_parser import BaseParser
from ingestion.schema import Transaction

# HDFC net-banking statement export column fingerprint (publicly documented format)
FINGERPRINT = {"date", "narration", "withdrawal amt", "deposit amt", "closing balance"}
FINGERPRINT_ALT = {"date", "transaction details", "withdrawal amt", "deposit amt", "balance amt"}


class HDFCParser(BaseParser):
    bank_name = "HDFC"

    def matches(self, df: pd.DataFrame) -> bool:
        cols = {c.strip().lower() for c in df.columns}
        return FINGERPRINT.issubset(cols) or FINGERPRINT_ALT.issubset(cols)

    def parse(self, df, source_file, source_format):
        cols = {c.strip().lower(): c for c in df.columns}
        date_col = cols.get("date")
        narr_col = cols.get("narration") or cols.get("transaction details")
        wd_col = cols.get("withdrawal amt")
        dep_col = cols.get("deposit amt")
        bal_col = cols.get("closing balance") or cols.get("balance amt")
        val_col = cols.get("value date")

        txns = []
        for _, row in df.iterrows():
            wd = self._to_float(row.get(wd_col))
            dep = self._to_float(row.get(dep_col))
            amount = dep - wd
            t = Transaction(
                date=self._to_iso_date(row.get(date_col)),
                value_date=self._to_iso_date(row.get(val_col)) if val_col else None,
                raw_narration=str(row.get(narr_col, "")).strip(),
                amount=amount,
                balance=self._to_float(row.get(bal_col), default=None),
                type="credit" if amount >= 0 else "debit",
                bank=self.bank_name,
                source_file=source_file,
                source_format=source_format,
            )
            t.compute_id()
            txns.append(t)
        return txns
