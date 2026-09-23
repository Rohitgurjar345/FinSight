import joblib
from sklearn.linear_model import LogisticRegression
from categorization.embedder import TfidfEmbedder


class Classifier:
    def __init__(self):
        self.embedder = TfidfEmbedder()
        self.model = LogisticRegression(max_iter=1000)

    def fit(self, texts, labels):
        X = self.embedder.fit_transform(texts)
        self.model.fit(X, labels)

    def predict(self, texts):
        X = self.embedder.transform(texts)
        preds = self.model.predict(X)
        probs = self.model.predict_proba(X).max(axis=1)
        return list(zip(preds, probs))

    def save(self, dirpath):
        self.embedder.save(f"{dirpath}/tfidf_vectorizer.joblib")
        joblib.dump(self.model, f"{dirpath}/logreg_model.joblib")

    def load(self, dirpath):
        self.embedder.load(f"{dirpath}/tfidf_vectorizer.joblib")
        self.model = joblib.load(f"{dirpath}/logreg_model.joblib")
        return self
