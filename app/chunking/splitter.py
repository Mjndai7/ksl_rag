import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.settings import settings

# Body section starts look like "Short title.\n1. This Act may be cited ...".
# Table-of-contents entries put a newline after the number ("1.\nShort title."), so they don't match.
_SECTION_START = re.compile(r"(?m)^(?P<num>\d{1,3}[A-Z]{0,2})\.[ \t]+(?=\S)")


@dataclass
class Chunk:
    index: int
    text: str
    sections: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)

    @property
    def section_label(self) -> Optional[str]:
        if not self.sections:
            return None
        if len(self.sections) == 1:
            return f"s. {self.sections[0]}"
        return f"ss. {self.sections[0]}–{self.sections[-1]}"


@dataclass
class _Section:
    num: Optional[str]
    heading: Optional[str]
    text: str


def _split_sections(text: str) -> List[_Section]:
    matches = list(_SECTION_START.finditer(text))
    if not matches:
        return [_Section(None, None, text)]

    sections: List[_Section] = []
    preamble_end = matches[0].start()

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end]

        # The marginal heading is the line just before the section number, e.g. "Short title."
        heading = None
        before = text[:m.start()].rstrip("\n")
        last_line_start = before.rfind("\n") + 1
        last_line = before[last_line_start:]
        if last_line.endswith(".") and 3 <= len(last_line) <= 150 and not _SECTION_START.match(last_line):
            heading = last_line[:-1]
            if i == 0:
                preamble_end = last_line_start
            else:
                # Move the heading line from the previous section's tail into this one.
                prev = sections[-1]
                if prev.text.rstrip("\n").endswith(last_line):
                    prev.text = prev.text.rstrip("\n")[: -len(last_line)]
            body = f"{last_line}\n{body}"

        sections.append(_Section(m.group("num"), heading, body))

    preamble = text[:preamble_end].strip()
    if preamble:
        sections.insert(0, _Section(None, None, preamble))
    return sections


def _split_long(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into windows of ~chunk_size chars, breaking on paragraph/line/word boundaries."""
    if len(text) <= chunk_size:
        return [text]

    pieces = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            window = text[start:end]
            for sep in ("\n\n", "\n", ". ", " "):
                cut = window.rfind(sep)
                if cut > chunk_size // 2:
                    end = start + cut + len(sep)
                    break
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        next_start = end - overlap
        # Start the overlap on a word boundary.
        space = text.find(" ", next_start, end)
        start = space + 1 if space != -1 else next_start
    return pieces


def chunk_document(
    text: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
) -> List[Chunk]:
    """Chunk a statute along section boundaries.

    Small consecutive sections are packed together up to chunk_size; long sections are
    split with overlap. Each chunk records the section numbers it covers for citation.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP if overlap is None else overlap
    if not text or not text.strip():
        return []

    chunks: List[Chunk] = []
    buf_text = ""
    buf_sections: List[str] = []
    buf_headings: List[str] = []

    def flush():
        nonlocal buf_text, buf_sections, buf_headings
        if buf_text.strip():
            chunks.append(Chunk(len(chunks), buf_text.strip(), buf_sections, buf_headings))
        buf_text, buf_sections, buf_headings = "", [], []

    for sec in _split_sections(text):
        body = sec.text.strip()
        if not body:
            continue
        nums = [sec.num] if sec.num else []
        heads = [sec.heading] if sec.heading else []

        if len(body) > chunk_size:
            flush()
            for piece in _split_long(body, chunk_size, overlap):
                chunks.append(Chunk(len(chunks), piece, list(nums), list(heads)))
            continue

        if buf_text and len(buf_text) + len(body) + 2 > chunk_size:
            flush()
        buf_text = f"{buf_text}\n\n{body}" if buf_text else body
        buf_sections += nums
        buf_headings += heads

    flush()
    return chunks


def chunk_text(text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
    """Plain-string variant of chunk_document."""
    return [c.text for c in chunk_document(text, chunk_size, overlap)]
