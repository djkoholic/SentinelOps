from datetime import datetime

from langgraph.types import Send

from backend.agent.tools import build_tools
from backend.agent.llms import llm, time_range_llm, evidence_summary_llm
from backend.agent.schemas import InvestigatorState
from backend.agent.prompts import TIME_RANGE_PROMPT, EXPLORE_START_PROMPT, EXPLORE_MID_LOOP_PROMPT, EVIDENCE_SUMMARY_PROMPT, EVIDENCE_REFINE_PROMPT
from backend.agent.utils import _format_evidence_chain, _format_past_actions, _refine_summarize

CHUNK_THRESHOLD = 50
MAX_FANOUT_TARGETS = 3

def time_range_parser(state: InvestigatorState) -> dict:
    """
    Unchanged from v0.2. Parses the time range from the query using the LLM
    and returns the start and end times as datetime objects.
    """
    print("Inside time_range_parser node...")
    messages = TIME_RANGE_PROMPT.invoke({
        "query": state["query"]
    })
    print("Calling LLM...")
    response = time_range_llm.invoke(messages)
    print("LLM Response Received...")

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
    print("Returning from time_range_parser node...")
    return {
        "start_time": start_dt,
        "end_time": end_dt,
    }


def explore_start(state: InvestigatorState) -> dict:
    """
    Round-1 exploration. No evidence_chain exists yet, so there is no
    current_question to chase. Defaults to broad, cheap orienting checks
    instead of a targeted lookup — the investigative equivalent of
    surveying the scene before pulling on any specific thread.

    Unlike later rounds (explore_mid_loop, not yet implemented), this node
    does not read evidence_chain at all — it only has the raw query and
    operational memory to go on.
    """
    print("Inside explore_start node...")
    all_tools = build_tools(state["start_time"], state["end_time"])

    explore_llm = llm.bind_tools(all_tools, tool_choice="any")

    messages = EXPLORE_START_PROMPT.invoke({
        "operational_memory": state.get("operational_memory", "No operational memory provided"),
        "query": state["query"],
    })
    print("Calling LLM to select initial orientation targets...")
    response = explore_llm.invoke(messages)
    print("LLM Response Received...")

    tool_calls = response.tool_calls[:MAX_FANOUT_TARGETS]
    explore_targets = [
        {"tool": tc["name"], "args": tc["args"]}
        for tc in tool_calls
    ]

    print(f"Selected {len(explore_targets)} orientation target(s):")
    for t in explore_targets:
        print(f"  - {t['tool']}({t['args']})")

    print("Returning from explore_start node...")
    return {
        "explore_targets": explore_targets,
    }

def explore_mid_loop(state: InvestigatorState) -> dict:
    """
    Subsequent-round exploration. Chases state["current_question"] — the
    single open "why" raised by the most recent integrate step — rather
    than reasoning about any hypothesis. Unlike explore_start, this node
    has the full evidence_chain and past_actions to work from.
    """
    print("Inside explore_mid_loop node...")
    all_tools = build_tools(state["start_time"], state["end_time"])

    explore_llm = llm.bind_tools(all_tools, tool_choice="any")

    messages = EXPLORE_MID_LOOP_PROMPT.invoke({
        "operational_memory": state.get("operational_memory", "No operational memory provided"),
        "query": state["query"],
        "evidence_chain": _format_evidence_chain(state.get("evidence_chain", [])),
        "current_question": state.get("current_question") or "No specific question yet",
        "past_actions": _format_past_actions(state.get("past_actions", [])),
    })
    print(f"Current question being chased: {state.get('current_question')}")
    print("Calling LLM to select targets...")
    response = explore_llm.invoke(messages)
    print("LLM Response Received...")

    tool_calls = response.tool_calls[:MAX_FANOUT_TARGETS]
    explore_targets = [
        {"tool": tc["name"], "args": tc["args"]}
        for tc in tool_calls
    ]

    print(f"Selected {len(explore_targets)} target(s):")
    for t in explore_targets:
        print(f"  - {t['tool']}({t['args']})")

    print("Returning from explore_mid_loop node...")
    return {
        "explore_targets": explore_targets,
    }

def _already_called(past_actions: list[dict]) -> set[tuple]:
    """Set of (tool, sorted-args-tuple) pairs already executed — used to
    filter out exact duplicates before they're even sent to gather."""
    return {
        (pa["tool"], tuple(sorted((pa.get("args") or {}).items())))
        for pa in past_actions
    }


def fan_out_to_gather(state: InvestigatorState) -> list[Send]:
    """
    Takes the targets selected by explore_start or explore_mid_loop, drops
    any that exactly duplicate a past action, and dispatches them as ONE
    Send carrying the full target list — gather executes them sequentially
    inside a single node run rather than as true concurrent branches. This
    is a deliberate hardware-driven choice: the local Ollama instance
    cannot safely serve multiple simultaneous inference calls (see the
    OOM/memory investigation in prior iterations). The targets remain
    logically parallel — none depends on another's result, all answer the
    same current_question together — they are just executed one at a time.
    """
    targets = state.get("explore_targets", [])
    already_called = _already_called(state.get("past_actions", []))

    deduped_targets = []
    for t in targets:
        key = (t["tool"], tuple(sorted((t.get("args") or {}).items())))
        if key in already_called:
            print(f"Skipping duplicate target: {t['tool']}({t['args']}) — already checked")
            continue
        deduped_targets.append(t)

    print(f"Fanning out to gather with {len(deduped_targets)} target(s) (sequential execution):")
    for t in deduped_targets:
        print(f"  - {t['tool']}({t['args']})")

    if not deduped_targets:
        print("No new targets after deduplication — dispatching empty batch")

    return [Send("gather", {**state, "targets": deduped_targets})]


def gather(state: InvestigatorState) -> dict:
    """
    Executes the targets assigned by fan_out_to_gather, sequentially (see
    fan_out_to_gather for why these are logically-parallel-but-sequential).

    Does NOT decide raised_question or is_actionable_cause — that requires
    seeing the whole evidence_chain for context, which a single gather
    round doesn't have reason to reason about. gather's job is strictly
    execution + summarization. Draft results are handed to `integrate`
    via gathered_evidence, which is responsible for turning them into
    real EvidenceStep entries.
    """
    print("Inside gather node...")
    all_tools = build_tools(state["start_time"], state["end_time"])
    tools_by_name = {t.name: t for t in all_tools}

    targets = state.get("targets", [])
    print(f"Executing {len(targets)} target(s) sequentially...")

    new_past_actions = []
    new_evidence_log = []
    gathered_evidence = []

    for target in targets:
        tool_name = target["tool"]
        call_args = target.get("args") or {}
        chosen_tool = tools_by_name.get(tool_name)

        if chosen_tool is None:
            print(f"Unknown tool '{tool_name}' — skipping")
            continue

        print(f"Invoking {tool_name}({call_args})...")
        try:
            raw_evidence = chosen_tool.invoke(call_args)
        except Exception as e:
            print(f"Tool call failed with args {call_args}: {e}")
            print("Retrying with no filters...")
            raw_evidence = chosen_tool.invoke({})
            call_args = {}

        print(f"Raw evidence retrieved: {len(raw_evidence)} records")

        if len(raw_evidence) > CHUNK_THRESHOLD:
            print(f"Evidence exceeds chunk threshold, using refine summarization...")
            summary_text = _refine_summarize(
                tool_name=tool_name,
                raw_evidence=raw_evidence,
                chunk_size=CHUNK_THRESHOLD,
            )
        else:
            print("Evidence within chunk threshold, using single-pass summarization...")
            summary_messages = EVIDENCE_SUMMARY_PROMPT.invoke({
                "tool_name": tool_name,
                "evidence": json.dumps(raw_evidence, default=str),
            })
            summary_text = evidence_summary_llm.invoke(summary_messages).summary

        source_action = {"tool": tool_name, "args": call_args}

        new_past_actions.append(source_action)
        new_evidence_log.append({"tool": tool_name, "args": call_args, "records": raw_evidence})
        gathered_evidence.append({
            "summary": summary_text,
            "source_action": source_action,
        })

    print(f"Gathered {len(gathered_evidence)} new observation(s) this round")
    print("Returning from gather node...")

    return {
        "past_actions": new_past_actions,
        "evidence_log": new_evidence_log,
        "gathered_evidence": gathered_evidence,
    }