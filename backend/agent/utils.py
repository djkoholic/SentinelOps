from pathlib import Path
import json

def _load_markdown(path, headings=['1. Product Overview', '2. Core Components', '3. Critical User Flows']):
    text = Path(path).read_text(encoding="utf-8").splitlines()

    sections = {}
    current = None

    for line in text:
        if line.startswith("## "):
            title = line[3:].strip()
            current = title if title in headings else None
            if current:
                sections[current] = []

        elif current:
            sections[current].append(line)

    return {
        k: "\n".join(v).strip()
        for k, v in sections.items()
    }

def _refine_summarize(tool_name: str, hypothesis: str, raw_evidence: list[dict], chunk_size: int = 50) -> str:
    """
    Sequential refine summarization for time-series evidence where order matters.
    Sorts by timestamp, then walks chunks in chronological order, carrying a
    running summary forward.
    """
    from backend.agent.llms import evidence_summary_llm
    from backend.agent.prompts import EVIDENCE_REFINE_PROMPT

    if not raw_evidence:
        return "No records found in this time window."

    sorted_evidence = sorted(raw_evidence, key=lambda r: r["timestamp"])
    chunks = [sorted_evidence[i:i + chunk_size] for i in range(0, len(sorted_evidence), chunk_size)]
    total = len(sorted_evidence)

    print(f"Refine summarizing {total} records across {len(chunks)} chunks (size={chunk_size})")

    running_summary = "No summary yet — this is the first chunk."
    for i, chunk in enumerate(chunks):
        chunk_start = i * chunk_size
        chunk_end = min(chunk_start + len(chunk), total)
        print(f"  Refining with chunk {i+1}/{len(chunks)} (records {chunk_start}-{chunk_end})...")

        messages = EVIDENCE_REFINE_PROMPT.invoke({
            "hypothesis": hypothesis,
            "tool_name": tool_name,
            "running_summary": running_summary,
            "chunk_start": chunk_start,
            "chunk_end": chunk_end,
            "total_records": total,
            "chunk": json.dumps(chunk, default=str),
        })
        result = evidence_summary_llm.invoke(messages)
        running_summary = result.summary
        print(f"  Updated summary: {running_summary[:150]}...")

    return running_summary