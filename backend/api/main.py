from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

import uvicorn
import asyncio
import threading
import uuid
import json

from backend.agent.graph import investigator
from backend.agent.utils import _load_markdown

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InvestigationRequest(BaseModel):
    query: str

OPERATIONAL_MEMORY_PATH = "/home/djkoholic/Projects/SentinelOps/MovieVerse/docs/Company Operational Memory.md"

investigations = {}
investigations_lock = threading.Lock()


def push_event(investigation_id, event):
    with investigations_lock:
        if investigation_id in investigations:
            investigations[investigation_id]["events"].append(event)


def node_update_to_events(node_name: str, update: dict) -> list[dict]:
    """
    Translates a LangGraph node's partial state update into the
    {type, message} event shape the frontend already expects — same
    contract as the old Investigator.emit(), just driven by the graph's
    own execution instead of manual emit() calls in node code.
    """
    events = []

    if node_name == "time_range_parser":
        events.append({
            "type": "status",
            "message": f"Investigating activity between {update.get('start_time')} and {update.get('end_time')}",
        })

    elif node_name == "planner":
        belief_state = update.get("belief_state")
        if belief_state:
            events.append({
                "type": "hypothesis",
                "message": f"Current hypothesis: {belief_state.selected_hypothesis}",
            })
            events.append({
                "type": "hypothesis",
                "message": belief_state.planner_reasoning,
            })

    elif node_name == "evidence_gatherer":
        past_actions = update.get("past_actions") or []
        findings = update.get("findings") or []
        if past_actions:
            action = past_actions[-1]
            events.append({
                "type": "action",
                "message": f"Collecting data using {action['tool']}({action.get('args') or {}})",
            })
        if findings:
            events.append({
                "type": "finding",
                "message": findings[-1],
            })

    elif node_name == "evidence_assessor":
        conclusion = update.get("conclusion")
        if conclusion:
            status = "Conclusive" if conclusion.conclusive else "Not yet conclusive"
            events.append({
                "type": "analysis",
                "message": f"{status}: {conclusion.root_cause}",
            })

    elif node_name == "generate_report":
        events.append({
            "type": "status",
            "message": "Generating investigation report...",
        })

    return events


def run_investigation(investigation_id, query):
    try:
        operational_memory = _load_markdown(OPERATIONAL_MEMORY_PATH)

        initial_state = {
            "query": query,
            "operational_memory": operational_memory,
            "hypothesis_history": [],
            "past_actions": [],
            "evidence_log": [],
            "findings": [],
            "iteration_count": 0,
            "max_iterations": 10,
            "max_actions": 10,
        }

        push_event(investigation_id, {"type": "status", "message": "Understanding investigation scope..."})

        final_state = None
        for mode, payload in investigator.stream(initial_state, stream_mode=["updates", "values"]):
            if mode == "updates":
                for node_name, update in payload.items():
                    for event in node_update_to_events(node_name, update):
                        push_event(investigation_id, event)
            elif mode == "values":
                final_state = payload  # last one received is the final full state

        final_report = final_state.get("final_report") if final_state else None

        with investigations_lock:
            investigations[investigation_id]["result"] = final_report.model_dump() if final_report else None
            investigations[investigation_id]["status"] = "completed"

    except Exception as e:
        with investigations_lock:
            investigations[investigation_id]["status"] = "error"
            investigations[investigation_id]["error"] = str(e)


@app.post("/investigate")
async def investigate(request: InvestigationRequest):
    investigation_id = str(uuid.uuid4())

    with investigations_lock:
        investigations[investigation_id] = {
            "events": [],
            "status": "running",
            "result": None,
            "error": None,
        }

    thread = threading.Thread(
        target=run_investigation,
        args=(investigation_id, request.query),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "investigation_id": investigation_id}


@app.get("/stream/{investigation_id}")
async def stream(investigation_id: str):
    async def event_generator():
        last_index = 0
        while True:
            with investigations_lock:
                investigation = investigations.get(investigation_id)

            if investigation is None:
                break

            while last_index < len(investigation["events"]):
                yield {"data": json.dumps(investigation["events"][last_index])}
                last_index += 1

            if investigation["status"] == "completed":
                yield {"data": json.dumps({"type": "complete", "result": investigation["result"]})}
                with investigations_lock:
                    investigations.pop(investigation_id, None)
                break

            if investigation["status"] == "error":
                yield {"data": json.dumps({"type": "error", "error": investigation["error"]})}
                with investigations_lock:
                    investigations.pop(investigation_id, None)
                break

            await asyncio.sleep(0.25)

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)