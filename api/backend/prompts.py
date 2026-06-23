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