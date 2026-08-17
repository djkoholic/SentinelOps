from datetime import datetime
from typing import Annotated, Literal, TypedDict
from operator import add

from pydantic import BaseModel, Field


# ---------- Structured LLM outputs ----------

class TimeRange(BaseModel):
    start_time: str = Field(description="Start time in HH:MM:SS format")
    end_time: str = Field(description="End time in HH:MM:SS format")


class EvidenceSummary(BaseModel):
    summary: str = Field(description="A concise summary of what this evidence shows or fails to show")
    supports_hypothesis: bool = Field(description="Deprecated field, retained for prompt compatibility during migration")


class EvidenceStep(BaseModel):
    """One link in the evidence-first causal chain. Written by `integrate`."""
    observation: str = Field(description="What this evidence shows, in plain terms")
    raised_question: str = Field(description="The next 'why' this observation prompts. Empty string if is_actionable_cause=True and the chain terminates here")
    is_actionable_cause: bool = Field(description="True if this observation is a change/event a human could act on (a deploy, a config change, a traffic source) rather than a system state (latency, CPU, error rate) that itself still needs explaining")
    source_action: dict = Field(description="{'tool': str, 'args': dict} — which tool call produced this observation")


class Conclusion(BaseModel):
    conclusive: bool = Field(description="True only if an actionable-cause step exists in the chain AND it is corroborated by the rest of the chain")
    root_cause: str = Field(description="Best current explanation of what happened, even if not yet conclusive")
    recommended_fix: str = Field(description="A specific, actionable remediation tied to the actionable-cause step. Must NOT be a generic mitigation like 'scale up the service'")
    fix_is_specific: bool = Field(description="True only if recommended_fix targets the specific actionable cause found in the chain")
    reasoning: str = Field(description="Why the chain does or doesn't support a conclusive, corroborated answer")
    confidence: float = Field(ge=0.0, le=1.0)
    remaining_uncertainty: str = Field(description="What is still unexplained. Empty string if conclusive.")


class InvestigationReport(BaseModel):
    summary: str = Field(description="A concise narrative summary of the incident and what the investigation found")
    root_cause: str = Field(description="The identified or best-current-understanding root cause")
    recommended_fix: str = Field(description="Concrete action(s) to mitigate or resolve the issue")
    status: Literal["conclusive", "inconclusive"]
    caveats: str = Field(description="What remains uncertain or unverified. Empty string if fully conclusive.")

# ---------- Graph state ----------

class InvestigatorState(TypedDict, total=False):
    # static: set once
    query: str
    operational_memory: dict
    start_time: datetime
    end_time: datetime

    # exploration control — overwritten each round, not accumulated
    explore_targets: list[dict]     # [{"tool": str, "args": dict}, ...] — set by explore, consumed by fan-out
    current_question: str           # the single open "why" being pursued — "" on round 1
    # transient: this round's raw gather results, consumed and cleared by
    # integrate each round — NOT an accumulating reducer field, since it
    # only needs to live for one round
    gathered_evidence: list[dict]
    # the causal chain itself — the primary reasoning artifact
    evidence_chain: Annotated[list[EvidenceStep], add]

    # bookkeeping, same reducers as before
    past_actions: Annotated[list[dict], add]
    evidence_log: Annotated[list[dict], add]
    # dynamic: overwritten in full when set
    conclusion: Conclusion

    # loop control
    iteration_count: int
    max_iterations: int
    max_actions: int

    # output
    final_report: InvestigationReport
    