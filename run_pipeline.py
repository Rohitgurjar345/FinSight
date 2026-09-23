"""Chains ALL FIVE modules together in one call:
ingestion (1) -> categorization (2) -> profile estimation -> health score (3)
-> loan pre-assessment (4, asks for the few fields a bank statement can't
reveal) -> RAG assistant (5) for follow-up questions.

Usage:
    python -m run_pipeline data/raw/bank.xlsx
    python -m run_pipeline data/raw/statement_jan.csv data/raw/statement_feb.xlsx
"""
import sys
from ingestion.pipeline import run, run_batch
from categorization.categorizer import Categorizer
from analytics.profile_estimator import estimate_profile, LOAN_FIELDS_REQUIRING_USER_INPUT
from analytics.health_score import FinancialHealthScore
from loan_assessment.model import LoanAssessor
from rag_assistant.assistant import FinancialAssistant


def ingest_and_categorize(filepaths: list):
    if len(filepaths) == 1:
        transactions = run(filepaths[0])
    else:
        result = run_batch(filepaths)
        transactions = result["transactions"]
        if result["errors"]:
            print(f"Warning: {result['files_failed']} file(s) failed: {result['errors']}")
    Categorizer().categorize_transactions(transactions)
    return transactions


def run_health_score(estimate: dict):
    print("\n--- Module 3: Financial Health Score (auto-derived from your statement) ---")
    for w in estimate["warnings"]:
        print(f"  [assumption] {w}")
    hs = FinancialHealthScore().load("data/models/health_score_percentiles.joblib")
    result = hs.score(estimate["profile"])
    print(f"  Score: {result['score']}/100")
    for metric, d in result["breakdown"].items():
        print(f"    {metric}: raw={d['raw_value']}, percentile={d['population_percentile']}%, "
              f"weight={d['weight']}, contributes={d['contribution']}")
    return result


def run_loan_assessment(estimate: dict, interactive: bool = True):
    print("\n--- Module 4: Loan Pre-Assessment ---")
    print("  Auto-derived from your statement: income (monthly avg), debt-to-income ratio, existing-loan flag.")
    print("  A bank statement has NO signal for age, credit score, assets, or criminal record —")
    print("  these genuinely cannot be inferred from transaction data, so they're asked directly.")
    print("  [caveat] Loan_Prediction.csv's original income units (monthly vs. annual) aren't")
    print("  documented — your derived MONTHLY income is used as-is, which may not match the")
    print("  scale the model was trained on. Treat this result with extra caution beyond the")
    print("  standard pre-assessment disclaimer.")

    applicant = {
        "income": estimate["monthly_income"],
        "debt_to_income_ratio": estimate["debt_to_income_ratio"],
        "existing_loan": int(estimate["has_loan"]),
    }

    if interactive:
        for field in LOAN_FIELDS_REQUIRING_USER_INPUT:
            while True:
                raw = input(f"  Enter your {field.replace('_', ' ')}: ").strip()
                try:
                    applicant[field] = float(raw) if "." in raw else int(raw)
                    break
                except ValueError:
                    print("    Please enter a number.")
    else:
        print("  [non-interactive mode] Skipping loan assessment — required fields not supplied.")
        return None

    assessor = LoanAssessor().load("data/models/loan_assessment_model.joblib")
    result = assessor.assess(applicant)
    print(f"  Readiness tier: {result['readiness_tier']}  (probability: {result['approval_probability']})")
    print(f"  {result['disclaimer']}")
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m run_pipeline <file1> [file2] [file3] ...")
        sys.exit(1)

    transactions = ingest_and_categorize(sys.argv[1:])
    print(f"Ingested + categorized {len(transactions)} transactions from {len(sys.argv) - 1} file(s).")

    estimate = estimate_profile(transactions)
    run_health_score(estimate)
    run_loan_assessment(estimate)

    print("\n--- Module 5: Ask questions about your statement (empty line to quit) ---")
    assistant = FinancialAssistant(transactions)
    while True:
        q = input("> ").strip()
        if not q:
            break
        result = assistant.ask(q)
        print(f"  {result['answer']}  [source: {result['source']}]")

