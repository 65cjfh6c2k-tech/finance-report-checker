import json
from html import escape
from pathlib import Path

from finance_checker.excel_output import save_annotated_workbook


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = PROJECT_ROOT / "report.json"
HTML_REPORT_PATH = PROJECT_ROOT / "report.html"


def html_value(value):
    if value is None:
        return ""
    return escape(str(value))


def render_severity_badge(severity):
    safe_severity = html_value(severity)
    return f'<span class="badge {safe_severity}">{safe_severity}</span>'


def render_issue_counts(issue_counts):
    rows = []
    for severity in ["high", "medium", "low"]:
        rows.append(
            "<tr>"
            f"<td>{render_severity_badge(severity)}</td>"
            f"<td>{issue_counts[severity]}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_sheet_rows(sheets):
    if not sheets:
        return '<tr><td colspan="6">No visible sheets found.</td></tr>'

    rows = []
    for sheet in sheets:
        rows.append(
            "<tr>"
            f"<td>{html_value(sheet['name'])}</td>"
            f"<td>{html_value(sheet['used_range'])}</td>"
            f"<td>{sheet['non_empty_cells']}</td>"
            f"<td>{sheet['formula_cells']}</td>"
            f"<td>{sheet['numeric_constant_cells']}</td>"
            f"<td>{sheet['blank_cells_inside_used_range']}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_issue_rows(issues):
    if not issues:
        return '<tr><td colspan="9">No issues detected.</td></tr>'

    rows = []
    for issue in issues:
        rows.append(
            "<tr>"
            f"<td>{render_severity_badge(issue['severity'])}</td>"
            f"<td>{html_value(issue['type'])}</td>"
            f"<td>{html_value(issue['sheet'])}</td>"
            f"<td>{html_value(issue['cell'])}</td>"
            f"<td>{html_value(issue['metric'])}</td>"
            f"<td>{html_value(issue['period'])}</td>"
            f"<td>{html_value(issue['message'])}</td>"
            f"<td>{html_value(issue['business_impact'])}</td>"
            f"<td>{html_value(issue['suggested_fix'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html_report(report):
    risk_level = html_value(report["risk_level"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Finance Report Checker</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background: #f6f7f9;
      color: #1f2933;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9dee7;
      padding: 28px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
    }}
    section {{
      margin-top: 28px;
    }}
    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 16px;
    }}
    .summary-item {{
      background: #f6f7f9;
      border: 1px solid #d9dee7;
      padding: 12px;
    }}
    .label {{
      color: #52606d;
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .value {{
      font-size: 20px;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
    }}
    th, td {{
      border: 1px solid #d9dee7;
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef2f7;
    }}
    .badge {{
      display: inline-block;
      min-width: 56px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-align: center;
      text-transform: uppercase;
    }}
    .badge.high {{
      background: #fde2e2;
      color: #9b1c1c;
    }}
    .badge.medium {{
      background: #fff3cd;
      color: #7a4d00;
    }}
    .badge.low {{
      background: #dff3e3;
      color: #0f6b2f;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Finance Report Checker</h1>
    <div class="summary">
      <div class="summary-item">
        <div class="label">Workbook</div>
        <div class="value">{html_value(report["workbook"])}</div>
      </div>
      <div class="summary-item">
        <div class="label">Risk Score</div>
        <div class="value">{report["risk_score"]}</div>
      </div>
      <div class="summary-item">
        <div class="label">Risk Level</div>
        <div class="value">{risk_level}</div>
      </div>
    </div>

    <section>
      <h2>Executive Summary</h2>
      <p>{html_value(report["executive_summary"])}</p>
    </section>

    <section>
      <h2>Issue Counts by Severity</h2>
      <table>
        <thead>
          <tr><th>Severity</th><th>Count</th></tr>
        </thead>
        <tbody>
          {render_issue_counts(report["issue_counts"])}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Sheet Statistics</h2>
      <table>
        <thead>
          <tr>
            <th>Sheet</th>
            <th>Used Range</th>
            <th>Non-empty Cells</th>
            <th>Formula Cells</th>
            <th>Numeric Constant Cells</th>
            <th>Blank Cells Inside Used Range</th>
          </tr>
        </thead>
        <tbody>
          {render_sheet_rows(report["sheets"])}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Issues</h2>
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Type</th>
            <th>Sheet</th>
            <th>Cell</th>
            <th>Metric</th>
            <th>Period</th>
            <th>Message</th>
            <th>Business Impact</th>
            <th>Suggested Fix</th>
          </tr>
        </thead>
        <tbody>
          {render_issue_rows(report["issues"])}
        </tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def save_report_outputs(file_path, report, output_dir=None, checked_filename=None):
    workbook_path = Path(file_path)
    output_dir = Path(output_dir) if output_dir is not None else PROJECT_ROOT
    report_path = output_dir / "report.json"
    html_report_path = output_dir / "report.html"
    checked_filename = checked_filename or f"checked_{workbook_path.name}"
    checked_path = output_dir / checked_filename

    output_dir.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, indent=2)
    report_path.write_text(output + "\n", encoding="utf-8")
    html_report_path.write_text(render_html_report(report), encoding="utf-8")
    save_annotated_workbook(workbook_path, report, checked_path)
