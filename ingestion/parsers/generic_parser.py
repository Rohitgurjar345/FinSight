import pandas as pd
from ingestion.parsers.base_parser import BaseParser
from ingestion.schema import Transaction

DATE_ALIASES = ["date", "txn date", "transaction date", "value date"]
NARRATION_ALIASES = ["narration", "description", "transaction details", "note",
                      "notes", "transaction_text", "details"]
DEBIT_ALIASES = ["debit", "withdrawal amt", "withdrawal"]
CREDIT_ALIASES = ["credit", "deposit amt", "deposit"]
AMOUNT_ALIASES = ["amount"]
TYPE_ALIASES = ["type", "transaction_type", "income/expense", "drcr", "dr/cr"]
BALANCE_ALIASES = ["balance", "balance amt", "closing balance"]


def _find(cols_lower_map, aliases):
    for a in aliases:
        if a in cols_lower_map:
            return cols_lower_map[a]
    return None


class GenericParser(BaseParser):
    bank_name = "GENERIC"

    def matches(self, df: pd.DataFrame) -> bool:
        return True  # always usable as last resort

    def parse(self, df, source_file, source_format):
        cols = {c.strip().lower(): c for c in df.columns}
        date_col = _find(cols, DATE_ALIASES)
        narr_col = _find(cols, NARRATION_ALIASES)
        debit_col = _find(cols, DEBIT_ALIASES)
        credit_col = _find(cols, CREDIT_ALIASES)
        amount_col = _find(cols, AMOUNT_ALIASES)
        type_col = _find(cols, TYPE_ALIASES)
        bal_col = _find(cols, BALANCE_ALIASES)

        txns = []
        for _, row in df.iterrows():
            amount = self._resolve_amount(row, debit_col, credit_col, amount_col, type_col)
            narration = str(row.get(narr_col, "")).strip() if narr_col else ""
            t = Transaction(
                date=self._to_iso_date(row.get(date_col)) if date_col else None,
                raw_narration=narration,
                amount=amount,
                balance=self._to_float(row.get(bal_col), default=None) if bal_col else None,
                type="credit" if amount >= 0 else "debit",
                bank=self.bank_name,
                source_file=source_file,
                source_format=source_format,
            )
            t.compute_id()
            txns.append(t)
        return txns

    def _resolve_amount(self, row, debit_col, credit_col, amount_col, type_col):
        if debit_col or credit_col:
            deb = self._to_float(row.get(debit_col)) if debit_col else 0.0
            cred = self._to_float(row.get(credit_col)) if credit_col else 0.0
            return cred - deb
        if amount_col:
            amt = self._to_float(row.get(amount_col))
            if type_col:
                t = str(row.get(type_col, "")).strip().lower()
                if t in ("debit", "expense", "dr", "withdrawal"):
                    return -abs(amt)
                if t in ("credit", "income", "cr", "deposit"):
                    return abs(amt)
            return amt
        return 0.0
