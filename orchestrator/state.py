import operator
from typing import Annotated, TypedDict


class ProgramState(TypedDict, total=False):
    week: str
    data_dir: str
    # collected inputs
    workstream_updates: dict      # workstream name -> update text
    transcript: str
    budget_rows: list             # rows from budget.csv
    raid_log: list                # existing RAID rows
    # agent outputs
    new_raid_items: list
    budget_metrics: dict
    draft: str
    validation: dict
    attempts: int
    # human gate
    decision: str                 # approve | edit | reject
    final_report: str
    # audit trail: parallel agents both append, so entries are merged, not overwritten
    audit: Annotated[list, operator.add]
