from datetime import datetime
import json

from backend.agent.tools import build_tools
from backend.agent.llms import llm, time_range_llm, planner_llm, evidence_summary_llm, evidence_assessor_llm, report_llm
from backend.agent.schemas import BeliefState, InvestigatorState, Conclusion, InvestigationReport
from backend.agent.prompts import TIME_RANGE_PROMPT, PLANNER_PROMPT, EVIDENCE_GATHERER_PROMPT, EVIDENCE_SUMMARY_PROMPT, EVIDENCE_ASSESSOR_PROMPT, REPORT_PROMPT
from backend.agent.utils import _refine_summarize

CHUNK_THRESHOLD = 50

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
def _format_past_actions(past_actions: list[dict]) -> str:
    if not past_actions:
        return "No actions taken yet"
    lines = []
    for pa in past_actions:
        args = pa.get("args") or {}
        args_str = ", ".join(f"{k}={v}" for k, v in args.items()) or "no filters"
        lines.append(f"- {pa['tool']}({args_str})")
    return "\n".join(lines)


def route_after_assessment(state: InvestigatorState) -> str:
    print("Inside route_after_assessment...")
    conclusion = state.get("conclusion")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 6)
    past_actions = state.get("past_actions", [])
    max_actions = state.get("max_actions", 8)

    MIN_ACTIONS_BEFORE_CONCLUSIVE = 2

    print(f"Conclusive: {conclusion.conclusive if conclusion else None}")
    print(f"Fix specific: {conclusion.fix_is_specific if conclusion else None}")
    print(f"Iteration count: {iteration_count}/{max_iterations}")
    print(f"Actions taken: {len(past_actions)}/{max_actions}")

    if conclusion and conclusion.conclusive and len(past_actions) < MIN_ACTIONS_BEFORE_CONCLUSIVE:
        print(f"LLM marked conclusive but only {len(past_actions)} action(s) taken — overriding, continuing investigation")
        return "planner"

    if conclusion and conclusion.conclusive and not conclusion.fix_is_specific:
        print("LLM marked conclusive but fix is not specific — overriding, continuing investigation")
        return "planner"

    if conclusion and conclusion.conclusive:
        print("Routing to generate_report (conclusive)")
        return "generate_report"
    if iteration_count >= max_iterations:
        print("Routing to generate_report (max iterations reached)")
        return "generate_report"
    if len(past_actions) >= max_actions:
        print("Routing to generate_report (max actions reached)")
        return "generate_report"

    print("Routing to planner (continuing investigation)")
    return "planner"


def evidence_gatherer(state: InvestigatorState) -> dict:
    """
    This node gathers evidence based on the current belief state and the available tools.
    Tools can now be called multiple times with different args — duplicates (same tool,
    same exact args) are detected and skipped rather than re-invoked.
    """
    print("Inside evidence_gatherer node...")
    all_tools = build_tools(state["start_time"], state["end_time"])
    past_actions = state.get("past_actions", [])

    already_called = {
        (pa["tool"], tuple(sorted((pa.get("args") or {}).items())))
        for pa in past_actions
    }

    action_llm = llm.bind_tools(all_tools, tool_choice="any")

    messages = EVIDENCE_GATHERER_PROMPT.invoke({
        "belief_state": state.get("belief_state") or "No belief state yet",
        "findings": state.get("findings") or "No evidence yet",
        "past_actions": _format_past_actions(past_actions),
    })
    print("Calling LLM to select a tool...")
    response = action_llm.invoke(messages)
    print("LLM Response Received...")

    tool_call = response.tool_calls[0]
    chosen_tool = next(t for t in all_tools if t.name == tool_call["name"])
    call_args = tool_call["args"]
    print(f"Chosen tool: {chosen_tool.name}, args: {call_args}")

    call_key = (chosen_tool.name, tuple(sorted(call_args.items())))
    if call_key in already_called:
        print("Exact same tool+args already used — skipping duplicate call")
        return {
            "past_actions": [{"tool": chosen_tool.name, "args": call_args}],
            "findings": [f"Duplicate action skipped: {chosen_tool.name}({call_args}) was already checked. No new evidence gained."],
        }

    print("Invoking tool...")
    try:
        raw_evidence = chosen_tool.invoke(call_args)
    except Exception as e:
        print(f"Tool call failed with args {call_args}: {e}")
        print("Retrying with no filters...")
        raw_evidence = chosen_tool.invoke({})
        call_args = {}

    print(f"Raw evidence retrieved: {len(raw_evidence)} records")

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

    print("Returning from evidence_gatherer node...")
    return {
        "past_actions": [{"tool": chosen_tool.name, "args": call_args}],
        "evidence_log": [{"tool": chosen_tool.name, "args": call_args, "records": raw_evidence}],
        "findings": [summary_text],
    }

def evidence_assessor(state: InvestigatorState) -> dict:
    print("Inside evidence_assessor node...")
    past_actions = state.get("past_actions", [])
    messages = EVIDENCE_ASSESSOR_PROMPT.invoke({
        "operational_memory": state.get("operational_memory", "No operational memory provided"),
        "query": state["query"],
        "belief_state": state.get("belief_state") or "No belief state yet",
        "findings": state.get("findings") or "No evidence yet",
        "past_actions": _format_past_actions(past_actions),
        "num_actions": len(past_actions),
        "total_tools": 5,  # informational only now — no longer a hard ceiling
    })
    print("Calling LLM...")
    conclusion: Conclusion = evidence_assessor_llm.invoke(messages)
    print("LLM Response Received...")
    print(f"Conclusive: {conclusion.conclusive}")
    print(f"Root cause: {conclusion.root_cause}")
    print(f"Confidence: {conclusion.confidence}")
    print("Returning from evidence_assessor node...")

    return {
        "conclusion": conclusion,
    }

def generate_report(state: InvestigatorState) -> dict:
    """
    Synthesizes belief_state, hypothesis_history, findings, and the final conclusion
    into a polished investigation report — whether or not the investigation reached
    a conclusive result.
    """
    print("Inside generate_report node...")
    conclusion = state.get("conclusion")

    messages = REPORT_PROMPT.invoke({
        "query": state["query"],
        "hypothesis_history": state.get("hypothesis_history") or "None considered",
        "findings": state.get("findings") or "No evidence gathered",
        "conclusive": conclusion.conclusive if conclusion else False,
        "root_cause": conclusion.root_cause if conclusion else "Unknown — no conclusion reached",
        "recommended_fix": conclusion.recommended_fix if conclusion else "N/A",
        "reasoning": conclusion.reasoning if conclusion else "N/A",
        "remaining_uncertainty": conclusion.remaining_uncertainty if conclusion else "Investigation did not reach an assessment",
    })
    print("Calling LLM to generate report...")
    report: InvestigationReport = report_llm.invoke(messages)
    print("Report status:", report.status)
    print("Root cause:", report.root_cause)
    print("Returning from generate_report node...")

    return {
        "final_report": report,
    }