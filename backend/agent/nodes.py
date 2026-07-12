from datetime import datetime

from backend.agent.llms import time_range_llm, planner_llm
from backend.agent.schemas import BeliefState, InvestigatorState
from backend.agent.prompts import TIME_RANGE_PROMPT, PLANNER_PROMPT
from backend.agent.utils import load_markdown

def time_range_parser(state: InvestigatorState) -> dict:
    """
    This node parses the time range from the query using the LLM
    and returns the start and end times as datetime objects.
    """
    print("Inside time range parse node...")
    messages = TIME_RANGE_PROMPT.invoke({
        "query": state["query"]
    })
    print("Calling LLM...")
    response = time_range_llm.invoke(messages)
    print("LLM Response Recieved...")

    start_dt = datetime.strptime(
        f"2026-01-01 {response.start_time}",
        "%Y-%m-%d %H:%M:%S",
    )

    end_dt = datetime.strptime(
        f"2026-01-01 {response.end_time}",
        "%Y-%m-%d %H:%M:%S",
    )

    print("Parsed Times")
    print(start_dt)
    print(end_dt)
    print("Returning from time range parse node...")
    return {
        "start_time": start_dt,
        "end_time": end_dt,
    }

def planner(state: InvestigatorState) -> dict:
    """
    This node takes the current state of the investigation and uses the LLM to generate a belief state.
    """
    print("Inside planner node...")
    messages = PLANNER_PROMPT.invoke({
        "operational_memory": state.get("operational_memory", "No operational memory provided"),
        "query": state["query"],
        "belief_state": state.get("belief_state") or "No belief state yet",
        "findings": state.get("findings") or "No evidence yet",
        "conclusions": state.get("final_report") or "No conclusion yet",
        "previous_hypotheses": state.get("hypothesis_history") or "None yet",
    })
    print("Calling LLM...")
    belief_state: BeliefState = planner_llm.invoke(messages)
    print("LLM Response Received...")
    print("Belief State:", belief_state)
    print("Returning from planner node...")
    return {
        "belief_state": belief_state,
        "hypothesis_history": list(belief_state.belief_state),
        "iteration_count": state.get("iteration_count", 0) + 1,
    }