from typing import List


def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> List[str]:

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def paragraph_chunker(
    text: str,
    max_chars: int = 1500,
):

    paragraphs = text.split("\n\n")

    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += "\n" + p
        else:
            if current:
                chunks.append(current.strip())
            current = p

    if current:
        chunks.append(current.strip())

    return chunks