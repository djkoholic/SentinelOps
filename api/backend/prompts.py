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

HYPOTHESIS_RANKING_PROMPT = """
You are an investigation planning agent.

Your task is to rank a set of possible incident hypotheses based on how likely they are to explain the user's query.

User Query: <<query>>

Possible Hypotheses:
<<hypotheses>>

Instructions:
- Analyze the user's query carefully.
- Use the hypothesis descriptions to understand what each hypothesis represents.
- Rank ALL hypotheses from most likely to least likely.
- Even if multiple hypotheses seem plausible, choose the one that best matches the query first.
- Do not remove hypotheses from the list.
- Do not explain your reasoning.
- Return ONLY the ranked list.

Output Format:
[
    "hypothesis_name_1",
    "hypothesis_name_2",
    "hypothesis_name_3",
    "hypothesis_name_4"
]

Output:
"""

EVIDENCE_EVALUATION_PROMPT = """
You are an investigation agent.

Current Hypothesis:
<<hypothesis>>

Evidence:
<<evidence>>

Analyze the evidence and summarize the most important observations.

Your job is NOT to determine whether the hypothesis is proven.

Your job is ONLY to summarize findings that may be relevant.

Output Format:

{
    "finding": "concise summary of what was observed"
}
Output:
"""

HYPOTHESIS_PROOF_PROMPT = """
You are the master investigation planner.

User Query:
<<query>>

Current Hypothesis:
<<hypothesis>>

Findings:
<<findings>>

Past Actions:
<<actions>>

Determine whether the current hypothesis is sufficiently supported.

Output Format:

{
    "hypothesis_proven": Yes,
    "reason": "short explanation"
}
Output:
"""

INVESTIGATION_REPORT_PROMPT = """
You are an AI Reliability Engineer.

User Query:
<<query>>

Proven Hypothesis:
<<hypothesis>>

Reason:
<<proof_reason>>

Findings:
<<findings>>

Generate a final investigation report.

Output Format:

{
    "summary": "short summary of the incident",
    "root_cause": "root cause identified",
    "recommended_fix": "the fix that should be applied or action that shoukd be taken to mitigate the issue"
}

Output:
"""

INVESTIGATION_REPORT_NO_CONCLUSION_PROMPT = """
You are an AI Reliability Engineer.

User Query:
<<query>>

Hypotheses Considered:
<<hypotheses>>

Findings:
<<findings>>

No hypothesis was conclusively proven.

Generate an investigation summary.

Output Format:

{
    "summary": "summary of investigation"
    "why_inconclusive": "why no hypothesis could be proven",
}

Output:
"""