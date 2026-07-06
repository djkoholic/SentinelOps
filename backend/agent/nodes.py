from datetime import datetime

from backend.agent.llms import time_range_llm
from backend.agent.schemas import InvestigatorState
from backend.agent.prompts import TIME_RANGE_PROMPT

def time_range_parser(state: InvestigatorState) -> InvestigatorState:

    """
    This node parses the time range from the query using the LLM
    and returns the start and end times as datetime objects.
    """

    messages = TIME_RANGE_PROMPT.invoke({
        "query": "Investigate between 10 AM and 11 AM"
    })
    response = time_range_llm.invoke(messages)

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

    return {
        "start_time": start_dt,
        "end_time": end_dt,
    }