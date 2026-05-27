import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"
ENABLED_VALUES = {"true", "1", "yes", "on"}

DISABLED_AI_INSIGHTS = {
    "enabled": False,
    "executive_summary": "",
    "key_insights": [],
    "management_note": "",
    "management_memo": {},
    "error": "AI insights disabled or API key missing.",
}

MEMO_FIELDS = [
    ("executive_summary", "Executive Summary"),
    ("key_movements", "Key Movements"),
    ("data_quality_risks", "Data Quality Risks"),
    ("recommended_actions", "Recommended Actions"),
    ("draft_note_for_management", "Draft Note for Management"),
]

LOCAL_AI_UNAVAILABLE = {
    "enabled": False,
    "executive_summary": "",
    "key_insights": [],
    "management_note": "",
    "management_memo": {},
    "error": "Local AI is not available. Start Ollama and check the configured model.",
}

LOCAL_AI_INVALID_JSON = {
    "enabled": False,
    "executive_summary": "",
    "key_insights": [],
    "management_note": "",
    "management_memo": {},
    "error": "Local AI returned an invalid JSON response.",
}

DEFAULT_PROVIDER = "ollama"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"


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
                "x_labels": chart.get("x", []),
                "series_names": [
                    series.get("name") for series in chart.get("series", [])
                ],
            }
            for chart in report.get("charts", [])
        ],
    }


def generate_ai_insights(report: dict) -> dict:
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)

    enabled_raw = os.getenv("AI_INSIGHTS_ENABLED", "")
    is_enabled = ai_insights_enabled(enabled_raw)
    provider = os.getenv("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()

    print(f"AI provider: {provider}")
    print(f"AI_INSIGHTS_ENABLED raw value: {enabled_raw!r}")

    if not is_enabled:
        return disabled_ai_insights()

    if provider == "ollama":
        return generate_ollama_insights(report)

    if provider == "openai":
        return generate_openai_insights(report)

    print(f"AI provider error: unsupported provider {provider!r}")
    return disabled_ai_insights(f"Unsupported AI provider: {provider}.")


def generate_ollama_insights(report):
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    print(f"Ollama model: {model}")
    print(f"Ollama base URL: {base_url}")
    print("Ollama request started")

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a finance reporting QA assistant. Return only valid "
                    "JSON. Do not use markdown. Do not wrap output in code fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Use only the sanitized AI context below. Do not infer from "
                    "unavailable workbook cells.\n\n"
                    "Return exactly this JSON object shape:\n"
                    "{\n"
                    '  "enabled": true,\n'
                    '  "executive_summary": "Short paragraph for finance user.",\n'
                    '  "key_insights": [\n'
                    "    {\n"
                    '      "title": "Short title",\n'
                    '      "severity": "high",\n'
                    '      "explanation": "What this means.",\n'
                    '      "recommended_action": "What to review or fix."\n'
                    "    }\n"
                    "  ],\n"
                    '  "management_note": "Short note the user could adapt before sending report.",\n'
                    '  "management_memo": {\n'
                    '    "executive_summary": "2-3 specific sentences for management.",\n'
                    '    "key_movements": ["2-4 bullets about notable movements."],\n'
                    '    "data_quality_risks": ["2-4 bullets about report quality risks."],\n'
                    '    "recommended_actions": ["2-4 concrete actions before sending."],\n'
                    '    "draft_note_for_management": "One concise paragraph the finance user can copy.",\n'
                    '    "supporting_charts": [\n'
                    "      {\n"
                    '        "chart_title": "Exact chart title from sanitized context.",\n'
                    '        "reason": "Why this chart supports a management-relevant insight."\n'
                    "      }\n"
                    "    ]\n"
                    "  }\n"
                    "}\n\n"
                    "Select supporting_charts only when a chart supports a "
                    "management-relevant movement, risk, or recommended action. "
                    "If no chart is useful, return an empty supporting_charts array. "
                    "Avoid generic phrases. Reference specific sheet, cell, metric, "
                    "and period values where available.\n\n"
                    "Sanitized AI context:\n"
                    f"{json.dumps(build_ai_context(report), indent=2)}"
                ),
            },
        ],
    }

    try:
        request = urllib.request.Request(
            f"{base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            print(f"Ollama HTTP status: {response.status}")
            response_data = json.loads(response.read().decode("utf-8"))

        print("Ollama request finished")
        content = response_data.get("message", {}).get("content", "")
        print(f"Ollama message.content exists: {bool(content)}")
        insights = json.loads(content)
        print("Ollama JSON parse success")
        return normalize_ai_insights(insights)
    except json.JSONDecodeError as error:
        print("Ollama JSON parse failure")
        print(f"Ollama response preview: {safe_response_preview(locals().get('content', ''))}")
        print(f"Ollama error: {error.__class__.__name__}: {error}")
        return dict(LOCAL_AI_INVALID_JSON)
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"Ollama error: {error.__class__.__name__}: {error}")
        return dict(LOCAL_AI_UNAVAILABLE)
    except Exception as error:
        print(f"Ollama error: {error.__class__.__name__}: {error}")
        return dict(LOCAL_AI_UNAVAILABLE)


def generate_openai_insights(report):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

    print(f"OPENAI_MODEL: {model}")
    print(f"OPENAI_API_KEY exists: {bool(api_key)}")

    if not api_key:
        return disabled_ai_insights()

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
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
                    "content": build_ai_prompt(report),
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
    except Exception as error:
        print(f"OpenAI error: {error.__class__.__name__}: {error}")
        return disabled_ai_insights(f"AI insights failed: {error.__class__.__name__}.")


def ai_insights_enabled(raw_value=None):
    if raw_value is None:
        load_dotenv(dotenv_path=DOTENV_PATH, override=True)
        raw_value = os.getenv("AI_INSIGHTS_ENABLED", "")
    return raw_value.strip().lower() in ENABLED_VALUES


def build_ai_prompt(report):
    return (
        "Use only the sanitized AI context below. Do not infer from unavailable "
        "workbook cells.\n\n"
        "Return a finance-facing JSON response with executive insights and a "
        "management_memo. The memo executive_summary should be 2-3 specific "
        "sentences. The key_movements, data_quality_risks, and "
        "recommended_actions arrays should each contain 2-4 useful bullets when "
        "the context supports them. The draft_note_for_management should be one "
        "concise paragraph that can be copied to management. Avoid generic "
        "phrases. Reference specific sheet, cell, metric, and period values "
        "where available. In management_memo.supporting_charts, select only "
        "charts that support a management-relevant movement, risk, or "
        "recommended action. If no chart is useful, return an empty "
        "supporting_charts array.\n\n"
        "Sanitized AI context:\n"
        f"{json.dumps(build_ai_context(report), indent=2)}"
    )


def disabled_ai_insights(error_message=None):
    insights = dict(DISABLED_AI_INSIGHTS)
    if error_message:
        insights["error"] = error_message
    return insights


def safe_response_preview(content):
    return str(content).replace("\n", " ")[:500]


def parse_json_response(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        extracted = extract_json_object(content)
        if extracted is None:
            raise
        return json.loads(extracted)


def extract_json_object(text):
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        character = text[index]
        if escape:
            escape = False
            continue
        if character == "\\":
            escape = True
            continue
        if character == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def ai_insights_schema():
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "enabled",
            "executive_summary",
            "key_insights",
            "management_note",
            "management_memo",
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
            "management_memo": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "executive_summary",
                    "key_movements",
                    "data_quality_risks",
                    "recommended_actions",
                    "draft_note_for_management",
                    "supporting_charts",
                ],
                "properties": {
                    "executive_summary": {"type": "string"},
                    "key_movements": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "data_quality_risks": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "recommended_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "draft_note_for_management": {"type": "string"},
                    "supporting_charts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["chart_title", "reason"],
                            "properties": {
                                "chart_title": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                        },
                    },
                },
            },
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
        "management_memo": normalize_management_memo(insights),
    }


def normalize_management_memo(insights):
    memo = insights.get("management_memo") or {}
    supporting_charts = []
    for chart in memo.get("supporting_charts", []):
        supporting_charts.append(
            {
                "chart_title": str(chart.get("chart_title", "")),
                "reason": str(chart.get("reason", "")),
            }
        )

    return {
        "executive_summary": str(
            memo.get("executive_summary") or insights.get("executive_summary", "")
        ),
        "key_movements": stringify_list(memo.get("key_movements", [])),
        "data_quality_risks": stringify_list(memo.get("data_quality_risks", [])),
        "recommended_actions": stringify_list(memo.get("recommended_actions", [])),
        "draft_note_for_management": str(
            memo.get("draft_note_for_management") or insights.get("management_note", "")
        ),
        "supporting_charts": supporting_charts,
    }


def stringify_list(values):
    return [str(value) for value in values if value is not None]


def has_management_memo(ai_insights):
    if not ai_insights or not ai_insights.get("enabled"):
        return False

    memo = ai_insights.get("management_memo") or {}
    return any(memo.get(field) for field, _label in MEMO_FIELDS)


def render_management_memo_markdown(ai_insights):
    memo = (ai_insights or {}).get("management_memo") or {}
    lines = ["# Management Memo", ""]

    for field, label in MEMO_FIELDS:
        value = memo.get(field)
        lines.extend([f"## {label}", ""])
        if isinstance(value, list):
            if value:
                lines.extend([f"- {item}" for item in value])
            else:
                lines.append("No specific items identified.")
        else:
            lines.append(str(value or "No specific items identified."))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
