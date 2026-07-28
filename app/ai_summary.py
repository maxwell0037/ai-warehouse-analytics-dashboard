"""AI Operational Summary: builds the prompt from the KPI payload, calls the
OpenAI API, and returns a business summary.

Kept independent of Streamlit and of dashboard rendering - this module only
knows about the KPI payload dict and the OpenAI API.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """You are an experienced Warehouse Operations Manager.

Review today's warehouse KPIs and write an executive summary.

Requirements:
- Maximum 200 words.
- Identify the biggest operational issues.
- Explain likely causes using the provided KPI data.
- Mention strong performance where appropriate.
- Provide exactly three actionable recommendations.
- Use professional business language.
- Do not invent information not present in the KPI data.

Respond as JSON with exactly this shape:
{"summary": "<the executive summary>", "recommendations": ["<rec 1>", "<rec 2>", "<rec 3>"]}"""


@dataclass
class AISummaryResult:
    summary: str
    recommendations: list[str] = field(default_factory=list)
    is_fallback: bool = False


_NO_API_KEY_RESULT = AISummaryResult(
    summary=(
        "AI summary unavailable: no OPENAI_API_KEY is configured. Set it in a "
        ".env file to enable AI-generated summaries. In the meantime, review "
        "the KPI Scorecards and Operational Root Cause Analysis sections below."
    ),
    is_fallback=True,
)


def build_prompt(kpi_payload: dict[str, Any]) -> str:
    """Serialize the KPI payload into the user-message content sent to the model."""
    return "Here is today's warehouse KPI data as JSON:\n\n" + json.dumps(kpi_payload, indent=2)


def generate_summary(kpi_payload: dict[str, Any]) -> AISummaryResult:
    """Call the OpenAI API to generate the executive summary.

    Falls back to a static, clearly-labeled message if the API key is missing,
    the API call fails, or the response can't be parsed - never raises.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _NO_API_KEY_RESULT

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(kpi_payload)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        parsed = json.loads(response.choices[0].message.content)
        return AISummaryResult(
            summary=str(parsed["summary"]).strip(),
            recommendations=[str(r) for r in parsed.get("recommendations", [])],
        )
    except OpenAIError as exc:
        return AISummaryResult(
            summary=f"AI summary unavailable: the OpenAI API returned an error ({exc}).",
            is_fallback=True,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return AISummaryResult(
            summary=f"AI summary unavailable: could not parse the model's response ({exc}).",
            is_fallback=True,
        )
