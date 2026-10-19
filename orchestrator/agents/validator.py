import json
import re
from datetime import datetime

REQUIRED_SECTIONS = ["## Overall", "## Decisions needed this week", "## Workstreams", "## Top risks", "## Budget"]
NUMBER = re.compile(r"\$?\d+(?:\.\d+)?%?")


def _norm(tok: str) -> str:
    """Compare numbers by value, so "$0.30" and "0.3" count as the same figure."""
    raw = tok.replace("$", "").replace("%", "")
    try:
        return f"{float(raw):g}"
    except ValueError:
        return raw


def validate(state):
    """Validator: deterministic checks, so a draft can't reach a person with an unsupported number."""
    draft = state["draft"]
    sources = (state["transcript"] + "\n".join(state["workstream_updates"].values())
               + json.dumps(state["budget_metrics"]) + json.dumps(state["new_raid_items"]) + " " + state["week"])
    allowed = {_norm(t) for t in NUMBER.findall(sources)}
    allowed |= {"1", "2", "3", "4", "5"}          # list numbering and section numbers

    findings = []
    for sec in REQUIRED_SECTIONS:
        if sec.lower() not in draft.lower():
            findings.append(f"Missing required section: {sec}")
    for tok in sorted(set(NUMBER.findall(draft))):
        if _norm(tok) not in allowed:
            findings.append(f"Number not found in any source: {tok}")
    for name in state["workstream_updates"]:
        if name.lower() not in draft.lower():
            findings.append(f"Workstream not covered: {name}")

    passed = not findings
    return {"validation": {"passed": passed, "findings": findings},
            "audit": [{"step": "validator", "at": datetime.now().isoformat(timespec="seconds"),
                       "detail": "passed" if passed else f"{len(findings)} findings: " + "; ".join(findings)}]}
