def merge_contexts(vector_hits: list[dict], graph_hits: list[dict], max_graph: int = 8) -> list[dict]:
    """Vector passages first (they carry the statute text), then distinct graph facts."""
    merged = []
    seen = set()

    def add(item):
        key = " ".join(item["text"].split()).lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)

    for v in vector_hits:
        add(v)
    for g in graph_hits[:max_graph]:
        add(g)
    return merged
