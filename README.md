# Finance Report Checker

Finance Report Checker is a pre-send QA tool for Excel-based finance reports. It helps finance teams detect spreadsheet issues before reports reach management, clients, investors, or board audiences.

The project currently has a public landing page for validation and a separate local/private app for real workbook analysis.

## Product Positioning

Finance Report Checker is designed for FP&A analysts, finance managers, controllers, CFOs, and finance consultants who prepare or review Excel reporting packs.

Core pain: finance professionals often spend time manually checking Excel reports and still risk sending files with broken formulas, manual overrides, missing values, unusual variances, or incorrect totals.

## Architecture

### Public Landing

`frontend/index.html` is the public Vercel landing page. It is a compact product page with sample output downloads, a Tally private beta request CTA, and Vercel Analytics.

Public upload is intentionally disabled for security reasons.

### Local/Private App

`frontend/app.html` is the local/private analysis app. It runs at:

```text
http://127.0.0.1:3000/app.html
```

It uploads `.xlsx` files to the local FastAPI backend, displays QA results, renders charts, and can optionally request local AI executive insights.

### FastAPI Backend

`app.py` runs at:

```text
http://127.0.0.1:8000
```

It accepts workbook uploads, runs the analyzer, generates downloadable outputs, and returns the JSON report to the local app.

### Analyzer Package

The `finance_checker/` package contains the core logic:

- workbook orchestration
- issue detection rules
- risk scoring
- report generation
- checked Excel output
- deterministic chart specs
- optional AI executive insights

## How To Run Local/Private App

Install dependencies in your virtual environment:

```bash
pip install -r requirements.txt
```

Start the backend and frontend:

```bash
./run_local.sh
```

Open the local/private app:

```text
http://127.0.0.1:3000/app.html
```

The public landing page remains available at:

```text
http://127.0.0.1:3000
```

## Manual Startup

Start the backend:

```bash
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend
python -m http.server 3000 --bind 127.0.0.1
```

## Public Landing Page

The public landing page is:

```text
frontend/index.html
```

It is intended for public validation and beta collection:

- deployed on Vercel
- compact one-page product landing page
- sample checked Excel, HTML, and JSON report downloads
- Tally private beta request form
- Vercel Analytics
- no public upload

## Local AI Insights With Ollama

AI Executive Insights are optional and intended for the local/private app.

The default local AI provider is Ollama. Recommended model:

```bash
ollama pull qwen2.5:7b
```

Create a `.env` file in the project root:

```env
AI_INSIGHTS_ENABLED=true
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

Then run the local app and check `Generate AI insights with local AI` before analyzing a workbook.

AI insights use a sanitized report summary only. The full Excel workbook is not sent to the model.

Do not commit `.env`.

## How To Test

Run the CLI analyzer:

```bash
python analyzer.py sample_files/sample_budget_actual.xlsx
python analyzer.py sample_files/sample_budget_actual_variance_spike.xlsx
python analyzer.py sample_files/sample_finance_report_large.xlsx
```

Run the local app:

```bash
./run_local.sh
```

Then open:

```text
http://127.0.0.1:3000/app.html
```

Upload `sample_files/sample_finance_report_large.xlsx` to test issues, charts, downloads, and optional AI insights.

## Detected Issue Types

- `formula_inconsistency_in_row`: formula pattern differs from neighboring formulas.
- `hardcoded_value_among_formulas`: numeric constant appears in a row mostly made of formulas.
- `blank_cell_between_values`: blank cell appears between non-empty cells in a financial row.
- `variance_spike_between_periods`: adjacent monthly values change by more than the configured threshold.
- `total_formula_mismatch`: total/subtotal formula may omit expected detail rows.

## Generated Outputs

The local/private app and CLI can generate:

- browser summary
- risk score
- issue counts
- issue table
- deterministic finance charts
- AI Executive Insights, if enabled
- `report.html`
- `report.json`
- `checked_<workbook_name>.xlsx`

The checked Excel workbook includes highlighted issue cells, Excel comments, and a `QA_Report` worksheet.

## Security Notes

- Public upload is intentionally disabled.
- Sensitive workbooks should be tested locally or in a private beta environment.
- Local AI with Ollama avoids sending data to external AI APIs.
- AI insights use sanitized issue, risk, and chart summaries rather than the full workbook.
- Hosted upload requires further security hardening, including authentication, file isolation, retention controls, and secure storage policies.

## Current Limitations

- Only `.xlsx` files are supported.
- Core QA checks are deterministic rules.
- Local AI output depends on the configured local model.
- No authentication or multi-user file isolation yet.
- Not production-ready.

## Roadmap

- Hosted beta backend with security hardening.
- Better AI prompts and management-ready explanations.
- More finance-specific checks.
- Multi-file/session output handling.
- Excel add-in or local desktop packaging later.
