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

class EvidenceSummary(BaseModel):
    summary: str = Field(description="A concise summary of what this evidence shows or fails to show, relevant to the current hypothesis")
    supports_hypothesis: bool = Field(description="Whether this evidence supports the current hypothesis")

class Conclusion(BaseModel):
    conclusive: bool = Field(description="True only if evidence supports a specific, actionable fix that addresses the actual cause")
    root_cause: str = Field(description="Best current explanation of what happened, even if not yet conclusive")
    recommended_fix: str = Field(description="A specific, actionable remediation. Must name a concrete action tied to a specific cause found in evidence — e.g. 'disable the newly enabled retry-on-timeout setting in the auth-service client' — NOT a generic mitigation like 'scale up the service' or 'restart the pods', which could be proposed without knowing the actual cause")
    fix_is_specific: bool = Field(description="True only if recommended_fix targets a specific identified cause (a config change, a specific traffic source, a specific saturated dependency). False if the fix is generic infrastructure scaling/restarting that doesn't require knowing what actually happened")
    reasoning: str = Field(description="Why this evidence is or isn't sufficient, and why the fix is or isn't specific")
    confidence: float = Field(ge=0.0, le=1.0)
    remaining_uncertainty: str = Field(description="What is still unknown. Empty string if conclusive.")

class InvestigationReport(BaseModel):
    summary: str = Field(description="A concise narrative summary of the incident and what the investigation found")
    root_cause: str = Field(description="The identified or best-current-understanding root cause")
    recommended_fix: str = Field(description="Concrete action(s) to mitigate or resolve the issue, based on the root cause identified")
    status: Literal["conclusive", "inconclusive"]
    caveats: str = Field(description="What remains uncertain or unverified. Empty string if fully conclusive.")

# ---------- Graph state ----------

class InvestigatorState(TypedDict, total=False):
    # static: set once
    query: str
    operational_memory: dict
    start_time: datetime
    end_time: datetime

    # dynamic: overwritten in full each planner run
    belief_state: BeliefState
    conclusion: Conclusion

    # accumulating: `add` reducer appends instead of replacing
    hypothesis_history: Annotated[list[Hypothesis], add]
    past_actions: Annotated[list[dict], add]   # now {"tool": str, "args": dict} instead of bare str
    evidence_log: Annotated[list[dict], add]
    findings: Annotated[list[str], add]

    # loop control
    iteration_count: int
    max_iterations: int
    max_actions: int   # NEW — total evidence-gathering calls allowed, since tool+args combos are unbounded

    # output
    final_report: InvestigationReport