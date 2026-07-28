"""Ask AI: answers a free-form operational question using the same KPI
context payload as the AI Operational Summary.

Kept independent of Streamlit - this module only knows about the question
string, the KPI payload dict, and the OpenAI API.
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()

_MODEL = "gpt-4o-mini"

_SYSTEM_PROMPT = """You are an experienced Warehouse Operations Manager.

Answer the user's question using ONLY the KPI data provided.

Requirements:
- Be concise.
- Use business language.
- Do not invent facts.
- If the answer cannot be determined from the provided KPI data, clearly say so.
- Provide actionable recommendations where appropriate."""


@dataclass
class AskAIResult:
    answer: str
    is_fallback: bool = False


_NO_API_KEY_RESULT = AskAIResult(
    answer=(
        "Ask AI is unavailable: no OPENAI_API_KEY is configured. Set it in a "
        ".env file to enable this feature."
    ),
    is_fallback=True,
)


def build_prompt(question: str, kpi_payload: dict[str, Any]) -> str:
    """Serialize the question + KPI payload into the user-message content sent to the model."""
    return f"Question: {question}\n\nHere is today's warehouse KPI data as JSON:\n\n{json.dumps(kpi_payload, indent=2)}"


def ask(question: str, kpi_payload: dict[str, Any]) -> AskAIResult:
    """Call the OpenAI API to answer a natural-language operational question.

    Falls back to a static, clearly-labeled message if the question is empty,
    the API key is missing, or the call fails - never raises.
    """
    if not question or not question.strip():
        return AskAIResult(answer="Please enter a question.", is_fallback=True)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _NO_API_KEY_RESULT

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, kpi_payload)},
            ],
            temperature=0.3,
        )
        answer = (response.choices[0].message.content or "").strip()
        return AskAIResult(answer=answer)
    except OpenAIError as exc:
        return AskAIResult(
            answer=f"Ask AI is unavailable: the OpenAI API returned an error ({exc}).",
            is_fallback=True,
        )
