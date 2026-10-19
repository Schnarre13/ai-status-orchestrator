import json
from datetime import datetime

from orchestrator import llm


def _inputs(state):
    return (
        "WEEK: " + state["week"]
        + "\n\nWORKSTREAM UPDATES:\n" + "\n\n".join(state["workstream_updates"].values())
        + "\n\nMEETING TRANSCRIPT:\n" + state["transcript"]
        + "\n\nCOMPUTED BUDGET METRICS ($M):\n" + json.dumps(state["budget_metrics"], indent=1)
        + "\n\nRAID ITEMS (new this week):\n" + json.dumps(state["new_raid_items"], indent=1)
    )


def draft_status(state):
    """Status agent: writes the decision-ready report. On a retry, it gets the validator's findings."""
    attempts = state.get("attempts", 0) + 1
    if attempts == 1:
        draft = llm.ask(llm.prompt("status_agent"), _inputs(state))
    else:
        findings = "\n".join(f"- {f}" for f in state["validation"]["findings"])
        draft = llm.ask(llm.prompt("status_agent"),
                        _inputs(state) + "\n\nPREVIOUS DRAFT:\n" + state["draft"]
                        + "\n\n" + llm.prompt("redraft") + findings)
    return {"draft": draft, "attempts": attempts,
            "audit": [{"step": "status_agent", "at": datetime.now().isoformat(timespec="seconds"),
                       "detail": f"draft {attempts} written ({len(draft)} characters)"}]}
