"""Bridges Module 2's output (categorized transactions) to the structured
profile inputs that Module 3 (Health Score) and Module 4 (Loan
Pre-Assessment) actually need. This is an ESTIMATE, not ground truth — it
makes real assumptions that are documented below and surfaced as warnings,
not hidden.
"""
from collections import defaultdict

# Module 2 only produces these 9 lowercase category labels (categorization/rules.py).
# Module 3 expects title-case columns matching data.csv's schema. Several of
# Module 2's categories don't map cleanly (e.g. "food" blends groceries AND
# restaurant spend, which data.csv splits into separate Groceries/Eating_Out
# columns) — mapped to the closest single column as a documented approximation.
CATEGORY_TO_EXPENSE_COL = {
    "food": "Groceries",       # approximation: blends groceries + dining
    "travel": "Transport",     # approximation: blends trips + daily commute
    "shopping": "Miscellaneous",
    "emi": "Loan_Repayment",
    "utilities": "Utilities",
    "healthcare": "Healthcare",
    "education": "Education",
    "entertainment": "Entertainment",
    "rent": "Rent",
    "insurance": "Insurance",
    # "investment" is deliberately excluded — it's savings/allocation, not
    # consumption, and isn't one of Module 3's EXPENSE_COLS.
}

# Module 2's "rent" and "insurance" categories are keyword-rule-based only
# (added specifically to improve this estimate) — if a real rent/insurance
# debit uses wording the rules don't recognize, it will still be missed and
# silently fall into Miscellaneous instead. Checked dynamically below.
NOT_DERIVABLE_EXPENSE_COLS = ["Rent", "Insurance"]  # kept for reference; not always 0 anymore

ALL_EXPENSE_COLS = ["Rent", "Loan_Repayment", "Insurance", "Groceries", "Transport",
                     "Eating_Out", "Entertainment", "Utilities", "Healthcare",
                     "Education", "Miscellaneous"]

# Module 4 fields with NO signal in a bank statement at all — must come from the user.
LOAN_FIELDS_REQUIRING_USER_INPUT = ["age", "credit_score", "assets", "criminal_record"]


def _months_covered(transactions: list) -> float:
    dates = [t.date for t in transactions if t.date]
    if not dates:
        return 1.0
    from datetime import date
    d_min = date.fromisoformat(min(dates))
    d_max = date.fromisoformat(max(dates))
    months = (d_max.year - d_min.year) * 12 + (d_max.month - d_min.month) + 1
    return max(months, 1)


def estimate_profile(transactions: list) -> dict:
    """Returns {"profile": {...health-score-shaped dict...}, "warnings": [...],
    "months_covered": n, "monthly_income": float, "debt_to_income_ratio": float,
    "has_loan": bool} — all figures are MONTHLY AVERAGES over the uploaded
    statement period, to match the monthly scale data.csv appears to use."""
    warnings = []
    months = _months_covered(transactions)

    total_income = sum(t.amount for t in transactions if t.amount > 0)
    monthly_income = total_income / months

    category_totals = defaultdict(float)
    for t in transactions:
        if t.amount >= 0:
            continue
        if t.category == "investment":
            continue  # savings/allocation, not consumption — must not count as an expense
        col = CATEGORY_TO_EXPENSE_COL.get(t.category)
        if col:
            category_totals[col] += abs(t.amount)
        else:
            category_totals["Miscellaneous"] += abs(t.amount)  # genuinely uncategorized

    profile = {"Income": round(monthly_income, 2)}
    for col in ALL_EXPENSE_COLS:
        profile[col] = round(category_totals.get(col, 0.0) / months, 2)

    warnings.append(
        f"'food' category was mapped entirely to Groceries — restaurant/dining "
        f"spend within it is not separated out, which may overstate Groceries "
        f"and understate Eating_Out."
    )
    if profile["Rent"] == 0:
        warnings.append("Rent came back as 0 — either you have no rent debits, or none "
                         "matched the 'rent' keyword rule (Module 2's rent detection is "
                         "keyword-based only). This will understate essential expenses.")
    if profile["Insurance"] == 0:
        warnings.append("Insurance came back as 0 for the same reason as Rent above.")
    if months < 2:
        warnings.append(
            f"Only {months:.0f} month of transaction history was found — monthly "
            f"averages from a single month are far less reliable than several "
            f"months of data."
        )

    total_expense = sum(profile[c] for c in ALL_EXPENSE_COLS)
    if total_expense > 0:
        dominant_col, dominant_amt = max(((c, profile[c]) for c in ALL_EXPENSE_COLS), key=lambda x: x[1])
        dominant_share = dominant_amt / total_expense
        if dominant_share > 0.6:
            warnings.append(
                f"{dominant_col} makes up {dominant_share:.0%} of total categorized "
                f"expenses, which will pull category-diversification down sharply. If this "
                f"looks too concentrated to be real spending behavior, it's likely Module 2's "
                f"categorizer over-assigning generic/ambiguous narrations to one category (a "
                f"documented limitation) rather than genuine spending — check "
                f"category_confidence on the underlying transactions before trusting this."
            )

    monthly_loan_repayment = profile["Loan_Repayment"]
    debt_to_income_ratio = round(monthly_loan_repayment / monthly_income, 4) if monthly_income > 0 else 0.0
    has_loan = monthly_loan_repayment > 0

    return {
        "profile": profile,
        "warnings": warnings,
        "months_covered": months,
        "monthly_income": round(monthly_income, 2),
        "debt_to_income_ratio": debt_to_income_ratio,
        "has_loan": has_loan,
    }
