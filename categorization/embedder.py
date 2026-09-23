"""Pluggable text-embedding interface. TF-IDF is the default, lightweight
implementation. A heavier embedder (e.g. SBERT) can be swapped in later by
implementing the same fit/transform interface — no changes needed elsewhere."""
from abc import ABC, abstractmethod
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib


class BaseEmbedder(ABC):
    @abstractmethod
    def fit_transform(self, texts):
        ...

    @abstractmethod
    def transform(self, texts):
        ...

    @abstractmethod
    def save(self, path):
        ...

    @abstractmethod
    def load(self, path):
        ...


class TfidfEmbedder(BaseEmbedder):
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))

    def fit_transform(self, texts):
        return self.vectorizer.fit_transform(texts)

    def transform(self, texts):
        return self.vectorizer.transform(texts)

    def save(self, path):
        joblib.dump(self.vectorizer, path)

    def load(self, path):
        self.vectorizer = joblib.load(path)
        return self
