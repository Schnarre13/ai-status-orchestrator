import json
from datetime import datetime

from orchestrator import llm


def extract_raid(state):
    """RAID agent: proposes new RAID items, each backed by a quote from the source text."""
    user = (
        "EXISTING RAID LOG:\n" + json.dumps(state["raid_log"], indent=1)
        + "\n\nWORKSTREAM UPDATES:\n" + "\n\n".join(state["workstream_updates"].values())
        + "\n\nMEETING TRANSCRIPT:\n" + state["transcript"]
    )
    items = llm.parse_json(llm.ask(llm.prompt("raid_agent"), user))

    # Guardrail: drop any item whose quoted evidence isn't actually in the sources.
    sources = state["transcript"] + "\n".join(state["workstream_updates"].values())
    kept, dropped = [], 0
    for it in items:
        quote = (it.get("evidence") or "").strip().strip('"')
        if quote and quote[:60] in sources:
            kept.append(it)
        else:
            dropped += 1
    return {"new_raid_items": kept,
            "audit": [{"step": "raid_agent", "at": datetime.now().isoformat(timespec="seconds"),
                       "detail": f"{len(kept)} items proposed with verified evidence; {dropped} dropped for unverifiable quotes"}]}
