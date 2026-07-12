from datetime import datetime
from typing import Annotated, Literal, TypedDict
from operator import add

from pydantic import BaseModel, Field


# ---------- Structured LLM outputs ----------

class TimeRange(BaseModel):
    start_time: str = Field(description="Start time in HH:MM:SS format")
    end_time: str = Field(description="End time in HH:MM:SS format")


class Hypothesis(BaseModel):
    hypothesis: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    status: Literal["active", "ruled_out", "proven"] = "active"


class BeliefState(BaseModel):
    belief_state: list[Hypothesis]
    selected_hypothesis: str
    planner_reasoning: str
    investigation_status: Literal["investigating", "ready_for_conclusion"]

# ---------- Graph state ----------

class InvestigatorState(TypedDict, total=False):
    # static: set once
    query: str
    operational_memory: dict
    start_time: datetime
    end_time: datetime

    # dynamic: overwritten in full each planner run
    belief_state: BeliefState

    # accumulating: `add` reducer appends instead of replacing
    hypothesis_history: Annotated[list[Hypothesis], add]
    past_actions: Annotated[list[str], add]
    evidence_log: Annotated[list[dict], add]
    findings: Annotated[list[str], add]

    # loop control
    available_actions: list[str]
    iteration_count: int
    max_iterations: int

    # output
    final_report: str