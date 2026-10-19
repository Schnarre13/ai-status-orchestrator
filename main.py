"""
AI Status Orchestrator: turns a week of raw program inputs into an approved status report.

Usage:
    python main.py                 # runs the sample program, week 21
    python main.py --data sample_data/week21 --week "Week 21"
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from langgraph.types import Command
from orchestrator.graph import build

BASE = Path(__file__).resolve().parent


def show(title, text=""):
    print("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70)
    if text:
        print(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(BASE / "sample_data" / "week21"))
    ap.add_argument("--week", default="Week 21")
    args = ap.parse_args()

    graph = build()
    config = {"configurable": {"thread_id": args.week}}
    result = graph.invoke({"week": args.week, "data_dir": args.data}, config)

    # The graph pauses at the human gate. Show the reviewer what they need to decide.
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        v = payload["validation"]
        show("NEW RAID ITEMS PROPOSED", "\n".join(
            f"- [{i['type']}] {i['description']}  (owner: {i.get('suggested_owner','?')})" for i in payload["new_raid_items"]) or "None")
        show("VALIDATOR", "PASSED" if v["passed"] else "FINDINGS:\n" + "\n".join(f"- {f}" for f in v["findings"]))
        show("DRAFT STATUS REPORT", payload["draft"])

        review_file = BASE / "outputs" / f"draft_for_review_{args.week.replace(' ', '').lower()}.md"
        review_file.parent.mkdir(exist_ok=True)
        review_file.write_text(payload["draft"], encoding="utf-8")
        print(f"\nThe draft is also saved at: {review_file}")
        choice = input("\nApprove as is [a], edit the file then approve [e], or reject [r]? ").strip().lower()

        if choice == "e":
            input(f"Edit {review_file.name}, save it, then press Enter to continue... ")
            resume = {"decision": "edit", "edited_report": review_file.read_text(encoding="utf-8")}
        elif choice == "a":
            resume = {"decision": "approve"}
        else:
            resume = {"decision": "reject"}
        result = graph.invoke(Command(resume=resume), config)

    show("AUDIT TRAIL", "\n".join(f"{a['at']}  {a['step']:<14} {a['detail']}" for a in result.get("audit", [])))
    if result.get("decision") in ("approve", "edit"):
        print(f"\nPublished to outputs/{args.week.replace(' ', '').lower()}/")
    else:
        print("\nRejected. Nothing was published.")


if __name__ == "__main__":
    main()
