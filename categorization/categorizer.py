import os
from categorization.rules import categorize as rule_categorize
from categorization.classifier import Classifier

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")
ML_CONFIDENCE_THRESHOLD = 0.55  # below this, flag for user review


class Categorizer:
    def __init__(self, model_dir=MODEL_DIR):
        self._ml = None
        self._model_dir = model_dir

    def _load_ml(self):
        if self._ml is None:
            self._ml = Classifier().load(self._model_dir)
        return self._ml

    def categorize(self, narration: str, clean_narration: str = None):
        """Rule engine first; ML classifier fallback for anything rules miss.
        Returns dict: category, confidence, source ("rule"|"ml"|"low_confidence")."""
        text = clean_narration if clean_narration is not None else narration

        category, confidence = rule_categorize(text)
        if category:
            return {"category": category, "confidence": confidence, "source": "rule"}

        ml = self._load_ml()
        (pred_category, pred_confidence), = ml.predict([text])
        if pred_confidence >= ML_CONFIDENCE_THRESHOLD:
            return {"category": pred_category, "confidence": float(pred_confidence), "source": "ml"}
        return {"category": pred_category, "confidence": float(pred_confidence), "source": "low_confidence"}

    def categorize_transactions(self, transactions: list):
        """Mutates and returns Transaction objects in place with category set."""
        for t in transactions:
            result = self.categorize(t.raw_narration, t.clean_narration)
            t.category = result["category"]
            t.category_confidence = result["confidence"]
        return transactions
