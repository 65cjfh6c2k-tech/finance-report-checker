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
    ("draft_note", "Draft Note for Management"),
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
    issues = report.get("issues", [])
    return {
        "workbook": report.get("workbook"),
        "risk_score": report.get("risk_score"),
        "risk_level": report.get("risk_level"),
        "issue_counts": report.get("issue_counts", {}),
        "top_issues": [
            issue_context(issue) for issue in prioritize_issues(issues)[:8]
        ],
        "issues": [
            issue_context(issue)
            for issue in issues
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


def issue_context(issue):
    return {
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


def prioritize_issues(issues):
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    type_rank = {
        "total_formula_mismatch": 0,
        "formula_inconsistency_in_row": 1,
        "hardcoded_value_among_formulas": 2,
        "variance_spike_between_periods": 3,
        "blank_cell_between_values": 4,
    }
    return sorted(
        issues,
        key=lambda issue: (
            severity_rank.get(issue.get("severity"), 9),
            type_rank.get(issue.get("type"), 9),
            str(issue.get("sheet") or ""),
            str(issue.get("cell") or ""),
        ),
    )


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
                "content": build_ai_prompt(report),
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
        insights = parse_json_response(content)
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
        "You are writing as an FP&A manager preparing a management review note "
        "for a CFO or CEO.\n\n"
        "Use only the sanitized QA context below. Do not infer from unavailable "
        "workbook cells. Do not invent numbers, variances, sheets, cells, "
        "metrics, or periods that are not present in the context. Write in a "
        "management-ready finance voice: direct, specific, calm, and practical.\n\n"
        "Return valid JSON only. Do not use markdown inside JSON values except "
        "plain strings in arrays. Keep the existing JSON shape exactly:\n"
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
        '    "executive_summary": "3-4 sentences.",\n'
        '    "key_movements": ["2-4 movement bullets."],\n'
        '    "data_quality_risks": ["3-5 data quality bullets."],\n'
        '    "recommended_actions": ["3-5 practical actions."],\n'
        '    "draft_note": "One polished paragraph.",\n'
        '    "supporting_charts": [\n'
        "      {\n"
        '        "chart_title": "Exact chart title from sanitized context.",\n'
        '        "reason": "Why this chart supports a management-relevant insight."\n'
        "      }\n"
        "    ]\n"
        "  }\n"
        "}\n\n"
        "Management memo requirements:\n"
        "- executive_summary must be 3-4 sentences. It must say whether the "
        "workbook is ready to send or requires review first. Mention risk_score "
        "and risk_level when available. If any high-severity issue exists, name "
        "the most important high-severity issue with sheet, cell, metric, and "
        "period when available.\n"
        "- key_movements must include only actual financial movements or "
        "variance items, not formula/data quality issues. Reference metric and "
        "period where available. If movement data is not reliable or not "
        "available, include exactly: \"No reliable movement insight available "
        "from the current extracted data.\" Then add the reason in the same "
        "string if supported by the context.\n"
        "- data_quality_risks must include 3-5 bullets, ordered by severity "
        "with high severity first. Each bullet must reference specific sheet, "
        "cell, metric, and period where available, and explain why it matters "
        "financially.\n"
        "- recommended_actions must include 3-5 practical actions ordered by "
        "priority. Avoid generic phrases such as \"ensure accuracy\", "
        "\"review the report\", or \"check everything\". Use action wording like "
        "\"Review OPEX Detail F9 for May and confirm the total includes all "
        "relevant detail rows.\"\n"
        "- draft_note must be one polished, copy-ready paragraph "
        "for a CFO or CEO. If high-risk issues exist, say the report should be "
        "reviewed before final distribution, but do not sound alarmist. Do not "
        "say \"attached report\" unless the context requires it.\n"
        "- Separate business movements from data quality issues.\n"
        "- Select supporting_charts only when the chart directly supports a "
        "specific key movement or data quality risk stated in the memo. If a "
        "chart is only generally contextual, not directly relevant, or not "
        "impacted by the current high-priority issues, do not include it. If no "
        "chart directly supports the memo, return an empty supporting_charts "
        "array.\n\n"
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
                    "draft_note",
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
                    "draft_note": {"type": "string"},
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
        chart_title = str(chart.get("chart_title", ""))
        reason = str(chart.get("reason", ""))
        if not chart_title or not is_direct_supporting_chart_reason(reason):
            continue

        supporting_charts.append(
            {
                "chart_title": chart_title,
                "reason": reason,
            }
        )

    draft_note = (
        memo.get("draft_note")
        or memo.get("draft_note_for_management")
        or insights.get("management_note", "")
    )

    return {
        "executive_summary": str(
            memo.get("executive_summary") or insights.get("executive_summary", "")
        ),
        "key_movements": stringify_list(memo.get("key_movements", [])),
        "data_quality_risks": stringify_list(memo.get("data_quality_risks", [])),
        "recommended_actions": stringify_list(memo.get("recommended_actions", [])),
        "draft_note": str(draft_note),
        "supporting_charts": supporting_charts,
    }


def stringify_list(values):
    return [str(value) for value in values if value is not None]


def is_direct_supporting_chart_reason(reason):
    normalized = reason.strip().lower()
    if not normalized:
        return False

    non_supporting_phrases = [
        "not impacted",
        "not directly",
        "not relevant",
        "not related",
        "only contextual",
        "generally contextual",
        "general context",
        "background context",
        "does not support",
        "doesn't support",
    ]
    return not any(phrase in normalized for phrase in non_supporting_phrases)


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
