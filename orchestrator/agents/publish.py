import csv
import json
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent.parent / "outputs"


def publish(state):
    """Write the approved report, the updated RAID log, and the audit trail."""
    week = state["week"].replace(" ", "").lower()
    folder = OUT / week
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "status_report.md").write_text(state["final_report"], encoding="utf-8")

    rows = list(state["raid_log"])
    counters = {}
    prefix = {"Risk": "R", "Assumption": "A", "Issue": "I", "Dependency": "D", "Value Risk": "V"}
    for it in state["new_raid_items"]:
        p = prefix.get(it.get("type"), "X")
        counters[p] = counters.get(p, 0) + 1
        rows.append({"id": f"{p}-{week.upper()}-{counters[p]:02d}", "type": it.get("type"),
                     "description": it.get("description"), "owner": it.get("suggested_owner"),
                     "impact": it.get("impact"), "response": it.get("suggested_response"),
                     "due": "", "status": "Open (pending owner confirmation)",
                     "source": it.get("evidence", "")})
    with open(folder / "raid_log.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "type", "description", "owner", "impact", "response", "due", "status", "source"],
                           restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    (folder / "budget_metrics.json").write_text(json.dumps(state["budget_metrics"], indent=2), encoding="utf-8")
    audit = state["audit"] + [{"step": "publish", "at": datetime.now().isoformat(timespec="seconds"),
                               "detail": f"wrote {folder.name}/status_report.md, raid_log.csv, budget_metrics.json"}]
    (folder / "audit_log.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return {"audit": [audit[-1]]}
