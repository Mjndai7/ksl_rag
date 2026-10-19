SYSTEM_PROMPT = """You are a legal research assistant for the Laws of Kenya.
Answer strictly from the numbered sources provided. Cite every claim with its source number in
square brackets, e.g. [1] or [2][3], and name the Act and section when the source gives them.
If the sources do not contain the answer, say you don't know based on the available statutes.
Do not invent sections, dates or provisions."""

QA_PROMPT = """Sources:
{context}

Question: {question}

Answer concisely, with citations."""


def format_source(n: int, item: dict) -> str:
    meta = item.get("metadata") or {}
    if item.get("source") == "graph":
        return f"[{n}] Knowledge graph fact: {item['text']}"
    label = meta.get("document_name") or "Unknown document"
    if meta.get("section_label"):
        label += f", {meta['section_label']}"
    return f"[{n}] {label}\n{item['text']}"


def build_qa_prompt(question: str, contexts: list[dict]) -> str:
    if contexts:
        context = "\n\n".join(format_source(i, c) for i, c in enumerate(contexts, start=1))
    else:
        context = "No relevant sources were found."
    return QA_PROMPT.format(question=question.strip(), context=context)
