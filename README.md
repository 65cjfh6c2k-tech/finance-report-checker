# Finance Report Checker

Finance Report Checker is a local MVP for reviewing Excel finance reports. It analyzes `.xlsx` workbooks, detects common spreadsheet QA issues, and produces reports that finance and operations teams can review.

The current version runs locally and uses deterministic rules. It does not send files to any external service.

## Product Positioning

Finance Report Checker is a pre-send QA tool for Excel-based finance reports.

It is designed for FP&A analysts, finance managers, controllers, CFOs, and consultants who prepare or review Excel-based reporting packs.

Finance professionals often spend time manually checking Excel reports and still risk sending files with broken formulas, manual overrides, missing values, or incorrect totals.

Current pitch: Upload your workbook, run finance QA checks, and download an annotated Excel file with highlighted issues, comments, and a QA_Report sheet.

## Current MVP Features

- Command-line analyzer through `analyzer.py`
- FastAPI backend through `app.py`
- Static browser frontend through `frontend/index.html`
- Local startup script through `run_local.sh`
- Excel upload and analysis from the browser
- JSON report output
- HTML report output
- Checked Excel output with highlighted issue cells
- Excel comments/notes on detected issue cells
- `QA_Report` worksheet inside the checked Excel file
- Download links for generated outputs in the frontend

## Project Structure

```text
.
├── analyzer.py                         # Core workbook analysis and report generation
├── app.py                              # FastAPI backend
├── frontend/
│   └── index.html                      # Static frontend
├── run_local.sh                        # Starts backend and frontend locally
├── requirements.txt                    # Python dependencies
├── sample_files/
│   ├── sample_budget_actual.xlsx
│   └── sample_budget_actual_variance_spike.xlsx
├── report.json                         # Generated JSON report
├── report.html                         # Generated HTML report
└── checked_<workbook_name>.xlsx         # Generated annotated Excel output
```

## How To Run Locally

Start both the backend and frontend with:

```bash
./run_local.sh
```

Then open:

```text
http://127.0.0.1:3000
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Press `Ctrl+C` in the terminal to stop both servers.

## Manual Startup

Start the backend:

```bash
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
python -m http.server 3000 --bind 127.0.0.1
```

Then open:

```text
http://127.0.0.1:3000
```

## How To Test

Run the CLI analyzer with the basic sample workbook:

```bash
python analyzer.py sample_files/sample_budget_actual.xlsx
```

Run the CLI analyzer with the variance spike sample workbook:

```bash
python analyzer.py sample_files/sample_budget_actual_variance_spike.xlsx
```

You can also test through the browser by starting the app with `./run_local.sh`, opening `http://127.0.0.1:3000`, and uploading either sample workbook.

## Detected Issue Types

### `hardcoded_value_among_formulas`

Flags a numeric constant in a row that mostly contains formulas. This can indicate that a copied formula was overwritten with a hardcoded value.

### `blank_cell_between_values`

Flags a blank cell between non-empty cells in the same row. This can indicate a missing value or missing formula in a financial schedule.

### `formula_inconsistency_in_row`

Flags a formula that does not match the neighboring formula pattern in the same row. This can indicate a formula copy or reference error.

### `variance_spike_between_periods`

Flags a numeric period-over-period change greater than 50% between adjacent reporting periods. This can indicate an unusual movement that should be reviewed or explained.

## Generated Outputs

### `report.json`

A machine-readable JSON report containing workbook metadata, sheet statistics, detected issues, issue counts, risk score, risk level, and executive summary.

### `report.html`

A readable HTML report for quick review in a browser. It includes the workbook summary, risk score, issue counts, sheet statistics, and issue details.

### `checked_<workbook_name>.xlsx`

An annotated copy of the source workbook. It includes:

- Highlighted issue cells
- Excel comments/notes on issue cells
- A `QA_Report` worksheet with workbook summary, sheet statistics, and issue details

## Current Limitations

- Only `.xlsx` files are supported
- Rules are deterministic only
- No authentication yet
- No file isolation per user yet
- Not production-ready

## Next Roadmap

- Better finance-specific checks
- Multi-file and session-specific outputs
- Improved UI
- Deployment
- AI-generated explanations later
