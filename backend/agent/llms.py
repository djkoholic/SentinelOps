from langchain_ollama import ChatOllama

from backend.agent.schemas import TimeRange, BeliefState

llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)

time_range_llm = llm.with_structured_output(TimeRange)

planner_llm = llm.with_structured_output(BeliefState)