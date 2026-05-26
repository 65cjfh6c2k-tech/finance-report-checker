ISSUE_TYPES_FOR_SUMMARY = {
    "hardcoded_value_among_formulas": "hardcoded values among formulas",
    "total_formula_mismatch": "total formulas that may omit detail rows",
    "variance_spike_between_periods": "large period-over-period variances",
    "formula_inconsistency_in_row": "formula inconsistencies",
    "blank_cell_between_values": "blank cells between values",
}


def build_issue_counts(issues):
    counts = {"high": 0, "medium": 0, "low": 0}
    for issue in issues:
        severity = issue.get("severity")
        if severity in counts:
            counts[severity] += 1

    return counts


def calculate_risk_score(issue_counts):
    score = 100
    score -= issue_counts["high"] * 18
    score -= issue_counts["medium"] * 6
    score -= issue_counts["low"] * 2
    return max(score, 0)


def calculate_risk_level(risk_score):
    if risk_score >= 85:
        return "low"
    if risk_score >= 60:
        return "medium"
    return "high"


def join_summary_items(items):
    if not items:
        return "no major issue categories"
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def build_executive_summary(issue_counts, issues):
    total_issues = sum(issue_counts.values())
    issue_word = "issue" if total_issues == 1 else "issues"

    issue_type_order = [
        "hardcoded_value_among_formulas",
        "total_formula_mismatch",
        "variance_spike_between_periods",
        "formula_inconsistency_in_row",
        "blank_cell_between_values",
    ]
    detected_types = {issue["type"] for issue in issues}
    main_risks = [
        ISSUE_TYPES_FOR_SUMMARY[issue_type]
        for issue_type in issue_type_order
        if issue_type in detected_types
    ]

    return (
        f"The workbook contains {total_issues} potential {issue_word}: "
        f"{issue_counts['high']} high, {issue_counts['medium']} medium, "
        f"and {issue_counts['low']} low. The main risks are "
        f"{join_summary_items(main_risks)}."
    )


def add_risk_summary(report):
    issue_counts = build_issue_counts(report["issues"])
    risk_score = calculate_risk_score(issue_counts)

    report["issue_counts"] = issue_counts
    report["risk_score"] = risk_score
    report["risk_level"] = calculate_risk_level(risk_score)
    report["executive_summary"] = build_executive_summary(
        issue_counts, report["issues"]
    )
