from langgraph.graph import StateGraph, START, END
from backend.agent.nodes import (
    time_range_parser,
    planner,
    evidence_gatherer,
    evidence_assessor,
    generate_report,
    route_after_assessment,
)
from backend.agent.schemas import InvestigatorState

investigator_graph = StateGraph(InvestigatorState)

investigator_graph.add_node("time_range_parser", time_range_parser)
investigator_graph.add_node("planner", planner)
investigator_graph.add_node("evidence_gatherer", evidence_gatherer)
investigator_graph.add_node("evidence_assessor", evidence_assessor)
investigator_graph.add_node("generate_report", generate_report)

investigator_graph.add_edge(START, "time_range_parser")
investigator_graph.add_edge("time_range_parser", "planner")
investigator_graph.add_edge("planner", "evidence_gatherer")
investigator_graph.add_edge("evidence_gatherer", "evidence_assessor")

investigator_graph.add_conditional_edges(
    "evidence_assessor",
    route_after_assessment,
    {
        "planner": "planner",
        "generate_report": "generate_report",
    },
)

investigator_graph.add_edge("generate_report", END)

investigator = investigator_graph.compile()