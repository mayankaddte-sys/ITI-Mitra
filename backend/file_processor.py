"""Extract text from PDF / DOCX / TXT.

Every extractor returns a list of (page_label, text) segments so that answers can
cite page numbers. page_label is None for formats without pages.
"""
import logging
import re
from typing import List, Optional, Tuple

from . import config

log = logging.getLogger("iti_mitra.files")

Segment = Tuple[Optional[int], str]


class UnreadableFileError(Exception):
    """Raised with a user-safe message when a file cannot be turned into text."""


# Characters that are neither ASCII, Devanagari, nor common punctuation. Legacy Hindi fonts
# (Kruti Dev etc.) and broken font maps extract as a soup of these. Heuristic, not perfect.
_ODD_CHARS = re.compile(r"[^\x00-\x7F\u0900-\u097F\u2000-\u206F\u00A0\u20B9\s]")


def looks_garbled(text: str) -> bool:
    sample = text.strip()
    if len(sample) < 40:
        return False
    if "(cid:" in sample or sample.count("\ufffd") > 3:
        return True
    return len(_ODD_CHARS.findall(sample)) / len(sample) > 0.25


def _ocr_pdf(path: str) -> Optional[List[Segment]]:
    """Optional OCR. Returns None if OCR libraries / binaries are not available."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return None
    try:
        images = convert_from_path(path, dpi=200, last_page=config.MAX_OCR_PAGES)
        segments: List[Segment] = []
        for i, img in enumerate(images, start=1):
            text = pytesseract.image_to_string(img, lang=config.OCR_LANGS)
            if text.strip():
                segments.append((i, text))
        return segments
    except Exception:
        log.exception("OCR failed for %s", path)
        return None


def extract_pdf(path: str) -> List[Segment]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        n_pages = len(reader.pages)
        segments: List[Segment] = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                segments.append((i, text))
    except Exception as exc:
        log.exception("PDF read failed")
        raise UnreadableFileError("Could not read this PDF. It may be corrupted or password-protected.") from exc

    total = sum(len(t) for _, t in segments)
    scanned = n_pages > 0 and total < 30 * n_pages
    garbled = bool(segments) and looks_garbled(" ".join(t for _, t in segments[:5]))

    if scanned or garbled:
        ocr = _ocr_pdf(path)
        if ocr:
            return ocr
        reason = "appears to be a scanned image" if scanned else "uses a legacy font that cannot be read as text"
        raise UnreadableFileError(
            f"This PDF {reason}, and OCR is not available on the server. "
            "Install the OCR extras (see README) or upload a text-based PDF / DOCX."
        )
    return segments


def extract_docx(path: str) -> List[Segment]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    try:
        doc = Document(path)
        lines: List[str] = []
        for child in doc.element.body.iterchildren():
            if child.tag.endswith("}p"):
                lines.append(Paragraph(child, doc).text)
            elif child.tag.endswith("}tbl"):
                table = Table(child, doc)
                for row in table.rows:
                    seen, cells = set(), []
                    for cell in row.cells:
                        if id(cell._tc) in seen:  # merged cells repeat
                            continue
                        seen.add(id(cell._tc))
                        cells.append(cell.text.strip().replace("\n", " "))
                    lines.append(" | ".join(cells))
        text = "\n".join(lines)
    except Exception as exc:
        log.exception("DOCX read failed")
        raise UnreadableFileError("Could not read this Word file. It may be corrupted.") from exc
    return [(None, text)] if text.strip() else []


def extract_txt(path: str) -> List[Segment]:
    with open(path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    return [(None, text)] if text.strip() else []


def process_file(path: str) -> List[Segment]:
    ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
    if ext == "pdf":
        segments = extract_pdf(path)
    elif ext == "docx":
        segments = extract_docx(path)
    elif ext == "txt":
        segments = extract_txt(path)
    else:
        raise UnreadableFileError(f"Unsupported file type: .{ext}")
    if not segments:
        raise UnreadableFileError("No readable text found in this file.")
    return segments
