from pathlib import Path

def load_markdown(path, headings=['1. Product Overview', '2. Core Components', '3. Critical User Flows']):
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