from langchain_core.prompts import ChatPromptTemplate

TIME_RANGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are an expert cybersecurity investigator.
            The user is asking to investigate an event within a specific time range.
            Your task is to extract ONLY the start time and end time.

            Return ONLY valid JSON.
            Example:

            {{
                "start_time": "11:30:00",
                "end_time": "13:05:25"
            }}
            """
        ),
        (
            "human",
            "{query}"
        ),
    ]
)