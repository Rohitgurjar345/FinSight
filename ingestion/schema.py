"""Canonical transaction schema — every parser normalizes into this shape."""
from dataclasses import dataclass, asdict
from typing import Optional
import hashlib


@dataclass
class Transaction:
    date: str                      # ISO YYYY-MM-DD
    raw_narration: str
    amount: float                  # signed: +credit, -debit
    type: str                      # "debit" | "credit"
    bank: str                      # HDFC | ICICI | SBI | GENERIC
    source_file: str
    source_format: str             # csv | xlsx | pdf
    value_date: Optional[str] = None
    balance: Optional[float] = None
    clean_narration: Optional[str] = None
    transaction_id: Optional[str] = None
    category: Optional[str] = None
    category_confidence: Optional[float] = None

    def compute_id(self):
        basis = f"{self.date}|{self.raw_narration}|{self.amount}|{self.source_file}"
        self.transaction_id = hashlib.sha256(basis.encode()).hexdigest()[:16]
        return self.transaction_id

    def to_dict(self):
        return asdict(self)
