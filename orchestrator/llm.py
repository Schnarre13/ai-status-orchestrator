import json
import os
import re
from pathlib import Path

from anthropic import Anthropic

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
_client = None


def client():
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is missing. Add it to your .env file.")
        _client = Anthropic(api_key=key)
    return _client


def model():
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-5")


def prompt(name: str) -> str:
    return (PROMPTS / f"{name}.txt").read_text(encoding="utf-8")


def ask(system: str, user: str, max_tokens: int = 3000) -> str:
    """One Claude call. The system prompt carries the agent's instructions."""
    resp = client().messages.create(
        model=model(),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "text") == "text").strip()


def parse_json(text: str):
    """Pull the first JSON array or object out of a model response."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in model output: {text[:300]}")
    return json.loads(match.group(1))
