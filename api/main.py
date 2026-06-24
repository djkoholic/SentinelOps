from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

import uvicorn
import asyncio
import threading
import uuid
import json

from backend.investigator import Investigator

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


# ============================================================
# Investigation State
# ============================================================

investigations = {}
investigations_lock = threading.Lock()


def create_event_callback(investigation_id):
    def push_event(event):
        with investigations_lock:
            if investigation_id in investigations:
                investigations[investigation_id]["events"].append(event)

    return push_event


# ============================================================
# Investigation Runner
# ============================================================

def run_investigation(investigation_id, query):
    try:
        callback = create_event_callback(investigation_id)

        investigator = Investigator(
            query=query,
            event_callback=callback,
        )

        result = investigator.investigate()

        with investigations_lock:
            investigations[investigation_id]["result"] = result
            investigations[investigation_id]["status"] = "completed"

    except Exception as e:
        with investigations_lock:
            investigations[investigation_id]["status"] = "error"
            investigations[investigation_id]["error"] = str(e)


# ============================================================
# API
# ============================================================

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

    return {
        "status": "started",
        "investigation_id": investigation_id,
    }


@app.get("/stream/{investigation_id}")
async def stream(investigation_id: str):

    async def event_generator():

        last_index = 0

        while True:

            with investigations_lock:
                investigation = investigations.get(investigation_id)

            if investigation is None:
                break

            # Send newly generated events
            while last_index < len(investigation["events"]):

                yield {
                    "data": json.dumps(
                        investigation["events"][last_index]
                    )
                }

                last_index += 1

            # Investigation completed
            if investigation["status"] == "completed":

                yield {
                    "data": json.dumps(
                        {
                            "type": "complete",
                            "result": investigation["result"],
                        }
                    )
                }

                with investigations_lock:
                    investigations.pop(investigation_id, None)

                break

            # Investigation failed
            if investigation["status"] == "error":

                yield {
                    "data": json.dumps(
                        {
                            "type": "error",
                            "error": investigation["error"],
                        }
                    )
                }

                with investigations_lock:
                    investigations.pop(investigation_id, None)

                break

            await asyncio.sleep(0.25)

    return EventSourceResponse(event_generator())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)