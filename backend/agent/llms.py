from langchain_ollama import ChatOllama

from backend.agent.schemas import TimeRange, BeliefState, EvidenceSummary, Conclusion

llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
    num_ctx=8192,
    keep_alive='0s'
)

time_range_llm = llm.with_structured_output(TimeRange)

planner_llm = llm.with_structured_output(BeliefState)

evidence_summary_llm = llm.with_structured_output(EvidenceSummary)

evidence_assessor_llm = llm.with_structured_output(Conclusion)