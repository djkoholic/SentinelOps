# api/main.py
from fastapi import FastAPI, Form
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

from backend.agents import parse_time_range, run_investigator
from backend.data_collector import collect_data

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

@app.post("/investigate")
async def investigate(request: InvestigationRequest):
    try:
        # Parse the query to extract time range
        start_time, end_time = parse_time_range(request.query)
        print(f"[DEBUG] Parsed time range - Start: {start_time}, End: {end_time}")

        # Collect data based on the parsed time range
        all_data = collect_data(start_time, end_time)
        print(f"[DEBUG] Collected data - Requests: {len(all_data['requests'])}, Logs: {len(all_data['application_logs'])}, Metrics: {len(all_data['request_metrics'])}")

        # Run the investigation
        answer = run_investigator(request.query, all_data)
        print("[DEBUG] Investigation complete")

        return {
            "status": "completed",
            "result": answer
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)