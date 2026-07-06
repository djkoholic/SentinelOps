from langchain_ollama import ChatOllama

from backend.agent.schemas import TimeRange

llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
)

time_range_llm = llm.with_structured_output(TimeRange)