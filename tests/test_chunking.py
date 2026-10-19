from app.chunking.splitter import chunk_document
from app.parser.cleaners import clean_text

STATUTE = """INTERPRETATION AND GENERAL PROVISIONS ACT
ARRANGEMENT OF SECTIONS
1.
Short title.
2.
Application.

8
CAP. 2
Interpretation and General Provisions
[Rev. 2022]
PART I – INTRODUCTORY
Short title.
1.\xa0This Act may be cited as the Interpretation and General Provisions Act.
Application.
2.\xa0 This Act shall not apply for the construction or interpretation of the
Constitution, which is not a written law for the purposes of this Act.

[Rev. 2022]
Interpretation and General Provisions
CAP. 2
9
Computation of time.
57.\xa0In computing time for the purposes of a written law, unless the contrary
intention appears, a period of days shall be deemed to be exclusive of the day on which the event happens.
"""


def test_clean_text_removes_page_headers_and_ligatures():
    text = clean_text(STATUTE + "ﬁnal")
    assert "[Rev. 2022]" not in text
    assert "CAP. 2" not in text
    assert "\xa0" not in text
    assert text.endswith("final")


def test_chunks_follow_sections_and_keep_headings():
    chunks = chunk_document(clean_text(STATUTE), chunk_size=200, overlap=20)
    by_section = {}
    for c in chunks:
        for s in c.sections:
            by_section.setdefault(s, c)  # first chunk of each section

    assert {"1", "2", "57"} <= set(by_section)
    assert by_section["57"].text.startswith("Computation of time.\n57.")
    assert "Computation of time" in by_section["57"].headings
    # Table-of-contents entries ("1.\nShort title.") are not treated as section starts.
    assert all("ARRANGEMENT OF SECTIONS" not in c.text for c in chunks if c.sections)


def test_small_sections_are_packed_and_labelled():
    chunks = chunk_document(clean_text(STATUTE), chunk_size=1200, overlap=100)
    packed = [c for c in chunks if len(c.sections) > 1]
    assert packed and packed[0].section_label.startswith("ss. ")


def test_long_sections_split_within_size_on_word_boundaries():
    body = "Long section.\n5. " + " ".join(f"word{i}" for i in range(800))
    chunks = chunk_document(body, chunk_size=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c.text) <= 500 for c in chunks)
    assert all(c.sections == ["5"] for c in chunks)
    assert all(not c.text.startswith("ord") for c in chunks[1:])
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_empty_text_gives_no_chunks():
    assert chunk_document("   ") == []
