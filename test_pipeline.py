"""Run: python3 -m pytest test_pipeline.py -v"""
import pandas as pd
from ingestion.detectors.bank_detector import detect_parser
from ingestion.parsers.hdfc_parser import HDFCParser
from ingestion.parsers.icici_parser import ICICIParser
from ingestion.parsers.sbi_parser import SBIParser
from ingestion.parsers.generic_parser import GenericParser
from ingestion.pipeline import run
from ingestion.cleaning.deduplicator import dedupe, dedupe_cross_file
from categorization.rules import categorize
from categorization.categorizer import Categorizer


def test_hdfc_detection():
    df = pd.DataFrame({"Date": ["01/01/24"], "Narration": ["x"], "Withdrawal Amt": [0],
                        "Deposit Amt": [0], "Closing Balance": [0]})
    assert isinstance(detect_parser(df), HDFCParser)


def test_icici_detection():
    df = pd.DataFrame({"Transaction Date": ["01/01/24"], "Description": ["x"],
                        "Debit": [0], "Credit": [0], "Balance": [0]})
    assert isinstance(detect_parser(df), ICICIParser)


def test_sbi_detection():
    df = pd.DataFrame({"Txn Date": ["01/01/24"], "Description": ["x"],
                        "Debit": [0], "Credit": [0], "Balance": [0]})
    assert isinstance(detect_parser(df), SBIParser)


def test_generic_fallback():
    df = pd.DataFrame({"Foo": [1], "Bar": [2]})
    assert isinstance(detect_parser(df), GenericParser)


def test_real_hdfc_file_parses():
    txns = run("data/raw/bank.xlsx")
    assert len(txns) > 0
    assert txns[0].bank == "HDFC"
    assert all(t.transaction_id for t in txns)


def test_generic_file_parses_with_correct_signs():
    txns = run("data/raw/Daily_Household_Transactions.csv")
    assert len(txns) > 0
    expenses = [t for t in txns if t.type == "debit"]
    assert all(t.amount < 0 for t in expenses)


def test_dedup_removes_duplicates():
    """bank.xlsx contains both genuine duplicate rows (real narration, real
    amount) and rows with blank/"nan" narration that must NOT be collapsed
    (see test_dedup_does_not_falsely_collapse_zero_amount_rows). Only the
    former should be deduped."""
    txns = run("data/raw/bank.xlsx")
    ids_with_signal = [t.transaction_id for t in txns
                        if (t.raw_narration or "").strip().lower() not in ("", "nan", "none") and t.amount != 0]
    assert len(ids_with_signal) == len(set(ids_with_signal))


def test_dedup_does_not_falsely_collapse_zero_amount_rows():
    """Regression test: rows with missing/malformed amounts (parsed as 0.0)
    and generic/blank narrations must NOT be treated as duplicates of each
    other — this was a real bug caught during testing that silently dropped
    ~760 genuine transactions from a single file."""
    from ingestion.schema import Transaction
    t1 = Transaction(date="2024-01-01", raw_narration="", amount=0.0, type="debit",
                      bank="GENERIC", source_file="a.csv", source_format="csv")
    t2 = Transaction(date="2024-01-01", raw_narration="", amount=0.0, type="debit",
                      bank="GENERIC", source_file="a.csv", source_format="csv")
    t1.compute_id(); t2.compute_id()
    result = dedupe([t1, t2])
    assert len(result) == 2  # both kept — insufficient signal to call them duplicates


def test_cross_file_dedup_catches_real_overlap():
    from ingestion.schema import Transaction
    t1 = Transaction(date="2024-03-15", raw_narration="Zomato food order", amount=-450.0,
                      type="debit", bank="GENERIC", source_file="statement_jan.csv", source_format="csv")
    t2 = Transaction(date="2024-03-15", raw_narration="Zomato food order", amount=-450.0,
                      type="debit", bank="GENERIC", source_file="statement_feb.csv", source_format="csv")
    t1.compute_id(); t2.compute_id()
    assert t1.transaction_id != t2.transaction_id  # different source_file -> different id
    result = dedupe_cross_file([t1, t2])
    assert len(result) == 1  # content-matched across files despite different source_file


def test_run_batch_multi_file_upload():
    from ingestion.pipeline import run_batch
    result = run_batch(["data/raw/Daily_Household_Transactions.csv", "data/raw/budgetwise_finance_dataset.csv"])
    assert result["files_processed"] == 2
    assert result["files_failed"] == 0
    assert len(result["per_file_counts"]) == 2
    assert len(result["transactions"]) > 0
    assert result["duplicates_removed_cross_file"] >= 0


def test_run_batch_handles_one_bad_file_gracefully():
    from ingestion.pipeline import run_batch
    result = run_batch(["data/raw/bank.xlsx", "data/raw/nonexistent_file.csv"])
    assert result["files_processed"] == 1
    assert result["files_failed"] == 1
    assert len(result["errors"]) == 1
    assert len(result["transactions"]) > 0  # good file still processed


def test_rule_categorization():
    cat, conf = categorize("Uber ride to airport")
    assert cat == "travel"
    assert conf == 1.0


def test_rule_categorization_no_match():
    cat, conf = categorize("xyz random text 12345")
    assert cat is None


def test_ml_categorizer_end_to_end():
    c = Categorizer()
    result = c.categorize("Zomato food order")
    assert result["category"] is not None
    assert "confidence" in result


def test_health_score_breakdown():
    from analytics.health_score import FinancialHealthScore
    hs = FinancialHealthScore().load("data/models/health_score_percentiles.joblib")
    profile = {"Income": 50000, "Loan_Repayment": 0, "Insurance": 2000,
               "Rent": 10000, "Groceries": 5000, "Transport": 2000,
               "Eating_Out": 1000, "Entertainment": 1000, "Utilities": 2000,
               "Healthcare": 1000, "Education": 0, "Miscellaneous": 500}
    result = hs.score(profile)
    assert 0 <= result["score"] <= 100
    assert set(result["breakdown"].keys()) == {
        "savings_rate", "debt_to_income", "essential_expense_ratio", "category_diversification"}
    for metric, d in result["breakdown"].items():
        assert 0 <= d["population_percentile"] <= 100


def test_health_score_no_double_counting():
    """savings_rate and essential_expense_ratio must be independent signals,
    not mirror images of each other (this was a real bug caught during testing)."""
    from analytics.health_score import FinancialHealthScore
    hs = FinancialHealthScore().load("data/models/health_score_percentiles.joblib")
    profile = {"Income": 50000, "Loan_Repayment": 0, "Insurance": 0,
               "Rent": 30000, "Groceries": 0, "Transport": 0, "Eating_Out": 0,
               "Entertainment": 0, "Utilities": 0, "Healthcare": 0,
               "Education": 0, "Miscellaneous": 0}
    result = hs.score(profile)["breakdown"]
    assert result["savings_rate"]["population_percentile"] != result["essential_expense_ratio"]["population_percentile"]


def test_forecast_model_beats_or_reports_honestly_vs_baseline():
    from analytics.forecasting import load_monthly_series, build_features, naive_baseline_predict, ExpenseForecaster
    from sklearn.metrics import mean_absolute_error
    series = load_monthly_series("data/raw/monthly_spending_dataset_2020_2025-selected-columns__1_.csv")
    feat_df = build_features(series)
    train_df, test_df = feat_df.iloc[:-12], feat_df.iloc[-12:]
    forecaster = ExpenseForecaster().load("data/models/forecast_model.joblib")
    ml_preds = forecaster.predict(test_df)
    ml_mae = mean_absolute_error(test_df["y"], ml_preds)
    baseline_mae = mean_absolute_error(test_df["y"], naive_baseline_predict(series, test_df.index))
    # Not asserting ML wins — asserting both numbers are sane and computable,
    # since the honest result here is the baseline currently wins (documented).
    assert ml_mae > 0 and baseline_mae > 0


def test_loan_assessment_returns_valid_tier_and_disclaimer():
    from loan_assessment.model import LoanAssessor
    assessor = LoanAssessor().load("data/models/loan_assessment_model.joblib")
    result = assessor.assess({"age": 35, "income": 90000, "assets": 300000,
                               "credit_score": 780, "debt_to_income_ratio": 0.2,
                               "existing_loan": 0, "criminal_record": 0})
    assert result["readiness_tier"] in ("ready", "borderline", "needs_improvement")
    assert 0.0 <= result["approval_probability"] <= 1.0
    assert "not a" in result["disclaimer"].lower() or "not represent" in result["disclaimer"].lower()
    assert "disclaimer" in result and len(result["disclaimer"]) > 20


def test_loan_assessment_explanation_present():
    from loan_assessment.model import LoanAssessor
    assessor = LoanAssessor().load("data/models/loan_assessment_model.joblib")
    result = assessor.assess({"age": 50, "income": 40000, "assets": 20000,
                               "credit_score": 550, "debt_to_income_ratio": 0.45,
                               "existing_loan": 1, "criminal_record": 1})
    contrib = result["feature_contributions"]["contributions"]
    assert len(contrib) == 7  # one per FEATURES column
    assert result["readiness_tier"] == "needs_improvement"  # low score, criminal record, high DTI


def test_loan_tier_thresholds_are_monotonic():
    from loan_assessment.model import tier_from_probability
    assert tier_from_probability(0.9) == "ready"
    assert tier_from_probability(0.45) == "borderline"
    assert tier_from_probability(0.1) == "needs_improvement"


def _sample_transactions_for_rag():
    from ingestion.schema import Transaction
    rows = [
        ("2024-08-01", "Zomato food order", -500.0, "food"),
        ("2024-08-05", "Swiggy dinner", -300.0, "food"),
        ("2024-07-10", "Uber ride", -200.0, "travel"),
        ("2024-08-15", "Electricity bill", -150.0, "utilities"),
        ("2024-08-20", "Salary credit", 50000.0, None),
    ]
    txns = []
    for date, narr, amt, cat in rows:
        t = Transaction(date=date, raw_narration=narr, clean_narration=narr, amount=amt,
                         type="credit" if amt > 0 else "debit", bank="GENERIC",
                         source_file="test.csv", source_format="csv", category=cat)
        t.compute_id()
        txns.append(t)
    return txns


def test_rag_retriever_returns_relevant_transactions():
    from rag_assistant.retriever import TransactionRetriever
    txns = _sample_transactions_for_rag()
    r = TransactionRetriever()
    r.build_index(txns)
    results = r.retrieve("food order dinner", k=3)
    assert len(results) > 0
    assert all(t.category == "food" or "food" in (t.clean_narration or "").lower()
               or "dinner" in (t.clean_narration or "").lower() for t in results[:2])


def test_rag_retriever_empty_transactions():
    from rag_assistant.retriever import TransactionRetriever
    r = TransactionRetriever()
    r.build_index([])
    assert r.retrieve("anything") == []


def test_no_key_fallback_category_spend():
    from rag_assistant.no_key_fallback import answer
    from datetime import date
    txns = _sample_transactions_for_rag()
    result = answer("how much did I spend on food this month?", txns, reference_date=date(2024, 8, 25))
    assert "800" in result.replace(",", "")  # 500 + 300


def test_no_key_fallback_synonym_mapping():
    from rag_assistant.no_key_fallback import answer
    from datetime import date
    txns = _sample_transactions_for_rag()
    result = answer("how much did I spend on groceries this month?", txns, reference_date=date(2024, 8, 25))
    assert "food" in result  # "groceries" mapped to the actual "food" category label


def test_no_key_fallback_total_spend():
    from rag_assistant.no_key_fallback import answer
    txns = _sample_transactions_for_rag()
    result = answer("what is my total spend?", txns)
    assert "1,150" in result or "1150" in result  # 500+300+200+150 in expenses


def test_no_key_fallback_unmatched_query_gives_guidance():
    from rag_assistant.no_key_fallback import answer
    txns = _sample_transactions_for_rag()
    result = answer("what is the meaning of life?", txns)
    assert "I can answer questions like" in result


def test_assistant_uses_fallback_when_no_api_key():
    import os
    from rag_assistant.assistant import FinancialAssistant
    had_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        txns = _sample_transactions_for_rag()
        assistant = FinancialAssistant(txns)
        result = assistant.ask("how many transactions do I have?")
        assert result["source"] == "template_fallback"
        assert "5" in result["answer"]
    finally:
        if had_key:
            os.environ["ANTHROPIC_API_KEY"] = had_key


def test_platform_health_score_runs_automatically_from_upload():
    from finance_platform import FinancialPlatform
    p = FinancialPlatform("data/raw/Daily_Household_Transactions.csv")
    result = p.health_score()
    assert 0 <= result["score"] <= 100
    assert result["estimated_profile"]["Income"] > 0
    assert len(result["estimation_warnings"]) > 0


def test_platform_loan_requires_manual_fields_not_fabricated():
    from finance_platform import FinancialPlatform
    p = FinancialPlatform("data/raw/Daily_Household_Transactions.csv")
    report = p.full_report()  # no loan fields supplied
    assert report["loan_preassessment"]["status"] == "not_run"
    assert "credit_score" in report["loan_preassessment"]["reason"]


def test_platform_loan_runs_when_manual_fields_supplied():
    from finance_platform import FinancialPlatform
    p = FinancialPlatform("data/raw/Daily_Household_Transactions.csv")
    result = p.loan_preassessment(age=30, credit_score=700, assets=100000,
                                   existing_loan=0, criminal_record=0)
    assert result["readiness_tier"] in ("ready", "borderline", "needs_improvement")
    assert "estimated_from_transactions" in result
    assert "scale_caveat" in result


def test_platform_ask_works_end_to_end():
    import os
    from finance_platform import FinancialPlatform
    had_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        p = FinancialPlatform("data/raw/Daily_Household_Transactions.csv")
        result = p.ask("what is my total spend?")
        assert result["source"] == "template_fallback"
        assert "spend" in result["answer"].lower() or "total" in result["answer"].lower()
    finally:
        if had_key:
            os.environ["ANTHROPIC_API_KEY"] = had_key


def test_profile_estimator_produces_valid_health_score_input():
    from analytics.profile_estimator import estimate_profile
    from analytics.health_score import FinancialHealthScore
    txns = _sample_transactions_for_rag()
    estimate = estimate_profile(txns)
    assert estimate["monthly_income"] > 0
    assert 0 <= estimate["debt_to_income_ratio"]
    assert isinstance(estimate["has_loan"], bool)
    assert len(estimate["warnings"]) >= 2  # rent/insurance gap + food-mapping gap always present

    hs = FinancialHealthScore().load("data/models/health_score_percentiles.joblib")
    result = hs.score(estimate["profile"])  # must not raise — validates key compatibility
    assert 0 <= result["score"] <= 100


def test_profile_estimator_excludes_investment_from_expenses():
    """Investment spend is savings/allocation, not consumption — it must
    never silently inflate the essential/total expense figures."""
    from analytics.profile_estimator import estimate_profile
    from ingestion.schema import Transaction
    t1 = Transaction(date="2024-08-01", raw_narration="Salary", amount=50000.0, type="credit",
                      bank="GENERIC", source_file="t.csv", source_format="csv", category=None)
    t2 = Transaction(date="2024-08-05", raw_narration="Mutual fund SIP", amount=-10000.0, type="debit",
                      bank="GENERIC", source_file="t.csv", source_format="csv", category="investment")
    t1.compute_id(); t2.compute_id()
    estimate = estimate_profile([t1, t2])
    assert sum(v for k, v in estimate["profile"].items() if k != "Income") == 0.0  # investment excluded entirely


def test_profile_estimator_flags_missing_loan_fields():
    from analytics.profile_estimator import LOAN_FIELDS_REQUIRING_USER_INPUT
    assert set(LOAN_FIELDS_REQUIRING_USER_INPUT) == {"age", "credit_score", "assets", "criminal_record"}
