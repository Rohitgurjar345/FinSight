# FinSight — AI-Powered Personal Financial Intelligence Platform (Backend)

Upload one or more bank statements (CSV / Excel / text-layer PDF) and the platform automatically:

1. **Ingests** them (HDFC / ICICI / SBI / generic layouts) into one canonical schema
2. **Categorizes** every transaction (rule engine + TF-IDF/Logistic Regression fallback)
3. **Estimates** a monthly financial profile from the categorized data
4. **Scores** financial health (weighted, percentile-calibrated, explainable)
5. **Pre-assesses** loan readiness (XGBoost + SHAP, 3 tiers, mandatory disclaimer)
6. **Answers questions** about your statement (RAG assistant with a no-API-key fallback)

> Everything below uses `python` (not `python3`) because the commands were verified on Windows / Git Bash.
> On macOS/Linux, use `python3` wherever you see `python`.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11 – 3.13 | Check with `python --version` |
| pip | Comes with Python |
| Git (optional) | Only needed to clone the repo |

---

## 2. Get the code

```bash
git clone https://github.com/Rohitgurjar345/FinSight.git
cd FinSight
```

Or unzip the downloaded ZIP and `cd` into the extracted folder. **All commands below must be run from this project root folder** (the one containing `finance_platform.py`) — otherwise you will get `ModuleNotFoundError`.

---

## 3. Required data files

Place these in `data/raw/` (they are used for training and testing):

| File | Used by |
|---|---|
| `bank.xlsx` | Module 1 test (real HDFC-layout statement) |
| `Daily_Household_Transactions.csv` | Module 1 / 2 / 5 testing |
| `budgetwise_finance_dataset.csv` | Module 1 stress-testing (messy data) |
| `financial_transaction_test.csv` | Module 2 training |
| `test_transactions.csv` | Module 2 training |
| `data.csv` | Module 3 health-score population reference |
| `monthly_spending_dataset_2020_2025-selected-columns__1_.csv` | Module 3 forecasting |
| `Loan_Prediction.csv` | Module 4 training |

Check they are all present:

```bash
ls data/raw
```

---

## 4. Environment setup

### 4.1 Create a virtual environment (do NOT use `--system-site-packages`)

```bash
python -m venv venv
```

### 4.2 Activate it

| Shell | Command |
|---|---|
| Git Bash (Windows) | `source venv/Scripts/activate` |
| Command Prompt (Windows) | `venv\Scripts\activate.bat` |
| PowerShell (Windows) | `venv\Scripts\Activate.ps1` |
| macOS / Linux | `source venv/bin/activate` |

Your prompt should now start with `(venv)`.

### 4.3 Upgrade pip tooling (prevents most install errors)

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 4.4 Install dependencies

```bash
pip install -r requirements.txt
pip install pytest
```

Expected contents of `requirements.txt`:

```
pandas>=2.2.3
openpyxl>=3.1
scikit-learn>=1.4
joblib>=1.3
pdfplumber>=0.11
xgboost>=2.0      # optional — falls back to sklearn GradientBoosting if missing
shap>=0.44        # optional — falls back to global feature importance if missing
anthropic>=0.40   # optional — only needed for live (LLM) RAG answers
```

---

## 5. Train the models (run once, in this order)

Each command trains a model, prints its evaluation metrics, and saves it to `data/models/`.

```bash
python -m categorization.train          # Module 2: TF-IDF + Logistic Regression
python -m analytics.train_health_score  # Module 3: builds population percentile reference
python -m analytics.train_forecasting   # Module 3: forecaster vs. moving-average baseline
python -m loan_assessment.train         # Module 4: loan model (+ SHAP if installed)
```

Modules 1 (ingestion) and 5 (RAG assistant) need no training.

After this, `data/models/` should contain:

```
tfidf_vectorizer.joblib
logreg_model.joblib
health_score_percentiles.joblib
forecast_model.joblib
loan_assessment_model.joblib
```

---

## 6. Verify everything works

```bash
python -m pytest test_pipeline.py -v
```

Expected: **34 passed**. Fix any failure before continuing.

---

## 7. Run the platform

### 7.1 One command — full pipeline (interactive)

```bash
python -m run_pipeline data/raw/bank.xlsx
```

Multiple statements at once (any mix of `.csv`, `.xlsx`, `.xls`, `.pdf`):

```bash
python -m run_pipeline data/raw/bank.xlsx data/raw/Daily_Household_Transactions.csv
```

What happens, in order: ingestion → categorization → profile estimation → health score → loan pre-assessment (you'll be asked **age, credit score, assets, criminal record** — a bank statement cannot contain these, so they are never guessed) → interactive question prompt for the RAG assistant. Press Enter on an empty line to exit.

### 7.2 Python shell — step-by-step control

Start the shell **from the project root**:

```bash
python
```

Then enter the lines **one at a time** (pressing Enter after each). Pasting several statements on one line causes `SyntaxError`.

```python
from finance_platform import FinancialPlatform
p = FinancialPlatform("data/raw/bank.xlsx")        # or a list of files
print(len(p.transactions))
print(p.transactions[0].bank, p.transactions[0].date, p.transactions[0].amount, p.transactions[0].category)
```

**Health score (fully automatic):**

```python
hs = p.health_score()
print(hs["score"])
print(hs["estimated_profile"])
print("\n".join(hs["estimation_warnings"]))
```

**Loan pre-assessment (needs your inputs):**

```python
print(p.full_report()["loan_preassessment"])        # shows status: not_run + what's missing
r = p.loan_preassessment(age=32, credit_score=720, assets=200000, existing_loan=0, criminal_record=0)
print(r["readiness_tier"], r["approval_probability"])
print(r["disclaimer"])
```

Sanity check — a weaker applicant should score worse:

```python
r2 = p.loan_preassessment(age=32, credit_score=450, assets=200000, existing_loan=0, criminal_record=1)
print(r2["readiness_tier"], r2["approval_probability"])
```

**Ask questions (RAG assistant):**

```python
print(p.ask("what is my total spend?")["answer"])
print(p.ask("how much did I spend on food last month?")["answer"])
print(p.ask("what is my top spending category?")["answer"])
print(p.ask("how many transactions do I have?")["answer"])
```

**Multiple files through the platform:**

```python
p2 = FinancialPlatform(["data/raw/bank.xlsx", "data/raw/Daily_Household_Transactions.csv"])
print(p2.ingestion_report)
```

**Full report in one call:**

```python
report = p.full_report(loan_manual_fields={
    "age": 32, "credit_score": 720, "assets": 200000,
    "existing_loan": 0, "criminal_record": 0,
})
```

Exit the shell with `exit()`.

### 7.3 Run individual modules

```bash
python -m ingestion.pipeline data/raw/bank.xlsx
python -m ingestion.pipeline data/raw/file1.csv data/raw/file2.xlsx    # batch + cross-file dedup
```

---

## 8. Optional: live LLM answers (Anthropic API)

By default the assistant answers with the **no-key fallback** (exact aggregation over your data, no LLM, no hallucination). To enable live answers, set the key **in your shell** — it is read only from the environment, never hard-coded:

| Shell | Set | Remove |
|---|---|---|
| Git Bash / macOS / Linux | `export ANTHROPIC_API_KEY="your-key"` | `unset ANTHROPIC_API_KEY` |
| PowerShell | `$env:ANTHROPIC_API_KEY="your-key"` | `Remove-Item Env:ANTHROPIC_API_KEY` |
| Command Prompt | `set ANTHROPIC_API_KEY=your-key` | `set ANTHROPIC_API_KEY=` |

Check whether one is currently set: `echo $ANTHROPIC_API_KEY` (Git Bash).

The `source` field in each answer tells you what happened:

| `source` value | Meaning |
|---|---|
| `template_fallback` | No key set — answered locally |
| `anthropic_api` | Live LLM answer |
| `template_fallback_after_api_error` | Key was set but the call failed (invalid/expired key, no network) — answered locally |

> **Security:** never paste API keys into chats, commits, or screenshots. If a key has ever been shared anywhere, rotate it.

---

## 9. Optional: SHAP explanations and XGBoost

```bash
pip install shap xgboost
python -m loan_assessment.train     # re-run so the saved model uses them
```

Without them the code still works: XGBoost falls back to scikit-learn gradient boosting, and SHAP falls back to global feature importances (clearly labeled as *not* per-applicant).

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Python was not found; run without arguments to install from the Microsoft Store` | Using `python3` on Windows | Use `python` |
| `can't open file '...ingestion.pipeline'` | Missing `-m` | `python -m ingestion.pipeline ...` |
| `ModuleNotFoundError: No module named 'ingestion'` | Not in the project root | `cd` into the folder containing `finance_platform.py` |
| `SyntaxError` when pasting into Python | Several statements pasted on one line | Enter one statement per line |
| `...` prompt never returns | Unclosed `(` or `[` | Type the closing character, or press Ctrl+C |
| `test_platform_ask_works_end_to_end` fails with `template_fallback_after_api_error` | `ANTHROPIC_API_KEY` set in your shell (older test version) | `unset ANTHROPIC_API_KEY`, or use the latest `test_pipeline.py` (it clears the key itself) |
| pandas "building from source" / wheel errors on Python 3.13 | Pinned old pandas or old pip | `python -m pip install --upgrade pip`, keep `pandas>=2.2.3` |
| `pip` errors in a fresh venv | Outdated pip/setuptools | Step 4.3, then reinstall |
| `FileNotFoundError: data/models/...joblib` | Models not trained yet | Run Section 5 |
| Naming a file `platform.py` breaks pandas | Shadows Python's built-in `platform` module | Never name a project file `platform.py` (this repo uses `finance_platform.py`) |

---

## 11. Project structure

```
ingestion/
  schema.py                   canonical Transaction dataclass
  extractors/                 csv / excel / pdf  ->  DataFrame
  detectors/bank_detector.py  header fingerprint  ->  parser
  parsers/                    hdfc / icici / sbi / generic
  cleaning/                   narration_cleaner, deduplicator (single + cross-file)
  pipeline.py                 run() single file, run_batch() multi-file
categorization/
  rules.py                    keyword rules (editable)
  embedder.py                 pluggable embedder interface (TF-IDF default)
  classifier.py               Logistic Regression wrapper
  train.py                    trains + saves the classifier
  categorizer.py              rules first, ML fallback, confidence-gated
analytics/
  health_score.py             weighted percentile-based scorer
  train_health_score.py       builds population reference
  forecasting.py              feature engineering + XGBoost/sklearn forecaster
  train_forecasting.py        trains + compares against moving-average baseline
  profile_estimator.py        categorized transactions -> Module 3/4 profile
loan_assessment/
  model.py                    classifier + SHAP + 3-tier output + disclaimer
  train.py                    trains + evaluates
rag_assistant/
  retriever.py                TF-IDF retrieval over the user's own transactions
  no_key_fallback.py          exact-aggregation answers (no LLM)
  assistant.py                retrieval + API-or-fallback generation
finance_platform.py           single entry point (FinancialPlatform)
run_pipeline.py               one-command interactive run
test_pipeline.py              34 automated tests
backend_api/                  (not covered in this README — see that folder)
frontend/                     (not covered in this README — see that folder)
data/raw/                     datasets
data/models/                  trained models
```

---

## 12. How each result is computed

**Financial Health Score (0–100)** — weighted average of four factors, each converted to a percentile against the 20,000-profile reference population (`data.csv`):

| Factor | Weight | Healthier when |
|---|---|---|
| Savings rate | 40% | higher |
| Debt-to-income | 25% | lower |
| Essential expense ratio (rent + groceries + utilities + healthcare ÷ income) | 20% | lower |
| Category diversification | 15% | higher |

**Forecasting** — gradient-boosted regressor on lag + calendar features, evaluated on a time-ordered 12-month holdout against a naive 3-month moving-average baseline. Both MAE values print on every training run.

**Loan readiness** — `ready` (≥ 60%), `borderline` (30–60%), `needs_improvement` (< 30%) predicted approval probability, with a disclaimer attached to every result.

**Profile estimation** — monthly averages over the months your statement covers; income = total credits ÷ months. Every estimate ships with an `estimation_warnings` list.

---

## 13. Known limitations (read before trusting numbers)

- **Synthetic training data.** Module 2 reports ~100% accuracy and Module 4 reports ROC-AUC 1.0 because the datasets are templated / rule-generated. Real-world performance will be lower; Module 2 therefore flags uncertain predictions as `low_confidence` instead of guessing.
- **Module 2 skews toward `food`** on short, generic real-world narrations, which can distort the diversification score and category-based answers.
- **Forecasting:** the moving-average baseline currently beats the ML model (limited history: 54 training months). The comparison is shown, not hidden.
- **Loan model:** `age`, `credit_score`, `assets`, `criminal_record` can never be derived from a bank statement — they are required inputs. Income scale in `Loan_Prediction.csv` may differ from monthly income estimated from statements; treat outputs as rough pre-assessment only. Not a lending decision.
- **ICICI / SBI parsers** are built from publicly documented layouts and unit-tested on synthetic fixtures — not verified against real exports. HDFC is verified on real data.
- **PDF:** text-layer PDFs only. Scanned/image statements need OCR (not implemented).
- **RAG fallback** matches known question patterns and exact-phrase synonyms (e.g. "groceries" → food); unknown phrasings return guidance rather than a guess.
- **Rent / Insurance** are detected by keyword only; differently worded debits fall into Miscellaneous.

---

## 14. Quick start (copy-paste summary)

```bash
python -m venv venv
source venv/Scripts/activate              # Git Bash on Windows
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install pytest

python -m categorization.train
python -m analytics.train_health_score
python -m analytics.train_forecasting
python -m loan_assessment.train

python -m pytest test_pipeline.py -v      # expect 34 passed
python -m run_pipeline data/raw/bank.xlsx
```
