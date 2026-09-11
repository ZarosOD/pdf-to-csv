"""Text extraction. The only part of the package that knows about PDFs."""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .models import Invoice
from .parse import parse_invoice

PDF_SUFFIXES = {".pdf"}
# Below this many characters a PDF almost certainly has no text layer, i.e. it
# is a scan. We say so instead of returning a page of empty fields.
MIN_TEXT_CHARS = 40


def extract_text(path: Path) -> str:
    """Concatenate the text layer of every page, in page order."""
    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages)


def parse_pdf(path: Path, date_order: str = "mdy") -> Invoice:
    try:
        text = extract_text(path)
    except Exception as exc:  # a corrupt or encrypted file is data, not a crash
        invoice = Invoice(source_file=path.name)
        invoice.issues.append(f"could not read PDF: {type(exc).__name__}: {exc}")
        return invoice

    if len(text.strip()) < MIN_TEXT_CHARS:
        invoice = Invoice(source_file=path.name)
        invoice.issues.append("no text layer (looks like a scan; OCR is out of scope)")
        return invoice

    return parse_invoice(text, path.name, date_order)


def collect_pdfs(target: Path) -> list[Path]:
    """One PDF, or every PDF under a directory, sorted by name."""
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(p for p in target.rglob("*") if p.suffix.lower() in PDF_SUFFIXES)
    raise FileNotFoundError(target)
