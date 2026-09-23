"""RAG conversational assistant, grounded in the user's own transactions.

Flow: retrieve relevant transactions (TF-IDF) -> if ANTHROPIC_API_KEY is set
in the environment, call the Anthropic API with that context -> otherwise
fall back to the no-key template layer.

SECURITY NOTE: the API key is read ONLY from the environment variable
ANTHROPIC_API_KEY. It is never hardcoded, logged, or accepted as a plain
function argument — this is deliberate so a key never ends up committed to
source, printed in a demo, or pasted somewhere unsafe.
"""
import os
from rag_assistant.retriever import TransactionRetriever
from rag_assistant import no_key_fallback

DEFAULT_MODEL = "claude-sonnet-5"


class FinancialAssistant:
    def __init__(self, transactions: list):
        self.transactions = transactions
        self.retriever = TransactionRetriever()
        self.retriever.build_index(transactions)

    def ask(self, query: str, k: int = 5) -> dict:
        retrieved = self.retriever.retrieve(query, k=k)
        api_key = os.environ.get("ANTHROPIC_API_KEY")

        if api_key:
            answer, used_fallback = self._ask_via_api(query, retrieved, api_key)
            source = "anthropic_api" if not used_fallback else "template_fallback_after_api_error"
        else:
            answer = no_key_fallback.answer(query, self.transactions)
            source = "template_fallback"

        return {
            "answer": answer,
            "source": source,
            "retrieved_count": len(retrieved),
            "retrieved_transactions": [
                {"date": t.date, "narration": t.clean_narration or t.raw_narration,
                 "category": t.category, "amount": t.amount}
                for t in retrieved
            ],
        }

    def _ask_via_api(self, query: str, retrieved: list, api_key: str):
        """Real Anthropic API call. Untested in this sandbox (no network/key
        available here) — falls back safely to the template layer if the
        call fails for any reason, so a bad/expired/rate-limited key never
        crashes the assistant."""
        try:
            import anthropic
        except ImportError:
            return (no_key_fallback.answer(query, self.transactions)
                    + " (Note: 'anthropic' package not installed — install it to enable live answers.)"), True

        context = "\n".join(
            f"- {t.date} | {t.clean_narration or t.raw_narration} | "
            f"{t.category or 'uncategorized'} | {t.amount:,.2f}"
            for t in retrieved
        ) or "(no matching transactions found)"

        system_prompt = (
            "You are a personal finance assistant. Answer ONLY using the transaction "
            "data provided below. If the data doesn't contain the answer, say so plainly "
            "rather than guessing. Be concise."
        )
        user_prompt = f"Relevant transactions:\n{context}\n\nQuestion: {query}"

        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text, False
        except Exception as e:
            fallback_answer = no_key_fallback.answer(query, self.transactions)
            return f"{fallback_answer} (Note: API call failed — {type(e).__name__} — used fallback.)", True
