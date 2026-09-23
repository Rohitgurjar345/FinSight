"""Retrieval half of RAG: builds a lightweight TF-IDF index over a single
user's own transactions (never a shared/global corpus) and returns the
most relevant ones for a natural-language query.

TF-IDF chosen over SBERT per project decision: consistent with Module 2,
no heavy model download, deterministic, and the retrieval corpus here is
small (one user's transaction history) where semantic embeddings buy less
than they would over a large heterogeneous document set.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _transaction_to_text(t) -> str:
    """Flattens a transaction into a text blob for indexing."""
    narration = t.clean_narration or t.raw_narration or ""
    category = t.category or "uncategorized"
    return f"{narration} {category} {t.date} amount {abs(t.amount)}"


class TransactionRetriever:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
        self.matrix = None
        self.transactions = []

    def build_index(self, transactions: list):
        self.transactions = transactions
        if not transactions:
            self.matrix = None
            return
        texts = [_transaction_to_text(t) for t in transactions]
        self.matrix = self.vectorizer.fit_transform(texts)

    def retrieve(self, query: str, k: int = 5) -> list:
        """Returns up to k transactions most relevant to the query."""
        if self.matrix is None or not self.transactions:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix).flatten()
        top_idx = scores.argsort()[::-1][:k]
        return [self.transactions[i] for i in top_idx if scores[i] > 0]
