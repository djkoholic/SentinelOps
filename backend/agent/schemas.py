from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel

class InvestigatorState(TypedDict):
    query: str
    start_time: datetime
    end_time: datetime

class TimeRange(BaseModel):
    start_time: str
    end_time: str