"""Single entry point: upload bank statement(s), everything that can be
derived automatically from them runs immediately — categorization, Health
Score, and the RAG assistant. Loan Pre-Assessment is the one exception (see
loan_preassessment() docstring) — it needs data that genuinely cannot come
from a bank statement, and this platform will not fabricate it.
"""
from ingestion.pipeline import run, run_batch
from categorization.categorizer import Categorizer
from analytics.health_score import FinancialHealthScore
from analytics.profile_estimator import estimate_profile, LOAN_FIELDS_REQUIRING_USER_INPUT
from loan_assessment.model import LoanAssessor, FEATURES as LOAN_FEATURES
from rag_assistant.assistant import FinancialAssistant

HEALTH_SCORE_MODEL_PATH = "data/models/health_score_percentiles.joblib"
LOAN_MODEL_PATH = "data/models/loan_assessment_model.joblib"

REQUIRED_LOAN_MANUAL_FIELDS = LOAN_FIELDS_REQUIRING_USER_INPUT + ["existing_loan"]


class FinancialPlatform:
    def __init__(self, filepaths):
        """Runs the moment you upload — ingestion + categorization happen here."""
        if isinstance(filepaths, str):
            filepaths = [filepaths]

        if len(filepaths) == 1:
            self.transactions = run(filepaths[0])
            self.ingestion_report = {"files_processed": 1, "files_failed": 0, "errors": []}
        else:
            result = run_batch(filepaths)
            self.transactions = result["transactions"]
            self.ingestion_report = {
                "files_processed": result["files_processed"],
                "files_failed": result["files_failed"],
                "errors": result["errors"],
                "duplicates_removed_cross_file": result["duplicates_removed_cross_file"],
            }

        Categorizer().categorize_transactions(self.transactions)
        self._assistant = None  # built lazily, only when first question is asked

    # ---- Module 3: automatic ----
    def health_score(self) -> dict:
        """Fully automatic — estimates a profile from your transactions and scores it.
        Returns the score, its breakdown, the estimated profile used, and the
        assumptions behind it (see analytics/profile_estimator.py)."""
        estimate = estimate_profile(self.transactions)
        scorer = FinancialHealthScore().load(HEALTH_SCORE_MODEL_PATH)
        result = scorer.score(estimate["profile"])
        result["estimated_profile"] = estimate["profile"]
        result["estimation_warnings"] = estimate["warnings"]
        result["months_covered"] = estimate["months_covered"]
        return result

    # ---- Module 4: NOT fully automatic — by necessity, not oversight ----
    def loan_preassessment(self, age: int, credit_score: int, assets: float,
                            existing_loan: int, criminal_record: int) -> dict:
        """Age, credit score, assets, and criminal record CANNOT be derived
        from a bank statement — no amount of transaction analysis reveals
        someone's credit score or legal history. These five arguments are
        required with no defaults, on purpose: fabricating them would make
        the loan pre-assessment actively misleading rather than just
        incomplete. Income and debt-to-income ARE auto-estimated from your
        transactions.

        CAVEAT: the estimated income here uses the same monthly-average logic
        as health_score() (calibrated against data.csv's scale), while the
        loan model was trained on Loan_Prediction.csv, whose income range
        suggests a possibly different scale/period. Treat the auto-estimated
        income/DTI as a rough estimate, not a verified figure — provide your
        own income figure if you have a more accurate one.
        """
        estimate = estimate_profile(self.transactions)
        income = estimate["monthly_income"]
        debt_to_income_ratio = estimate["debt_to_income_ratio"]

        applicant = {
            "age": age, "income": income, "assets": assets,
            "credit_score": credit_score, "debt_to_income_ratio": debt_to_income_ratio,
            "existing_loan": existing_loan, "criminal_record": criminal_record,
        }

        assessor = LoanAssessor().load(LOAN_MODEL_PATH)
        result = assessor.assess(applicant)
        result["estimated_from_transactions"] = {"income": income, "debt_to_income_ratio": debt_to_income_ratio}
        result["manually_provided"] = {"age": age, "credit_score": credit_score,
                                        "assets": assets, "existing_loan": existing_loan,
                                        "criminal_record": criminal_record}
        result["scale_caveat"] = (
            "Income/DTI were auto-estimated from your transactions using health-score-style "
            "monthly averaging, which may not match the income scale/period the loan model "
            "was trained on (Loan_Prediction.csv). Treat this as a rough estimate."
        )
        return result

    # ---- Module 5: automatic once you ask ----
    def ask(self, query: str) -> dict:
        if self._assistant is None:
            self._assistant = FinancialAssistant(self.transactions)
        return self._assistant.ask(query)

    def full_report(self, loan_manual_fields: dict = None) -> dict:
        """One call: everything that's automatic, plus loan pre-assessment
        IF you supply the fields that can't be derived — otherwise a clear
        note explaining exactly what's still needed and why."""
        report = {
            "ingestion": self.ingestion_report,
            "transaction_count": len(self.transactions),
            "health_score": self.health_score(),
        }
        if loan_manual_fields:
            missing = [f for f in REQUIRED_LOAN_MANUAL_FIELDS if f not in loan_manual_fields]
            if missing:
                report["loan_preassessment"] = {
                    "error": f"Missing required fields (cannot be derived automatically): {missing}"
                }
            else:
                report["loan_preassessment"] = self.loan_preassessment(**loan_manual_fields)
        else:
            report["loan_preassessment"] = {
                "status": "not_run",
                "reason": f"Requires manual input that cannot be derived from a bank "
                          f"statement: {REQUIRED_LOAN_MANUAL_FIELDS}. Call "
                          f"platform.loan_preassessment(**your_fields) directly, or pass "
                          f"loan_manual_fields={{...}} to full_report().",
            }
        return report
