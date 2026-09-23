"""No-key fallback layer. When no Anthropic API key is configured, the
assistant still needs to degrade gracefully rather than fail outright.
This module answers a fixed set of common question patterns directly from
the user's transaction data via pandas aggregation — no LLM involved, so
it's exact and free, at the cost of only covering known phrasings.
"""
import re
from datetime import date
from collections import Counter


def _to_month_bounds(ref_date, months_back=0):
    """Returns (year, month) for `months_back` months before ref_date's month."""
    month = ref_date.month - months_back
    year = ref_date.year
    while month <= 0:
        month += 12
        year -= 1
    return year, month


CATEGORY_PATTERN = re.compile(
    r"spen[dt].*(?:on|for)\s+([a-zA-Z ]+?)(?:\s+(?:last|this)\s+month|\s*\?|$)", re.IGNORECASE
)
LAST_MONTH_PATTERN = re.compile(r"last month", re.IGNORECASE)
THIS_MONTH_PATTERN = re.compile(r"this month", re.IGNORECASE)
TOP_CATEGORY_PATTERN = re.compile(r"(top|biggest|highest|largest)\s+(?:spending\s+)?categor", re.IGNORECASE)
TOTAL_SPEND_PATTERN = re.compile(r"total\s+(?:spend|expense|spent)", re.IGNORECASE)
COUNT_PATTERN = re.compile(r"how many\s+transactions", re.IGNORECASE)

# Module 2's rule engine (categorization/rules.py) only produces these 9
# category labels. Free-text queries rarely use the label name itself
# ("groceries" not "food"), so map common synonyms to the actual label
# before matching — otherwise a perfectly reasonable question silently
# returns "no transactions found" even when matching data exists.
CATEGORY_SYNONYMS = {
    "grocery": "food", "groceries": "food", "restaurant": "food", "dining": "food",
    "medical": "healthcare", "doctor": "healthcare", "hospital": "healthcare", "medicine": "healthcare",
    "bill": "utilities", "bills": "utilities", "electricity": "utilities", "water bill": "utilities",
    "loan": "emi", "loans": "emi", "installment": "emi",
    "movie": "entertainment", "movies": "entertainment", "netflix": "entertainment", "subscription": "entertainment",
    "school": "education", "college": "education", "tuition": "education",
    "stocks": "investment", "mutual fund": "investment", "sip": "investment",
}


def _normalize_category(phrase: str) -> str:
    phrase = phrase.strip().lower()
    return CATEGORY_SYNONYMS.get(phrase, phrase)


def answer(query: str, transactions: list, reference_date=None) -> str:
    """Best-effort direct answer from transaction data. Returns a plain
    string; if nothing matches, returns a message describing what CAN be
    asked instead of pretending to understand."""
    if not transactions:
        return "I don't have any transactions loaded yet to answer questions about."

    ref_date = reference_date or max((t.date for t in transactions if t.date), default=None)
    if ref_date and isinstance(ref_date, str):
        ref_date = date.fromisoformat(ref_date)

    if COUNT_PATTERN.search(query):
        return f"You have {len(transactions)} transactions on record."

    if TOP_CATEGORY_PATTERN.search(query):
        totals = Counter()
        for t in transactions:
            if t.amount < 0:
                totals[t.category or "uncategorized"] += abs(t.amount)
        if not totals:
            return "I don't have enough categorized expense data to determine your top category."
        top_cat, top_amt = totals.most_common(1)[0]
        return f"Your top spending category is '{top_cat}' at {top_amt:,.2f} total."

    if TOTAL_SPEND_PATTERN.search(query):
        total = sum(abs(t.amount) for t in transactions if t.amount < 0)
        return f"Your total recorded spending is {total:,.2f} across {len(transactions)} transactions."

    cat_match = CATEGORY_PATTERN.search(query)
    if cat_match and ref_date:
        target_category = _normalize_category(cat_match.group(1))
        months_back = 1 if LAST_MONTH_PATTERN.search(query) else 0
        year, month = _to_month_bounds(ref_date, months_back)
        matched = [
            t for t in transactions
            if t.amount < 0 and t.category and target_category in t.category.lower()
            and t.date and t.date[:7] == f"{year:04d}-{month:02d}"
        ]
        total = sum(abs(t.amount) for t in matched)
        period = "last month" if months_back else "this month"
        if not matched:
            return f"I found no '{target_category}' transactions {period} ({year:04d}-{month:02d})."
        return f"You spent {total:,.2f} on {target_category} {period} ({len(matched)} transactions)."

    return (
        "I can answer questions like: 'how much did I spend on food last month?', "
        "'what's my top spending category?', 'what's my total spend?', or "
        "'how many transactions do I have?'. Try rephrasing your question along those lines."
    )
