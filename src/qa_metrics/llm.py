"""Optional LLM-generated narrative over aggregate metrics and signals only."""

from __future__ import annotations

import json
import os
from typing import Any


SYSTEM_PROMPT = """You are a quality engineering metrics advisor writing for engineering leaders. Summarize only patterns supported by the aggregate metrics and supplied signals. Do not rank teams or individuals, infer causation, invent targets, or claim a release is safe. State uncertainty and suggest a few investigation questions. Return concise plain text, not markdown tables."""


def generate_metric_narrative(summary: dict[str, Any], insights: list[dict[str, Any]], api_key: str | None = None) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY to use the optional AI narrative.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('Install the optional dependency with: pip install -e ".[llm]"') from exc
    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"aggregate_metrics": summary, "rule_based_signals": insights}, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("The model returned an empty narrative.")
    return content.strip()

