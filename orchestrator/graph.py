from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from orchestrator.state import ProgramState
from orchestrator.agents.collector import collect
from orchestrator.agents.budget import analyze_budget
from orchestrator.agents.raid_agent import extract_raid
from orchestrator.agents.status_agent import draft_status
from orchestrator.agents.validator import validate
from orchestrator.agents.human_gate import human_review
from orchestrator.agents.publish import publish

MAX_DRAFTS = 3


def after_validation(state):
    if state["validation"]["passed"] or state["attempts"] >= MAX_DRAFTS:
        return "human_review"
    return "draft_status"


def after_review(state):
    return "publish" if state["decision"] in ("approve", "edit") else END


def build():
    g = StateGraph(ProgramState)
    g.add_node("collect", collect)
    g.add_node("extract_raid", extract_raid)
    g.add_node("analyze_budget", analyze_budget)
    g.add_node("draft_status", draft_status)
    g.add_node("validate", validate)
    g.add_node("human_review", human_review)
    g.add_node("publish", publish)

    g.add_edge(START, "collect")
    g.add_edge("collect", "extract_raid")          # fan out: these two run in parallel
    g.add_edge("collect", "analyze_budget")
    g.add_edge(["extract_raid", "analyze_budget"], "draft_status")   # join: wait for both
    g.add_edge("draft_status", "validate")
    g.add_conditional_edges("validate", after_validation, ["draft_status", "human_review"])
    g.add_conditional_edges("human_review", after_review, ["publish", END])
    g.add_edge("publish", END)
    return g.compile(checkpointer=MemorySaver())
