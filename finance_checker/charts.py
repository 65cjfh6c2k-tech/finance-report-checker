from finance_checker.rules import (
    get_metric_for_row,
    get_period_for_column,
    is_aggregate_period,
    is_empty,
    normalized_label,
    should_ignore_issue_sheet,
)


MONTH_HEADERS = {
    "jan",
    "january",
    "feb",
    "february",
    "mar",
    "march",
    "apr",
    "april",
    "may",
    "jun",
    "june",
    "jul",
    "july",
    "aug",
    "august",
    "sep",
    "sept",
    "september",
    "oct",
    "october",
    "nov",
    "november",
    "dec",
    "december",
}


def build_chart_specs(workbook, get_used_bounds):
    """Create deterministic chart recommendations from monthly finance rows."""
    candidates = []

    for sheet in workbook.worksheets:
        if sheet.sheet_state != "visible" or should_ignore_issue_sheet(sheet):
            continue

        bounds = get_used_bounds(sheet)
        if bounds is None:
            continue

        candidates.extend(get_sheet_chart_candidates(sheet, bounds))

    chart_specs = []
    for category in ("revenue", "gross", "profitability"):
        candidate = choose_best_candidate(candidates, category)
        if candidate is not None:
            chart_specs.append(format_chart_spec(candidate, category))

    return chart_specs[:3]


def get_sheet_chart_candidates(sheet, bounds):
    min_row, min_col, max_row, max_col = bounds
    period_columns = get_monthly_period_columns(sheet, min_col, max_col)
    if len(period_columns) < 3:
        return []

    candidates = []
    for row_number in range(min_row + 1, max_row + 1):
        metric = get_metric_for_row(sheet, row_number)
        if is_empty(metric):
            continue

        values = []
        numeric_count = 0
        for _, column in period_columns:
            value = sheet.cell(row=row_number, column=column).value
            if is_number(value):
                values.append(float(value))
                numeric_count += 1
            else:
                values.append(None)

        if numeric_count < 3:
            continue

        categories = categorize_metric(metric)
        if not categories:
            continue

        for category in categories:
            candidates.append(
                {
                    "category": category,
                    "metric": str(metric),
                    "sheet": sheet.title,
                    "x": [period for period, _ in period_columns],
                    "y": values,
                    "score": score_metric(metric, category, sheet.title),
                }
            )

    return candidates


def get_monthly_period_columns(sheet, min_col, max_col):
    period_columns = []
    for column in range(min_col + 1, max_col + 1):
        period = get_period_for_column(sheet, column)
        if is_empty(period) or is_aggregate_period(period):
            continue
        if is_month_header(period):
            period_columns.append((str(period), column))

    return period_columns


def is_month_header(value):
    normalized = normalized_label(value)
    return normalized in MONTH_HEADERS


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def categorize_metric(metric):
    normalized = normalized_label(metric)
    categories = []

    if "revenue" in normalized or ("sales" in normalized and "cost" not in normalized):
        categories.append("revenue")
    if "gross profit" in normalized or "gross margin" in normalized:
        categories.append("gross")
    if (
        "opex" in normalized
        or "operating expenses" in normalized
        or "ebitda" in normalized
        or "net income" in normalized
    ):
        categories.append("profitability")

    return categories


def score_metric(metric, category, sheet_title):
    normalized = normalized_label(metric)
    score = 0

    if "p&l" in normalized_label(sheet_title) or "income" in normalized_label(sheet_title):
        score += 10
    if "total" in normalized:
        score += 20
    if category == "revenue" and ("net sales" in normalized or "revenue" in normalized):
        score += 30
    if category == "gross" and ("gross profit" in normalized or "gross margin" in normalized):
        score += 30
    if category == "profitability":
        if "ebitda" in normalized:
            score += 35
        elif "net income" in normalized:
            score += 30
        elif "total operating expenses" in normalized or "opex" in normalized:
            score += 25

    return score


def choose_best_candidate(candidates, category):
    category_candidates = [
        candidate for candidate in candidates if candidate["category"] == category
    ]
    if not category_candidates:
        return None

    return max(category_candidates, key=lambda candidate: candidate["score"])


def format_chart_spec(candidate, category):
    titles = {
        "revenue": "Revenue / Sales Trend",
        "gross": "Gross Profit / Gross Margin Trend",
        "profitability": "OPEX / EBITDA / Net Income Trend",
    }

    return {
        "title": titles[category],
        "type": "line",
        "x": candidate["x"],
        "series": [
            {
                "name": candidate["metric"],
                "y": candidate["y"],
            }
        ],
        "insight": build_insight(candidate),
    }


def build_insight(candidate):
    first = first_numeric_point(candidate)
    last = last_numeric_point(candidate)
    if first is None or last is None:
        return f"{candidate['metric']} has limited monthly data available for trend analysis."

    first_period, first_value = first
    last_period, last_value = last
    if first_value == 0:
        return (
            f"{candidate['metric']} starts at zero in {first_period}; review the monthly "
            "trend for directional movement."
        )

    change = (last_value - first_value) / abs(first_value)
    if abs(change) < 0.05:
        direction = "was broadly flat"
    elif change > 0:
        direction = "increased"
    else:
        direction = "decreased"

    return (
        f"{candidate['metric']} {direction} from {first_period} to {last_period} "
        "based on the monthly values available."
    )


def first_numeric_point(candidate):
    for period, value in zip(candidate["x"], candidate["y"]):
        if value is not None:
            return period, value
    return None


def last_numeric_point(candidate):
    for period, value in reversed(list(zip(candidate["x"], candidate["y"]))):
        if value is not None:
            return period, value
    return None
