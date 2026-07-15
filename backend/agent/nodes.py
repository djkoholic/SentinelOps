from datetime import datetime
import json

from backend.agent.tools import build_tools
from backend.agent.llms import llm, time_range_llm, planner_llm, evidence_summary_llm, evidence_assessor_llm
from backend.agent.schemas import BeliefState, InvestigatorState, Conclusion
from backend.agent.prompts import TIME_RANGE_PROMPT, PLANNER_PROMPT, EVIDENCE_GATHERER_PROMPT, EVIDENCE_SUMMARY_PROMPT, EVIDENCE_ASSESSOR_PROMPT
from backend.agent.utils import _refine_summarize

CHUNK_THRESHOLD = 50

def route_after_assessment(state: InvestigatorState) -> str:
    print("Inside route_after_assessment...")
    conclusion = state.get("conclusion")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 6)

    # available_actions being empty means every tool has been used at least once
    all_tools = build_tools(state["start_time"], state["end_time"])
    already_used = set(state.get("past_actions", []))
    tools_remaining = len(already_used) < len(all_tools)

    print(f"Conclusive: {conclusion.conclusive if conclusion else None}")
    print(f"Iteration count: {iteration_count}/{max_iterations}")
    print(f"Tools remaining: {tools_remaining} ({len(already_used)}/{len(all_tools)} used)")

    if conclusion and conclusion.conclusive:
        print("Routing to generate_report (conclusive)")
        return "generate_report"
    if iteration_count >= max_iterations:
        print("Routing to generate_report (max iterations reached)")
        return "generate_report"
    if not tools_remaining:
        print("Routing to generate_report (no tools remaining)")
        return "generate_report"

    print("Routing to planner (continuing investigation)")
    return "planner"

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
    print(f"Iteration count so far: {state.get('iteration_count', 0)}")
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
    print("Selected hypothesis:", belief_state.selected_hypothesis)
    print("Belief State:", belief_state)
    print("Returning from planner node...")
    return {
        "belief_state": belief_state,
        "hypothesis_history": list(belief_state.belief_state),
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

def evidence_gatherer(state: InvestigatorState) -> dict:
    """
    This node gathers evidence based on the current belief state and the available tools.
    It uses the LLM to select which tool to use next and summarizes the evidence gathered.
    """
    print("Inside evidence_gatherer node...")
    all_tools = build_tools(state["start_time"], state["end_time"])

    already_used = set(state.get("past_actions", []))
    remaining_tools = [t for t in all_tools if t.name not in already_used]
    print(f"Tools already used: {already_used}")
    print(f"Tools remaining: {[t.name for t in remaining_tools]}")

    # Safety net: the loop's edge logic should stop calling this node once
    # actions run out, but guard here too in case it's ever reached anyway.
    if not remaining_tools:
        print("No remaining tools — returning early")
        return {
            "findings": ["No remaining evidence sources to check."],
        }

    action_llm = llm.bind_tools(remaining_tools, tool_choice="any")

    messages = EVIDENCE_GATHERER_PROMPT.invoke({
        "belief_state": state.get("belief_state") or "No belief state yet",
        "findings": state.get("findings") or "No evidence yet",
    })
    print("Calling LLM to select a tool...")
    response = action_llm.invoke(messages)
    print("LLM Response Received...")

    # tool_choice="any" forces at least one call; we only act on the first
    tool_call = response.tool_calls[0]
    chosen_tool = next(t for t in remaining_tools if t.name == tool_call["name"])
    print(f"Chosen tool: {chosen_tool.name}, args: {tool_call['args']}")

    print("Invoking tool...")
    raw_evidence = chosen_tool.invoke(tool_call["args"])
    print(f"Raw evidence retrieved: {len(raw_evidence)} records")
    print("Calling LLM to summarize evidence...")
    if len(raw_evidence) > CHUNK_THRESHOLD:
        print("Evidence exceeds chunk threshold, using refine summarization...")
        summary_text = _refine_summarize(
            tool_name=chosen_tool.name,
            hypothesis=state.get("belief_state").selected_hypothesis if state.get("belief_state") else "None yet",
            raw_evidence=raw_evidence,
            chunk_size=CHUNK_THRESHOLD,
        )
    else:
        print("Evidence within chunk threshold, using single-pass summarization...")
        summary_messages = EVIDENCE_SUMMARY_PROMPT.invoke({
            "hypothesis": state.get("belief_state").selected_hypothesis if state.get("belief_state") else "None yet",
            "tool_name": chosen_tool.name,
            "evidence": json.dumps(raw_evidence, default=str),
        })
        summary_text = evidence_summary_llm.invoke(summary_messages).summary
    print("Calling LLM to summarize evidence...")
    print("Returning from evidence_gatherer node...")
    return {
        "past_actions": [chosen_tool.name],
        "evidence_log": [{"tool": chosen_tool.name, "records": raw_evidence}],
        "findings": [summary_text],
    }

def evidence_assessor(state: InvestigatorState) -> dict:
    print("Inside evidence_assessor node...")
    all_tools = build_tools(state["start_time"], state["end_time"])
    past_actions = state.get("past_actions", [])

    messages = EVIDENCE_ASSESSOR_PROMPT.invoke({
        "operational_memory": state.get("operational_memory", "No operational memory provided"),
        "query": state["query"],
        "belief_state": state.get("belief_state") or "No belief state yet",
        "findings": state.get("findings") or "No evidence yet",
        "past_actions": past_actions or "No actions taken yet",
        "num_actions": len(past_actions),
        "total_tools": len(all_tools),
    })

def generate_report(state: InvestigatorState) -> dict:
    """
    Placeholder — will synthesize belief_state, conclusion, and findings
    into a final written report. For now just echoes the conclusion.
    """
    print("Inside generate_report node...")
    conclusion = state.get("conclusion")
    print(f"Generating report, conclusion present: {conclusion is not None}")
    print("Returning from generate_report node...")
    return {
        "final_report": f"[DUMMY REPORT] {conclusion.root_cause if conclusion else 'No conclusion reached.'}",
    }