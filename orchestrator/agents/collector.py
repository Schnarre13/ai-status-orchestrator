import csv
from datetime import datetime
from pathlib import Path


def collect(state):
    """Gather every input the other agents need. Plain code: no AI here."""
    folder = Path(state["data_dir"])
    updates = {}
    for f in sorted(folder.glob("ws_*.md")):
        text = f.read_text(encoding="utf-8")
        name = text.splitlines()[0].lstrip("# ").split(" - ")[0].strip()
        updates[name] = text

    with open(folder / "budget.csv", newline="", encoding="utf-8") as fh:
        budget = list(csv.DictReader(fh))
    with open(folder / "raid_log.csv", newline="", encoding="utf-8") as fh:
        raid = list(csv.DictReader(fh))

    transcript = (folder / "meeting_transcript.txt").read_text(encoding="utf-8")
    return {
        "workstream_updates": updates,
        "transcript": transcript,
        "budget_rows": budget,
        "raid_log": raid,
        "attempts": 0,
        "audit": [{"step": "collect", "at": datetime.now().isoformat(timespec="seconds"),
                   "detail": f"{len(updates)} workstream updates, {len(budget)} budget rows, {len(raid)} existing RAID items"}],
    }
