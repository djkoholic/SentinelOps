
import json
import logging
from collections import deque

from .data_collector import DataCollector
from .llm_utils import call_llm
from .prompts import HYPOTHESIS_RANKING_PROMPT, INVESTIGATION_REPORT_NO_CONCLUSION_PROMPT, INVESTIGATION_REPORT_PROMPT, TIME_RANGE_PARSE_PROMPT, EVIDENCE_EVALUATION_PROMPT, HYPOTHESIS_PROOF_PROMPT
from .constants import POSSIBLE_HYPOTHESIS, ACTION_REGISTRY, HYPOTHESIS_TO_TOOL_RANKED

logger = logging.getLogger(__name__)

class Investigator:
    def __init__(self, query):
        self.is_hypothesis_proven = False
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
        prompt = HYPOTHESIS_RANKING_PROMPT.replace("<<query>>", self.query).replace("<<hypotheses>>", json.dumps(POSSIBLE_HYPOTHESIS, indent=2))
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
    
    def _evaluate_evidence(self, hypothesis, evidence):
        prompt = EVIDENCE_EVALUATION_PROMPT.replace("<<hypothesis>>", hypothesis).replace("<<evidence>>", json.dumps(evidence, indent=2))
        response = call_llm(prompt)
        return response['finding']

    def _prove_hypothesis(self, hypothesis):
        prompt = HYPOTHESIS_PROOF_PROMPT.replace("<<query>>", self.query).replace("<<hypothesis>>", hypothesis).replace("<<findings>>", json.dumps(self.findings, indent=2)).replace("<<actions>>", json.dumps(self.past_actions, indent=2))
        response = call_llm(prompt)
        hypothesis_proven = response['hypothesis_proven']
        reason = response['reason']
        if hypothesis_proven.lower() == 'yes':
            return True, reason
        else:
            return False, reason

    def _generate_investigation_report(self):
        if self.is_hypothesis_proven:
            prompt = INVESTIGATION_REPORT_PROMPT.replace("<<query>>", self.query).replace("<<hypothesis>>", self.proven_hypothesis).replace("<<proof_reason>>", self.proof_reason).replace("<<findings>>", json.dumps(self.findings, indent=2))
        else:
            prompt = INVESTIGATION_REPORT_NO_CONCLUSION_PROMPT.replace("<<query>>", self.query).replace("<<hypothesis>>", json.dumps(POSSIBLE_HYPOTHESIS, indent=2)).replace("<<findings>>", json.dumps(self.findings, indent=2))
        response = call_llm(prompt)
        return response
        
    def investigate(self):
       
        # Step 3: The loop begins here, where we try to prove the hypothesis one by one based on ranking
        for curr_hypothesis in self.ranked_hypothesis:
            print(f"Evaluating hypothesis: {curr_hypothesis}")
            # Pick the first hypothesis and determine the best tool to prove it.
            # This part will be a prompt but for now we can hard code hypothesis to tool mapping
            remaining_actions = deque(HYPOTHESIS_TO_TOOL_RANKED[curr_hypothesis])
            print(f"Tools: {remaining_actions}")
            
            while remaining_actions:
                action = remaining_actions.popleft()
                if action in self.past_actions:
                    print(f"Tool: {action} already executed, skipping...")
                print(f"Running tool: {action}")
                # Step 4: Execute the tool and get the context
                evidence = self.data_collector.collect_data(ACTION_REGISTRY[action])
                print(f"Found evidence: {evidence}")
                
                finding = self._evaluate_evidence(curr_hypothesis, evidence)
                print(f"Findings from found evidence: {finding}")
                self.evidences.append(evidence)
                self.findings.append(finding)
                self.past_actions.append(action)

                is_hypothesis_proven, reason = self._prove_hypothesis(curr_hypothesis)

                if is_hypothesis_proven:
                    self.proven_hypothesis = curr_hypothesis
                    self.is_hypothesis_proven = is_hypothesis_proven
                    self.proof_reason = reason
                    
                    return self._generate_investigation_report()
            # If evidence proves - send everything to a prompt and generate report - loop ends here

        # If no hypothesis is proven, return a summary of the investigation
        return self._generate_investigation_report()
