import pandas as pd
from ingestion.parsers.base_parser import BaseParser
from ingestion.schema import Transaction

# ICICI net-banking statement export column fingerprint
FINGERPRINT = {"transaction date", "description", "debit", "credit", "balance"}


class ICICIParser(BaseParser):
    bank_name = "ICICI"

    def matches(self, df: pd.DataFrame) -> bool:
        cols = {c.strip().lower() for c in df.columns}
        return FINGERPRINT.issubset(cols)

    def parse(self, df, source_file, source_format):
        cols = {c.strip().lower(): c for c in df.columns}
        date_col = cols.get("transaction date")
        val_col = cols.get("value date")
        narr_col = cols.get("description")
        deb_col = cols.get("debit")
        cred_col = cols.get("credit")
        bal_col = cols.get("balance")

        txns = []
        for _, row in df.iterrows():
            deb = self._to_float(row.get(deb_col))
            cred = self._to_float(row.get(cred_col))
            amount = cred - deb
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
