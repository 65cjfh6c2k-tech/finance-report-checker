import json
import os


DISABLED_AI_INSIGHTS = {
    "enabled": False,
    "executive_summary": "",
    "key_insights": [],
    "management_note": "",
}

DEFAULT_MODEL = "gpt-5-mini"


def build_ai_context(report: dict) -> dict:
    """Build a sanitized context for AI insights without workbook cell contents."""
    return {
        "workbook": report.get("workbook"),
        "risk_score": report.get("risk_score"),
        "risk_level": report.get("risk_level"),
        "issue_counts": report.get("issue_counts", {}),
        "issues": [
            {
                "sheet": issue.get("sheet"),
                "cell": issue.get("cell"),
                "metric": issue.get("metric"),
                "period": issue.get("period"),
                "type": issue.get("type"),
                "severity": issue.get("severity"),
                "message": issue.get("message"),
                "business_impact": issue.get("business_impact"),
                "suggested_fix": issue.get("suggested_fix"),
            }
            for issue in report.get("issues", [])
        ],
        "charts": [
            {
                "title": chart.get("title"),
                "insight": chart.get("insight"),
                "series_names": [
                    series.get("name") for series in chart.get("series", [])
                ],
            }
            for chart in report.get("charts", [])
        ],
    }


def generate_ai_insights(report: dict) -> dict:
    if not ai_insights_enabled():
        return dict(DISABLED_AI_INSIGHTS)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return dict(DISABLED_AI_INSIGHTS)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a finance QA assistant. Use only the sanitized "
                        "JSON context provided. Do not infer from unavailable "
                        "workbook cells. Return concise, practical finance "
                        "review guidance as valid JSON."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(build_ai_context(report), indent=2),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "finance_report_ai_insights",
                    "schema": ai_insights_schema(),
                    "strict": True,
                }
            },
        )
        insights = json.loads(response.output_text)
        return normalize_ai_insights(insights)
    except Exception:
        return dict(DISABLED_AI_INSIGHTS)


def ai_insights_enabled():
    return os.getenv("AI_INSIGHTS_ENABLED", "").strip().lower() == "true"


def ai_insights_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "enabled",
            "executive_summary",
            "key_insights",
            "management_note",
        ],
        "properties": {
            "enabled": {"type": "boolean"},
            "executive_summary": {"type": "string"},
            "key_insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "title",
                        "severity",
                        "explanation",
                        "recommended_action",
                    ],
                    "properties": {
                        "title": {"type": "string"},
                        "severity": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "explanation": {"type": "string"},
                        "recommended_action": {"type": "string"},
                    },
                },
            },
            "management_note": {"type": "string"},
        },
    }


def normalize_ai_insights(insights):
    key_insights = []
    for insight in insights.get("key_insights", []):
        severity = str(insight.get("severity", "medium")).lower()
        if severity not in {"high", "medium", "low"}:
            severity = "medium"

        key_insights.append(
            {
                "title": str(insight.get("title", "")),
                "severity": severity,
                "explanation": str(insight.get("explanation", "")),
                "recommended_action": str(insight.get("recommended_action", "")),
            }
        )

    return {
        "enabled": True,
        "executive_summary": str(insights.get("executive_summary", "")),
        "key_insights": key_insights,
        "management_note": str(insights.get("management_note", "")),
    }
