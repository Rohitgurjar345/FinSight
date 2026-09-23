import re

_PATTERNS = [
    r"\bref:?\s*[a-z0-9]+\b",           # Ref:37c9a05e
    r"\btxn[a-z0-9]+\b",                 # TXN684df950
    r"\bupi[/-][a-z0-9./-]+\b",          # UPI/xxx/xxx
    r"\b\d{10,}\b",                      # long reference/account numbers
    r"\bamount:?\s*inr\s*[\d.,]+\b",     # "Amount: INR 3436.58"
    r"[|]",                              # pipe separators
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def clean(narration: str) -> str:
    if not narration:
        return ""
    text = narration
    for pat in _COMPILED:
        text = pat.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
