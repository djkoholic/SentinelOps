
import json
import logging
from collections import deque

from .data_collector import DataCollector
from .llm_utils import call_llm
from .prompts import HYPOTHESIS_RANKING_PROMPT, TIME_RANGE_PARSE_PROMPT
from .constants import POSSIBLE_HYPOTHESIS, ACTION_REGISTRY, HYPOTHESIS_TO_TOOL_RANKED

logger = logging.getLogger(__name__)

class Investigator:
    def __init__(self, query):
        self.evidences = []
        self.findings = []
        self.past_actions = []
        self.query = query
        self._initialize_state()
        self.data_collector = DataCollector(self.start_time, self.end_time)
    
    def _initialize_state(self):
        # Step 1: Given the query, determine the time range for investigation (Prompt 1)
        self.start_time, self.end_time = self._parse_time_range()
         # Step 2: Planning Agent - This is our master agent, given a set of pre-defined hypothesis and the user query rank the hypothesis. (Prompt 2)
        self.ranked_hypothesis = self._rank_hypothesis()

    def _rank_hypothesis(self):
        hypothesis_str = "\n\n".join(f"{name}:\n{description.strip()}" for name, description in POSSIBLE_HYPOTHESIS.items())
        prompt = HYPOTHESIS_RANKING_PROMPT.replace("<<query>>", self.query).replace("<<hypothesis>>", hypothesis_str)
        ranked_hypothesis =  call_llm(prompt)
        return ranked_hypothesis

    def _parse_time_range(self):
        logger.info(f"Parsing time range from query: {self.query}")
        prompt = TIME_RANGE_PARSE_PROMPT.replace("<<query>>", self.query)
        response = call_llm(prompt)
        logger.info(f"LLM response for time parsing: {response}")
        start_time = f"2026-01-01 {response['start_time']}"
        end_time = f"2026-01-01 {response['end_time']}"
        logger.info(f"Extracted times - Start: {start_time}, End: {end_time}")
        return start_time, end_time
    
    def _summarize_findings(self):
        pass

    def _evaluate_findings(self):
        pass

    def investigate(self):
       
        # Step 3: The loop begins here, where we try to prove the hypothesis one by one based on ranking
        for curr_hypothesis in self.ranked_hypothesis:
            # Pick the first hypothesis and determine the best tool to prove it.
            # This part will be a prompt but for now we can hard code hypothesis to tool mapping
            remaining_actions = deque(HYPOTHESIS_TO_TOOL_RANKED(curr_hypothesis))
            
            while remaining_actions:
                action = remaining_actions.popleft()
                # Step 4: Execute the tool and get the context
                context = self.data_collector.collect_data(ACTION_REGISTRY[action])
                
            # The hypothesis we are currently proving alongwith the context is used to determine if current evidence supports the hypothesis
            # or do we need to gather more evidence or reject the hypothesis and move to the next one.
            evidence_summary = self._evaluate_evidence(hypothesis, context)

            self.evidence.append(evidence_summary)
            self.past_actions.append(f"Used tool {tool} to prove hypothesis {hypothesis}")

            # If evidence proves - send everything to a prompt and generate report - loop ends here
            if self._is_hypothesis_proven(hypothesis, evidence_summary):
                report = self._generate_report(hypothesis, evidence_summary, self.past_actions)
                return report

        # If no hypothesis is proven, return a summary of the investigation
        return self._generate_summary()

    def _determine_time_range(self, query):
        # Placeholder for logic to determine time range based on query
        return "All time"

    def _rank_hypothesis(self, hypothesis, query):
        # Placeholder for logic to rank hypothesis based on query
        return hypothesis

    def _select_tool(self, hypothesis):
        # Placeholder for logic to select the best tool for the hypothesis
        return "tool_1"

    def _execute_tool(self, tool, time_range):
        # Placeholder for logic to execute the tool and get context
        return f"Context from {tool} for {time_range}"

    def _evaluate_evidence(self, hypothesis, context):
        # Placeholder for logic to evaluate evidence based on hypothesis and context
        return f"Evidence for {hypothesis} from {context}"

    def _is_hypothesis_proven(self, hypothesis, evidence_summary):
        # Placeholder for logic to determine if hypothesis is proven based on evidence
        return True

    def _generate_report(self, hypothesis, evidence_summary, past_actions):
        # Placeholder for logic to generate a report based on hypothesis, evidence, and past actions
        return f"Report for hypothesis {hypothesis} with evidence {evidence_summary} and actions {past_actions}"

    def _generate_summary(self):
        # Placeholder for logic to generate a summary of the investigation
        return "No hypothesis was proven during the investigation."
