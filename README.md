# AI-QA-Metrics-Copilot

A leadership-friendly quality engineering metrics dashboard with explainable AI-assisted summaries. Upload release-level test data or use the clearly labeled fictional dataset to explore pass rate, automation coverage, blocked and flaky tests, escaped defects, production incidents, and automation runtime.

## What it demonstrates

- A transparent metric dictionary and validated CSV ingestion
- Per-release trends and weighted aggregate metrics
- Evidence-backed rule signals with configurable example thresholds
- Optional LLM narrative over aggregate metrics only
- JSON and CSV exports for sharing or analysis
- Unit tests and GitHub Actions CI

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
streamlit run app.py
```

The app opens with a fictional release dataset, so the dashboard works immediately without an API key.

## CSV format

Upload one row per release with the following columns:

```csv
release_id,release_date,total_tests,passed_tests,failed_tests,blocked_tests,automated_tests,escaped_defects,pre_release_defects,production_incidents,flaky_tests,automation_duration_minutes
release-001,2026-01-01,100,90,5,5,75,2,8,0,3,25
```

Dates must use `YYYY-MM-DD`. Counts and durations must be non-negative. Passed, failed, and blocked counts cannot exceed `total_tests`; automation and flaky counts cannot exceed the total inventory.

## Optional OpenAI narrative

Install the optional integration and set a key in an environment variable or Streamlit secrets:

```bash
pip install -e ".[llm]"
# macOS / Linux:
export OPENAI_API_KEY="your-key"
# Windows PowerShell:
$env:OPENAI_API_KEY = "your-key"
streamlit run app.py
```

The LLM receives aggregate metrics and existing rule-based signals only. It does not receive the raw uploaded CSV. Use only data allowed by your organization's policy, and review generated wording before sharing it.

## Metric definitions

- **Pass rate:** passed ÷ (passed + failed). Blocked tests are reported separately.
- **Automation coverage:** automated tests ÷ total test inventory.
- **Blocked rate:** blocked tests ÷ total test inventory.
- **Defect escape share:** escaped defects ÷ (escaped + pre-release defects recorded).
- **Flaky-test rate:** flaky tests ÷ total test inventory.

## Run unit tests

```bash
python -m pip install -e ".[dev]"
pytest
```

## Upload to GitHub

1. Extract the project ZIP.
2. Create a repository named `AI-QA-Metrics-Copilot`.
3. Upload the extracted folder contents, including `.github/workflows/ci.yml`.
4. Commit with a message such as `Add AI QA metrics copilot`.

## Important use guidance

Metrics are diagnostic signals, not a complete measure of quality. Interpret changes with customer impact, release scope, product risk, and data definitions. Thresholds in the app are editable examples, not standards. Do not use the dashboard to rank individuals or teams.

## Repository map

```text
app.py                          Streamlit dashboard
src/qa_metrics/metrics.py       CSV validation, calculations, and insights
src/qa_metrics/llm.py            Optional aggregate-only narrative
src/qa_metrics/exports.py        JSON and CSV outputs
examples/release_metrics.csv    Fictional demo data
tests/                          Unit tests
docs/architecture.md            Data flow and production considerations
.github/workflows/ci.yml        GitHub Actions checks
```

## License

MIT. See [LICENSE](LICENSE).

