# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import logging
import asyncio
import uuid
import json
from datetime import datetime
import concurrent.futures
import threading

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

# Store ongoing investigations with thread locks for safety
investigations = {}
investigations_lock = threading.Lock()

class LogCapture(logging.Handler):
    """Custom logging handler that stores logs for streaming"""
    def __init__(self, investigation_id):
        super().__init__()
        self.investigation_id = investigation_id

    def emit(self, record):
        try:
            # Only capture INFO and higher level logs
            if record.levelno >= logging.INFO:
                msg = self.format(record)
                # Safely append to investigation logs
                with investigations_lock:
                    if self.investigation_id in investigations:
                        investigations[self.investigation_id]['logs'].append(msg)
        except Exception:
            self.handleError(record)

@app.post("/investigate")
async def investigate(request: InvestigationRequest):
    """Start an investigation and return investigation_id for streaming"""
    investigation_id = str(uuid.uuid4())
    
    # Initialize investigation record
    with investigations_lock:
        investigations[investigation_id] = {
            'logs': [],
            'result': None,
            'status': 'running',
            'error': None,
            'created_at': datetime.now()
        }
    
    # Run investigation in background thread (not async task)
    thread = threading.Thread(
        target=run_investigation_sync,
        args=(investigation_id, request.query),
        daemon=True
    )
    thread.start()
    
    return {
        "investigation_id": investigation_id,
        "status": "started"
    }

def run_investigation_sync(investigation_id, query):
    """Background thread to run investigation (synchronous)"""
    # Set up logging
    log_capture = LogCapture(investigation_id)
    log_capture.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    log_capture.setLevel(logging.INFO)  # Only capture INFO and higher level logs
    
    root_logger = logging.getLogger()
    old_level = root_logger.level
    old_handlers = list(root_logger.handlers)
    
    # Clear and set up handlers
    for handler in old_handlers:
        root_logger.removeHandler(handler)
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(log_capture)
    
    # Configure backend loggers to propagate
    for module_name in ['backend.agents', 'backend.data_collector', 'backend.llm_utils', '__main__']:
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.INFO)
        logger.propagate = True
    
    try:
        logger = logging.getLogger(__name__)
        logger.info("Starting investigation")
        
        # Parse the query to extract time range
        start_time, end_time = parse_time_range(query)
        logger.info(f"Parsed time range - Start: {start_time}, End: {end_time}")

        # Collect data based on the parsed time range
        all_data = collect_data(start_time, end_time)
        logger.info(f"Collected data - Requests: {len(all_data['requests'])}, Logs: {len(all_data['application_logs'])}, Metrics: {len(all_data['request_metrics'])}")

        # Run the investigation
        answer = run_investigator(query, all_data)
        logger.info("Investigation complete")

        with investigations_lock:
            investigations[investigation_id]['result'] = answer
            investigations[investigation_id]['status'] = 'completed'

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Investigation failed: {str(e)}")
        with investigations_lock:
            investigations[investigation_id]['error'] = str(e)
            investigations[investigation_id]['status'] = 'error'
    
    finally:
        # Clean up logging
        root_logger.removeHandler(log_capture)
        root_logger.setLevel(old_level)
        for handler in old_handlers:
            root_logger.addHandler(handler)

@app.get("/stream/{investigation_id}")
async def stream_logs(investigation_id: str):
    """Stream logs for an investigation in real-time"""
    
    with investigations_lock:
        if investigation_id not in investigations:
            return {"error": "Investigation not found"}, 404
    
    async def event_generator():
        """Generator that yields log events"""
        last_log_index = 0
        last_emit_time = 0
        
        while True:
            with investigations_lock:
                investigation = investigations.get(investigation_id)
            
            if investigation is None:
                break
            
            # Stream any new logs
            current_logs = investigation['logs']
            while last_log_index < len(current_logs):
                log_msg = current_logs[last_log_index]
                # EventSourceResponse handles the "data: " prefix, so just yield JSON
                yield json.dumps({'type': 'log', 'message': log_msg}) + '\n\n'
                last_log_index += 1
            
            # Check if investigation is complete
            if investigation['status'] in ['completed', 'error']:
                # Send any final logs first
                while last_log_index < len(investigation['logs']):
                    log_msg = investigation['logs'][last_log_index]
                    yield json.dumps({'type': 'log', 'message': log_msg}) + '\n\n'
                    last_log_index += 1
                
                # Send final result
                final_data = {
                    'type': 'complete',
                    'status': investigation['status'],
                    'result': investigation.get('result'),
                    'error': investigation.get('error')
                }
                yield json.dumps(final_data) + '\n\n'
                
                # Clean up
                with investigations_lock:
                    if investigation_id in investigations:
                        del investigations[investigation_id]
                break
            
            # Debounce: only check for new logs every 0.5 seconds
            current_time = asyncio.get_event_loop().time()
            if current_time - last_emit_time < 0.5:
                await asyncio.sleep(0.5 - (current_time - last_emit_time))
            else:
                last_emit_time = current_time
            
            await asyncio.sleep(0.05)

    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)