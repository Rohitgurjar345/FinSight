# Modules 1 & 2 — Ingestion + Categorization (backend only, no frontend)

## Setup
```
pip install -r requirements.txt
```

## Single Platform — everything automatic after one upload (except one thing)

`finance_platform.py` is the actual answer to "upload once, everything runs":

```python
from finance_platform import FinancialPlatform

p = FinancialPlatform("data/raw/bank.xlsx")              # single file
# or: FinancialPlatform(["jan.csv", "feb.xlsx"])          # multiple files at once

p.health_score()                    # fully automatic — no manual input needed
p.ask("what's my total spend?")     # fully automatic
p.full_report()                     # both of the above in one call
```

The moment you construct `FinancialPlatform`, ingestion (Module 1) and
categorization (Module 2) already ran. `health_score()` then automatically
estimates a financial profile from those categorized transactions
(`analytics/profile_estimator.py`) and scores it — no manual data entry.

**Loan Pre-Assessment is the one deliberate exception:**
```python
p.loan_preassessment(age=32, credit_score=720, assets=200000,
                      existing_loan=0, criminal_record=0)
```
`age`, `credit_score`, `assets`, and `criminal_record` are **required
arguments with no defaults** — this is not a limitation I'm planning to
lift later, it's a hard fact about what a bank statement can and can't
tell you. No amount of transaction analysis reveals someone's credit
score or legal history, so this platform will not guess or fabricate
them. Income and debt-to-income *are* auto-estimated from your
transactions and used alongside whatever you provide. Calling
`full_report()` without these fields returns a clear `"not_run"` status
explaining exactly what's missing and why, rather than silently skipping
the module.

### The profile estimate is an approximation — see `estimation_warnings`
Every `health_score()`/`loan_preassessment()` result includes a
`warnings` list (or `estimation_warnings` in the health score result)
spelling out the real assumptions being made: monthly averaging over
however many months your statement covers, "food" being mapped to
Groceries with no dining-out split, Rent/Insurance depending on keyword
matches that may miss real rent/insurance debits worded differently, and
a flag if one category dominates so heavily it's more likely a
categorization gap than genuine spending concentration. None of this is
hidden inside the score — read the warnings before trusting the number.

## Module 1 — Ingestion & Parsing
Detects format (CSV/XLSX/PDF) and bank (HDFC/ICICI/SBI/generic fallback),
parses into a canonical `Transaction` schema, cleans narration text, dedupes.

Single file:
```
python3 -m ingestion.pipeline data/raw/bank.xlsx
```

**Multiple files at once** (upload several statements in one batch):
```
python3 -m ingestion.pipeline data/raw/file1.csv data/raw/file2.xlsx data/raw/file3.csv
```
Or in code:
```python
from ingestion.pipeline import run_batch
result = run_batch(["file1.csv", "file2.xlsx", "file3.csv"])
result["transactions"]          # merged, cross-file-deduped list
result["per_file_counts"]       # {filename: count}
result["duplicates_removed_cross_file"]
result["errors"]                # one bad file never aborts the whole batch
```
Each file is parsed independently (so one corrupt/unsupported file doesn't
fail the others), then results are merged with **cross-file dedup** — this
catches the same transaction appearing in two different uploaded files (e.g.
overlapping statement periods across two exports), which the per-file dedup
can't catch since its ID includes the source filename.

**Bug caught and fixed during testing:** the first cross-file dedup version
was matching on (date, narration, amount) too eagerly and silently dropped
~760 genuine transactions from a single messy dataset — rows with a missing
amount (parsed as 0.0) and a blank/"nan" narration were colliding with each
other and getting wrongly treated as duplicates. Both dedup functions now
require a real date, real narration, and a non-zero amount before treating
two rows as duplicates at all; anything missing that signal is always kept.
Verified via `test_dedup_does_not_falsely_collapse_zero_amount_rows`.

- Confirmed working against real data: `bank.xlsx` (99,629 txns, auto-detected as HDFC).
- HDFC/ICICI/SBI parsers are built from each bank's **publicly documented**
  statement-export column layout (no real sample files exist for ICICI/SBI —
  flagged, untested against a live ICICI/SBI export; unit tests use synthetic
  fixtures matching the documented format).
- PDF support requires text-layer PDFs. Scanned/image statements need OCR,
  not yet implemented — no sample scanned PDF was available to build against.

## Module 2 — Categorization
Rule engine (keyword match, instant, confidence=1.0) runs first. Anything it
misses falls to a TF-IDF + Logistic Regression classifier (trained on 2,000
labeled narrations, 9 categories). Predictions below 0.55 confidence are
flagged `low_confidence` for user review instead of guessing silently.

Train (already run once, model saved to `data/models/`):
```
python3 -m categorization.train
```

Use:
```python
from categorization.categorizer import Categorizer
c = Categorizer()
c.categorize("Zomato food order")
# {'category': 'food', 'confidence': 1.0, 'source': 'rule'}
```

**Honest caveat:** test accuracy on the training datasets is 100% — expected,
since those are templated/synthetic (merchant name = category, always). Real
messy narrations (tested against `Daily_Household_Transactions.csv`) score
much lower and correctly get flagged `low_confidence` rather than mis-guessed
— see test run output. More real labeled data will improve this over time;
the rule layer + confidence threshold are there specifically to keep wrong
guesses from slipping through silently.

Embedder is pluggable (`categorization/embedder.py`) — swapping TF-IDF for
SBERT later is a new class, not a rewrite.

## Module 3 — Analytics

### Financial Health Score (`analytics/health_score.py`)
Weighted, explainable score (0-100) calibrated against the real 20,000-profile
population in `data.csv`. Four independent factors, each scored as a
population percentile so there's a transparent reference point, not an
arbitrary number:

| Factor | Weight | Direction |
|---|---|---|
| Savings rate | 40% | higher = healthier |
| Debt-to-income | 25% | lower = healthier |
| Essential expense ratio (rent+groceries+utilities+healthcare / income) | 20% | lower = healthier |
| Category diversification (Herfindahl-based) | 15% | higher = healthier |

**Bug caught and fixed during testing:** an earlier version used
"expense-to-income ratio" as a 4th factor, but that's mathematically
`1 - savings_rate` — scoring both double-counted the same signal at 60%
combined weight. Replaced with essential-expense-ratio, a genuinely
independent measure of fixed-cost burden. Verified via
`test_health_score_no_double_counting`.

Train (builds the population percentile reference):
```
python3 -m analytics.train_health_score
```
Use:
```python
from analytics.health_score import FinancialHealthScore
hs = FinancialHealthScore().load("data/models/health_score_percentiles.joblib")
hs.score({"Income": 50000, "Rent": 10000, "Groceries": 5000, ...})
```

### Expense Forecasting (`analytics/forecasting.py`)
XGBoost regressor (falls back to sklearn's GradientBoostingRegressor if
xgboost isn't installed — same gradient-boosted-tree family, zero code
changes needed) on lag + calendar features, trained on the 2020-2025 monthly
series, evaluated against a naive 3-month moving-average baseline on the most
recent 12 months (time-ordered holdout, no shuffling).

Train + evaluate:
```
python3 -m analytics.train_forecasting
```

**Honest result:** the moving-average baseline currently wins (MAE ~2,113 vs
~3,611 for the ML model). With only 54 training months, this is a real,
expected outcome — not a bug. Smooth, moderately-noisy short series often
favor simple baselines over tree-based ML; this is well documented in
forecasting literature. The comparison is deliberately printed every run so
this isn't hidden. More historical months would likely close the gap.

## Module 4 — Loan Pre-Assessment

XGBoost classifier (falls back to sklearn's GradientBoostingClassifier if
xgboost isn't installed) with **SHAP** explainability (`shap.TreeExplainer`),
trained on `Loan_Prediction.csv` (12,367 applicants, ~11% approval rate,
handled via `scale_pos_weight`). Outputs a three-tier readiness label —
`ready` (≥60% predicted approval probability) / `borderline` (30-60%) /
`needs_improvement` (<30%) — plus a per-applicant SHAP breakdown of which
features pushed the prediction up or down, and a mandatory disclaimer
attached to every single result.

**Honest result:** ROC-AUC came back at a perfect 1.0000. I checked why
instead of taking it at face value — this dataset was generated by
deterministic threshold rules (100% of approved applicants have
`criminal_record == 0` AND `credit_score >= 701` AND `debt_to_income_ratio
<= 0.29`), so perfect separation is expected on this synthetic data, not a
sign the model is production-ready. Real applicant data will be noisier and
will not separate this cleanly — flagging this now so it isn't mistaken for
real-world performance later.

**SHAP caveat:** the sandbox this was built in has no network access to
install `shap`, so the SHAP code path (`shap.TreeExplainer`) is written to
the standard, stable SHAP API but wasn't executable in this environment. A
fallback to the model's global `feature_importances_` was built in and
tested, and it kicks in automatically and prints a clear label
(`"shap not installed"`) if `shap` isn't present — so the code never
silently breaks either way. **Run `pip install shap` on your machine, then
re-run `python3 -m loan_assessment.train` once, to confirm the real
per-applicant SHAP values before relying on this for anything real.**

Train + evaluate:
```
python3 -m loan_assessment.train
```
Use:
```python
from loan_assessment.model import LoanAssessor
assessor = LoanAssessor().load("data/models/loan_assessment_model.joblib")
assessor.assess({"age": 35, "income": 90000, "assets": 300000,
                  "credit_score": 780, "debt_to_income_ratio": 0.2,
                  "existing_loan": 0, "criminal_record": 0})
```

## Module 5 — RAG Conversational Assistant (backend only, no Streamlit)

Per your decision: this is the RAG engine only — retrieval + generation +
no-key fallback, tested via scripts. No Streamlit dashboard file was built.

### Retrieval (`rag_assistant/retriever.py`)
TF-IDF over the user's own transactions (narration + category + date +
amount), per your decision to stay consistent with Module 2 rather than add
an SBERT dependency. The corpus is always a single user's own transaction
history, built fresh per session — not a persistent trained model.

### Generation (`rag_assistant/assistant.py`)
- If `ANTHROPIC_API_KEY` is set in the environment → calls the real
  Anthropic API with the retrieved transactions as grounding context.
- If not set → falls back to `rag_assistant/no_key_fallback.py`, a
  template/pattern layer that answers directly from the data via exact
  aggregation (no LLM, no hallucination risk).
- If the API call fails for any reason (bad/expired/rate-limited key,
  network error) → catches the exception and falls back to the template
  layer rather than crashing, and says so in the response.

**Security note:** the API key is read only from the `ANTHROPIC_API_KEY`
environment variable — never hardcoded, logged, or accepted as a plain
argument. **A key was pasted into this chat during development — treat it
as compromised and rotate it before using this module for anything real.**
The API call path is written to the correct, standard `anthropic` SDK shape
but was **not executable in this sandbox** (no network/key access here) —
only the no-key fallback path below has actually been run and verified.

### What's actually tested (no-key fallback, 8 tests)
- "how much did I spend on `<category>` this/last month?"
- "what's my top spending category?" / "what's my total spend?"
- "how many transactions do I have?"
- Unmatched queries return guidance instead of a wrong guess.

**Bug caught and fixed during testing:** the category-matching regex
extracted the literal phrase from the question (e.g. "groceries"), but
Module 2's categorizer only ever produces `food`/`travel`/`utilities`/etc.
— so "how much did I spend on groceries" was silently returning "no
transactions found" even when matching data existed. Added a synonym map
(`groceries`→`food`, `medical`→`healthcare`, etc.) so common phrasings
resolve to the actual category label. This is exact-phrase matching, not
fuzzy — a synonym has to match the whole extracted phrase (e.g. "medical
bills" won't match the "medical" entry) — a real remaining limitation,
documented rather than silently left in.

**Honest caveat carried over from Module 2:** the RAG answers are only as
good as the categories Module 2 assigned. Tested on real data
(`Daily_Household_Transactions.csv`), Module 2's rule engine defaults a
large majority of short/generic real-world narrations to `food` (2,184 of
2,458 transactions) — so category-specific RAG answers on messy real data
will inherit that skew until Module 2's categorization is improved with
more real labeled data.

Use:
```python
from ingestion.pipeline import run
from categorization.categorizer import Categorizer
from rag_assistant.assistant import FinancialAssistant

txns = run("data/raw/Daily_Household_Transactions.csv")
Categorizer().categorize_transactions(txns)
assistant = FinancialAssistant(txns)
assistant.ask("how much did I spend on food last month?")
```

## Running the whole platform in one command (all 5 modules, automatic)

**This is the single unified flow: upload a bank statement, everything else
runs automatically, with one exception explained below.**

```
python -m run_pipeline data/raw/bank.xlsx
python -m run_pipeline data/raw/statement_jan.csv data/raw/statement_feb.xlsx   # multiple files
```

What happens automatically, in order:
1. **Ingestion** (Module 1) — detects bank/format, parses, cleans, dedupes.
2. **Categorization** (Module 2) — rule engine + ML classifier tags every transaction.
3. **Profile estimation** (`analytics/profile_estimator.py`, new) — derives a
   monthly income/expense profile FROM your categorized transactions, bridging
   Module 2's output to the structured input Modules 3 & 4 need.
4. **Health Score** (Module 3) — runs automatically on the derived profile,
   prints the full weighted breakdown.
5. **Loan Pre-Assessment** (Module 4) — income, debt-to-income ratio, and
   existing-loan flag are auto-filled from your statement. **You will be
   asked 4 questions: age, credit score, assets, criminal record.** This is
   not a design choice to add friction — a bank statement genuinely contains
   no signal for any of these four fields, so guessing them would mean
   silently fabricating inputs to a model whose output gets called
   "loan readiness." Asking is the honest option.
6. **RAG Assistant** (Module 5) — drops into an interactive prompt to ask
   questions about your statement, grounded in the same ingested data.

### Honest limitations of the auto-derivation (read before trusting the numbers)
- **Module 2 has no "rent" or "insurance" category at all.** Both always
  come out as 0 in the derived profile — a real gap in your essential
  expenses that isn't visible unless you know to look for it.
- **"food" is mapped entirely to Groceries** (Module 2 doesn't separate
  dining from groceries) — this both overstates Groceries and, combined
  with Module 2's known tendency to over-predict "food" on messy real-world
  narrations (documented in Module 2's section above), can compress your
  Health Score's category-diversification factor toward its worst
  percentile. This isn't a bug — it's the food-categorization skew
  propagating downstream, and it's worth fixing Module 2's accuracy before
  trusting the diversification score.
- **Loan_Prediction.csv's income units (monthly vs. annual) are undocumented
  and unknown.** Your derived MONTHLY income is passed in as-is. This is a
  genuine, unresolved ambiguity, disclosed rather than silently guessed —
  treat any loan-readiness output with extra caution beyond the standard
  disclaimer already attached to every result.
- All profile figures are **monthly averages** over however much statement
  history you uploaded — one month of data gives a much noisier estimate
  than a year's worth.

If you'd rather supply Module 3/4 profile data yourself instead of trusting
the auto-derivation, call `HealthScorer`/`LoanAssessor` directly as shown in
their sections above — the automatic chain is a convenience layer on top of
the same tested functions, not a replacement for them.

## Tests
```
python3 -m pytest test_pipeline.py -v
```
34/34 passing — bank detection (all 3 banks + fallback), real-file parsing,
sign-convention correctness, single + cross-file dedup (incl. the
false-positive regression test), multi-file batch upload (incl. partial
failure handling), rule + ML categorization, health score breakdown +
non-redundancy, forecast model sanity, loan tier/disclaimer/explanation
correctness, RAG retrieval + no-key fallback (category spend, synonym
mapping, total spend, unmatched-query guidance, end-to-end assistant),
profile estimator (health-score compatibility, investment-exclusion
regression test, missing-loan-field flagging), and the unified
FinancialPlatform (automatic health score from upload, loan
pre-assessment correctly requiring manual fields, end-to-end Q&A).

## Structure
```
ingestion/
  schema.py                  # canonical Transaction dataclass
  extractors/                # csv / excel / pdf -> DataFrame
  detectors/bank_detector.py # fingerprint match -> parser
  parsers/                   # hdfc / icici / sbi / generic
  cleaning/                  # narration_cleaner, deduplicator (single + cross-file)
  pipeline.py                # run() single file, run_batch() multi-file upload
categorization/
  rules.py                   # keyword rules (editable dict)
  embedder.py                # pluggable interface, TF-IDF default
  classifier.py               # LogisticRegression wrapper
  train.py                    # merges labeled datasets, trains, saves
  categorizer.py               # rules-first, ML-fallback orchestrator
analytics/
  health_score.py             # weighted percentile-based scorer
  train_health_score.py       # builds population reference, saves it
  forecasting.py               # feature engineering + XGBoost/sklearn forecaster
  train_forecasting.py         # trains, evaluates vs baseline, saves
  profile_estimator.py         # bridges categorized transactions -> Module 3/4 profile input
loan_assessment/
  model.py                     # XGBoost/sklearn classifier + SHAP explainability + tiering
  train.py                     # trains, evaluates, saves, runs sample assessment
rag_assistant/
  retriever.py                 # TF-IDF retrieval over one user's own transactions
  no_key_fallback.py           # template Q&A, no LLM — the tested path
  assistant.py                 # orchestrator: retrieval + API-or-fallback generation
finance_platform.py           # THE single entry point: upload -> auto categorize+score+ask
run_pipeline.py                # lighter chain: ingest+categorize+interactive RAG prompt
data/raw/                    # your uploaded datasets
data/models/                 # trained tfidf_vectorizer.joblib, logreg_model.joblib,
                              # health_score_percentiles.joblib, forecast_model.joblib,
                              # loan_assessment_model.joblib
```
