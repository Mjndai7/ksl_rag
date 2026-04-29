import fitz  # PyMuPDF
from typing import Dict

def parse_pdf(file_path: str) -> str:
    """
    Extract plain text from pdf
    """
    doc = fitz.open(file_path)
    pages = []

    for page in doc:
        text = page.get_text("text")
        if text:
            pages.append(text)

    return "\n".join(pages)


def parse_pdf_with_metadata(file_path: str) -> Dict:
    """
    Optional richer parser.
    """

    doc = fitz.open(file_path)

    pages = []

    for page in doc:
        text = page.get_text("text")
        if text:
            pages.append(text)
    
    metadata = doc.metadata
    doc.close()

    return {
        "text": "\n".join(pages),
        "metadata": metadata,
    }