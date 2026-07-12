from langgraph.graph import StateGraph, START, END
from backend.agent.nodes import time_range_parser, planner
from backend.agent.schemas import InvestigatorState

investigator_graph = StateGraph(InvestigatorState)

investigator_graph.add_node("time_range_parser", time_range_parser)
investigator_graph.add_node("planner", planner)

investigator_graph.add_edge(START, "time_range_parser")
investigator_graph.add_edge("time_range_parser", "planner")
investigator_graph.add_edge("planner", END)  # swap for action_taker later

investigator = investigator_graph.compile()