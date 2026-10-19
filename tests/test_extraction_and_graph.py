import pytest

from app.chunking.splitter import Chunk
from app.extraction.knowledge_extractor import extract_knowledge, parse_json_object, salvage_json_object
from app.generation.llm_client import LLMTruncatedError
from app.graph import graph_builder as gb
from app.graph.cypher_queries import query_terms
from app.graph.normalize import entity_key, relation_type


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.reply


@pytest.mark.parametrize("raw", [
    '{"entities": [], "relations": []}',
    '```json\n{"entities": [], "relations": []}\n```',
    'Here you go:\n{"entities": [], "relations": []}\nThanks',
    '<think>hmm {not json}</think>{"entities": [], "relations": []}',
])
def test_parse_json_object_handles_common_llm_wrappers(raw):
    assert parse_json_object(raw) == {"entities": [], "relations": []}


def test_parse_json_object_salvages_items_before_a_syntax_error():
    raw = '{"entities": [{"name": "A", "type": "Act"}, {"name": "B" "type": "Act"}], "relations": []}'
    assert parse_json_object(raw) == {"entities": [{"name": "A", "type": "Act"}]}


def test_salvage_truncated_reply_keeps_complete_items():
    partial = '{"entities": [{"name": "A", "type": "Act"}], "relations": [{"source": "A", "relation": "X", "target": "B", "chunk": 1}, {"source": "A", "rel'
    assert salvage_json_object(partial) == {
        "entities": [{"name": "A", "type": "Act"}],
        "relations": [{"source": "A", "relation": "X", "target": "B", "chunk": 1}],
    }


def test_truncated_llm_reply_is_salvaged_by_extractor():
    class TruncatingLLM:
        def generate(self, prompt, **kw):
            raise LLMTruncatedError('{"entities": [{"name": "Kenya Law Reform Commission", "type": "Institution"}], "rel', "cut")

    out = extract_knowledge([Chunk(0, "t")], title="Cap. 3", llm=TruncatingLLM())
    assert [e["name"] for e in out["entities"]] == ["Kenya Law Reform Commission"]


def test_parse_json_object_rejects_empty():
    with pytest.raises(ValueError):
        parse_json_object("")


def test_extract_knowledge_normalises_output_and_chunk_ids():
    chunks = [Chunk(4, "text a", ["3"]), Chunk(5, "text b", ["4"])]
    llm = FakeLLM(
        '{"entities": [{"name": " Kenya Law Reform Commission ", "type": "Institution"}, {"name": ""}],'
        ' "triples": [{"subject": "Act", "relation": "establishes", "object": "Commission", "chunk": 5},'
        '             {"source": "A", "relation": "x", "target": "B", "chunk": 99},'
        '             {"source": "", "relation": "x", "target": "B"}]}'
    )
    out = extract_knowledge(chunks, title="Cap. 3", llm=llm)

    assert out["entities"] == [{"name": "Kenya Law Reform Commission", "type": "Institution", "description": ""}]
    assert [r["chunk"] for r in out["relations"]] == [5, 4]  # unknown chunk id falls back to the first
    assert "[4] (s. 3)" in llm.prompts[0] and "Cap. 3" in llm.prompts[0]


@pytest.mark.parametrize("raw,expected", [
    ("is amended by", "IS_AMENDED_BY"),
    ("Section 3(1)", "SECTION_31"),
    ("2nd schedule of", "R_2ND_SCHEDULE_OF"),
    ("—", "RELATED_TO"),
    ("mentioned in", "MENTIONED_IN_REL"),
])
def test_relation_type_is_always_a_valid_identifier(raw, expected):
    assert relation_type(raw) == expected


def test_entity_key_merges_surface_variants():
    assert entity_key("The  Kenya Law Reform Commission.") == entity_key("kenya law reform commission")


def test_query_terms_drop_stopwords():
    assert query_terms("What does the Interpretation Act say about public holidays?") == [
        "interpretation", "public", "holidays",
    ]


def test_batch_chunks_respects_char_budget():
    chunks = [Chunk(i, "x" * 400) for i in range(10)]
    batches = gb.batch_chunks(chunks, max_chars=1000)
    assert [len(b) for b in batches] == [2, 2, 2, 2, 2]
    assert [c.index for b in batches for c in b] == list(range(10))


def test_failed_batch_is_retried_in_halves(monkeypatch):
    calls = []

    def fake_extract(batch, title):
        calls.append([c.index for c in batch])
        if len(batch) > 1:
            raise ValueError("truncated JSON")
        return {"entities": [{"name": f"E{batch[0].index}", "type": "Act", "description": ""}], "relations": []}

    monkeypatch.setattr(gb, "extract_knowledge", fake_extract)
    monkeypatch.setattr(gb.GraphBuilder, "write_knowledge", lambda self, k, b, d, t: {"entities": 1, "relations": 0})

    result = gb.GraphBuilder()._process_batch([Chunk(0, "a"), Chunk(1, "b")], "doc", "Title")
    assert calls == [[0, 1], [0], [1]]
    assert result == {"entities": 2, "relations": 0, "failed_batches": 0}
