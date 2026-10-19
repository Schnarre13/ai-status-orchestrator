"""
Guardrail and workflow tests. They run without an API key: the model is replaced
by a stub so the tests check the orchestration and the controls, not the model.

    pip install pytest
    python -m pytest -v
"""
import json
from pathlib import Path

import pytest
from langgraph.types import Command

from orchestrator import llm
from orchestrator.agents import publish as publish_mod
from orchestrator.agents.budget import analyze_budget
from orchestrator.agents.collector import collect
from orchestrator.agents.raid_agent import extract_raid
from orchestrator.agents.validator import validate
from orchestrator.graph import build

DATA = Path(__file__).resolve().parent.parent / "sample_data" / "week21"
REAL_QUOTE = "Use case 3 is stuck. Without the evaluation data we can't run the pilot"


def inputs():
    s = {"data_dir": str(DATA), "week": "Week 21"}
    s.update(collect(s))
    return s


def good_draft(state):
    m = state["budget_metrics"]["program"]
    ws = "\n".join(f"- {n}: update" for n in state["workstream_updates"])
    return (f"## Overall\nAmber. CPI {m['cpi']}, SPI {m['spi']}.\n"
            f"## Decisions needed this week\n1. Resequence use case 4 ahead of use case 3.\n"
            f"## Workstreams\n{ws}\n## Top risks\n1. Evaluation data.\n## Budget\nEAC ${m['eac_m']}M.\n")


# ---- Budget: earned value is computed in code, not by the model ----
def test_budget_metrics_are_computed_in_code():
    s = inputs()
    m = analyze_budget(s)["budget_metrics"]
    assert m["program"]["cpi"] == 0.86      # EV 1.80 / AC 2.10
    assert m["program"]["spi"] == 0.9       # EV 1.80 / PV 2.00
    assert m["program"]["eac_m"] == 5.6     # BAC 4.80 / CPI
    assert set(m["flagged"]) == {"AI Use Case Delivery", "Governance & Risk"}


# ---- RAID agent: items without a real quote from the sources are dropped ----
def test_raid_agent_drops_items_with_invented_evidence(monkeypatch):
    fake = [{"type": "Risk", "description": "Eval data late", "evidence": REAL_QUOTE},
            {"type": "Issue", "description": "Vendor walked away", "evidence": "The vendor has terminated the contract."}]
    monkeypatch.setattr(llm, "ask", lambda *a, **k: json.dumps(fake))
    out = extract_raid(inputs())
    assert [i["description"] for i in out["new_raid_items"]] == ["Eval data late"]
    assert "1 dropped" in out["audit"][0]["detail"]


# ---- Validator: catches invented numbers, missing sections, missing workstreams ----
def test_validator_passes_a_grounded_draft():
    s = inputs()
    s.update(analyze_budget(s), new_raid_items=[])
    s["draft"] = good_draft(s)
    assert validate(s)["validation"] == {"passed": True, "findings": []}


def test_validator_catches_invented_number_and_missing_workstream():
    s = inputs()
    s.update(analyze_budget(s), new_raid_items=[])
    s["draft"] = good_draft(s).replace("CPI 0.86", "CPI 0.97").replace("- Governance & Risk: update\n", "")
    findings = validate(s)["validation"]["findings"]
    assert "Number not found in any source: 0.97" in findings
    assert "Workstream not covered: Governance & Risk" in findings


def test_validator_catches_missing_section():
    s = inputs()
    s.update(analyze_budget(s), new_raid_items=[])
    s["draft"] = good_draft(s).replace("## Decisions needed this week", "## Notes")
    assert "Missing required section: ## Decisions needed this week" in validate(s)["validation"]["findings"]


# ---- Full workflow: redraft loop, human gate, publish ----
@pytest.fixture
def stub_model(monkeypatch, tmp_path):
    """First status draft invents a number; the redraft fixes it."""
    calls = {"status": 0}
    state_box = {}

    def fake_ask(system, user, **k):
        if system == llm.prompt("raid_agent"):
            return json.dumps([{"type": "Value Risk", "description": "No baseline for use case 3",
                                "evidence": REAL_QUOTE, "suggested_owner": "Priya"}])
        calls["status"] += 1
        draft = good_draft(state_box["s"])
        return draft.replace("CPI 0.86", "CPI 0.97") if calls["status"] == 1 else draft

    s = inputs()
    s.update(analyze_budget(s))
    state_box["s"] = s
    monkeypatch.setattr(llm, "ask", fake_ask)
    monkeypatch.setattr(publish_mod, "OUT", tmp_path)
    return calls, tmp_path


def run_to_gate():
    graph = build()
    cfg = {"configurable": {"thread_id": "test"}}
    result = graph.invoke({"week": "Week 21", "data_dir": str(DATA)}, cfg)
    return graph, cfg, result


def test_workflow_redrafts_then_pauses_for_a_person(stub_model):
    calls, out = stub_model
    graph, cfg, result = run_to_gate()
    assert "__interrupt__" in result                      # paused at the human gate
    assert calls["status"] == 2                           # validator sent draft 1 back
    assert result["__interrupt__"][0].value["validation"]["passed"]
    assert not any(out.iterdir())                         # nothing published without approval


def test_approval_publishes_report_raid_log_and_audit_trail(stub_model):
    calls, out = stub_model
    graph, cfg, _ = run_to_gate()
    final = graph.invoke(Command(resume={"decision": "approve"}), cfg)
    files = sorted(p.name for p in (out / "week21").iterdir())
    assert files == ["audit_log.json", "budget_metrics.json", "raid_log.csv", "status_report.md"]
    steps = [a["step"] for a in final["audit"]]
    assert steps.count("status_agent") == 2 and steps[-2:] == ["human_review", "publish"]
    raid = (out / "week21" / "raid_log.csv").read_text()
    assert "V-WEEK21-01" in raid
    assert REAL_QUOTE in raid                             # each new item keeps the quote it came from


def test_rejection_publishes_nothing(stub_model):
    calls, out = stub_model
    graph, cfg, _ = run_to_gate()
    final = graph.invoke(Command(resume={"decision": "reject"}), cfg)
    assert final["audit"][-1]["detail"] == "decision: reject"
    assert not any(out.iterdir())
