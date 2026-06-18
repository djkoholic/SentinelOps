import json

from llm_utils import call_llm

TIME_RANGE_PARSE_PROMPT = """
You are given with a user query about investigating an issue that happened within a specific time range.
Your task is to extract and parse the start time and end time from the query of the time range and return it in the following format:
{
    "start_time": "11:30:00",
    "end_time": "13:05:25"
}
User query - <<query>>
Output:
"""

INVESTIGATION_PROMPT = """
You are an AI agent that is tasked with investigating a specific issue based on the provided context.
Your goal is to analyze the context and provide a detailed explanation of what happened and why it happened

User query - <<query>>

Requests:
<<requests>>

Application Logs:
<<application_logs>>

Request Metrics:
<<request_metrics>>

Pod Metrics:
<<pod_metrics>>

Output:
You need to provide the following keys -
1. Summary of the issue
2. Root cause analysis
3. Impact assessment
4. Recommended action for remediation

If any of the above keys cannot be determined from the context, they can be left empty string.

Output Format:
{
    "summary": "",
    "root_cause_analysis": "",
    "impact_assessment": "",
    "recommended_action": ""
} 
"""

def parse_time_range(query):
    print(f"[DEBUG] Parsing time range from query: {query}")
    prompt = TIME_RANGE_PARSE_PROMPT.replace("<<query>>", query)
    response = call_llm(prompt)
    print(f"[DEBUG] LLM response for time parsing: {response}")
    time_range = json.loads(response)
    start_time = f"2026-01-01 {time_range['start_time']}"
    end_time = f"2026-01-01 {time_range['end_time']}"
    print(f"[DEBUG] Extracted times - Start: {start_time}, End: {end_time}")
    return start_time, end_time

def run_investigator(query, context):
    print(f"[DEBUG] Starting investigation for query: {query}")
    requests = context['requests']
    application_logs = context['application_logs']
    request_metrics = context['request_metrics']
    pod_metrics = context['pod_metrics']
    print(f"[DEBUG] Context data - Requests: {len(requests)}, Logs: {len(application_logs)}, Metrics: {len(request_metrics)}, Pod metrics: {len(pod_metrics)}")

    prompt = INVESTIGATION_PROMPT.replace("<<query>>", query)
    prompt = prompt.replace("<<requests>>", json.dumps(requests, indent=2))
    prompt = prompt.replace("<<application_logs>>", json.dumps(application_logs, indent=2))
    prompt = prompt.replace("<<request_metrics>>", json.dumps(request_metrics, indent=2))
    prompt = prompt.replace("<<pod_metrics>>", json.dumps(pod_metrics, indent=2))

    response = call_llm(prompt)
    print(f"[DEBUG] LLM investigation response: {response[:200]}...") # Print first 200 chars
    investigation_result = json.loads(response)
    print(f"[DEBUG] Investigation result keys: {list(investigation_result.keys())}")
    return investigation_result