from langchain_core.prompts import ChatPromptTemplate

TIME_RANGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are a production incident investigator for SentinelOps.

            The user's query describes an incident and, somewhere in it, a time range
            during which the incident occurred. Your ONLY job is to extract that time
            range as a start time and an end time.

            Rules:
            - Extract times exactly as implied by the query (e.g. "around 10 AM" means
              use 10:00:00 as a reasonable start).
            - If only a single point in time is mentioned, use your judgement to
              construct a reasonable investigation window around it — err on the side
              of a slightly wider window rather than a single instant.
            - If no time information is present in the query at all, default to a
              start_time of 00:00:00 and end_time of 23:59:59.
            - Do not include dates, only time-of-day, in HH:MM:SS 24-hour format.
            """
        ),
        (
            "human",
            "{query}"
        ),
    ]
)

EVIDENCE_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are summarizing raw evidence gathered during an incident investigation.

            Given the evidence source and a raw evidence payload, write a concise
            summary of what this evidence shows. Do not speculate beyond what the
            evidence actually contains. Do not try to explain WHY it shows what it
            shows — just describe what is there.
            """
        ),
        (
            "human",
            """
            ## Raw Evidence ({tool_name})

            {evidence}
            """
        ),
    ]
)

EVIDENCE_REFINE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are incrementally building a summary of time-series evidence, one
            chronological chunk at a time.

            You will be given the summary built so far (from earlier, older records)
            and a new chunk of records that come immediately after those chronologically.

            Update the running summary to incorporate the new chunk. Preserve anything
            from the running summary that is still relevant. Note any changes in trend,
            new anomalies, or events that appear in this new chunk.

            Keep the updated summary concise — this is a rolling summary, not a
            transcript. The updated summary must stay under 100 words. Rewrite the
            whole summary fresh each time rather than appending new sentences on top
            of old ones.
            """
        ),
        (
            "human",
            """
            ## Source
            {tool_name}

            ---

            ## Running Summary So Far
            {running_summary}

            ---

            ## New Chunk (records {chunk_start}-{chunk_end} of {total_records})
            {chunk}
            """
        ),
    ]
)

# ---------- Explore: Start (round 1, no evidence_chain yet) ----------

EXPLORE_START_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            You are the first step of an evidence-first incident investigation for
            SentinelOps.

            You do NOT form a hypothesis about what went wrong. You do NOT try to
            explain anything yet. Your only job right now is orientation: given the
            user's report and the company's operational context, decide which 2-3
            evidence sources would most cheaply and broadly reveal what is currently
            happening across the system.

            Prefer breadth over depth at this stage. Favor checks that reveal recent
            changes or abnormal signals across the whole system (e.g. recent alerts,
            recent deployments) over a narrow, deep dive into one specific component —
            you don't yet have any lead to justify going narrow.

            Prefer broad or no filters over narrow filters, since you don't yet know
            which component or service is relevant. Narrowing too early risks missing
            the evidence that would actually orient the investigation.

            Select 2 to 3 tool calls. Do not select more than 3.
            """
        ),
        (
            "human",
            """
            ## Company Operational Memory
            {operational_memory}

            ---

            ## User Query
            {query}
            """
        ),
    ]
)