import re

_LIGATURES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬀ": "ff",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
}

# Laws of Kenya running page headers, in either order:
#   "8\nCAP. 2\nInterpretation and General Provisions\n[Rev. 2022]\n"
#   "[Rev. 2022]\nInterpretation and General Provisions\nCAP. 2\n31\n"
_PAGE_HEADER = re.compile(
    r"\n(?:\d{1,4}\n)?CAP\.\s*[0-9A-Z]+\n[^\n]{1,150}\n\[Rev\.\s*\d{4}\](?:\n\d{1,4})?\n"
    r"|\n(?:\d{1,4}\n)?\[Rev\.\s*\d{4}\]\n[^\n]{1,150}\nCAP\.\s*[0-9A-Z]+(?:\n\d{1,4})?\n"
)


def clean_text(text: str) -> str:
    """Normalise PDF text: ligatures, non-breaking spaces and repeated page headers."""
    for lig, repl in _LIGATURES.items():
        text = text.replace(lig, repl)
    text = text.replace("\xa0", " ")
    text = _PAGE_HEADER.sub("\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
