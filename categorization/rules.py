"""Rule-based keyword categorization — first pass, high confidence, editable."""

CATEGORY_RULES = {
    "food": ["zomato", "swiggy", "restaurant", "cafe", "starbucks", "dominos",
              "mcdonald", "kfc", "food", "snack", "grocery", "grocer", "dining"],
    "travel": ["makemytrip", "irctc", "uber", "ola", "flight", "airlines",
               "hotel", "booking.com", "goibibo", "train", "taxi", "cab"],
    "shopping": ["amazon", "flipkart", "myntra", "ikea", "mall", "shopping",
                 "electronics", "clothing", "store"],
    "investment": ["mutual fund", "sip", "zerodha", "groww", "stocks",
                   "investment", "dividend", "ppf", "nps"],
    "emi": ["emi", "loan repayment", "bajaj finserv", "loan installment"],
    "utilities": ["electricity", "water bill", "gas bill", "utility",
                  "utilities", "broadband", "wifi", "recharge", "mobile bill"],
    "healthcare": ["hospital", "pharmacy", "medical", "doctor", "clinic",
                   "healthcare", "medicine", "diagnostic"],
    "education": ["tuition", "school fee", "college", "course", "udemy",
                  "education", "book store"],
    "entertainment": ["netflix", "prime video", "hotstar", "movie", "cinema",
                      "spotify", "entertainment", "game", "concert"],
    "rent": ["rent", "landlord", "lease payment", "house rent"],
    "insurance": ["insurance", "premium payment", "lic ", "policy premium"],
}


def categorize(narration: str):
    """Returns (category, confidence) or (None, 0.0) if no rule matches."""
    if not narration:
        return None, 0.0
    text = narration.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw in text:
                return category, 1.0
    return None, 0.0
