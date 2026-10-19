from datetime import datetime

from langgraph.types import interrupt


def human_review(state):
    """Human approval gate. The run pauses here until a person approves, edits, or rejects."""
    response = interrupt({
        "draft": state["draft"],
        "validation": state["validation"],
        "new_raid_items": state["new_raid_items"],
    })
    decision = response.get("decision", "reject")
    final = response.get("edited_report") or state["draft"]
    return {"decision": decision, "final_report": final if decision != "reject" else "",
            "audit": [{"step": "human_review", "at": datetime.now().isoformat(timespec="seconds"),
                       "detail": f"decision: {decision}" + (" (report edited)" if response.get("edited_report") else "")}]}
