#!/usr/bin/env python3
"""The recorded scene. EDIT THIS FILE for a new piece — it is the Playwright
equivalent of a VHS tape. The rendering is not here: demo/lib/sheet.py is
shared by all four pieces and builds every frame.

Four beats, about 18 seconds, in the one shape all four clips use:

  1. BEFORE   samples/ — twelve PDFs from twelve vendors, listed off disk.
  2. BEFORE   one of them, rendered. The listing says there are twelve
              documents; this says what a document looks like, and it is the
              frame that makes "no per-vendor templates" mean something.
  3. COMMAND  one line, and the real stdout it printed.
  4. AFTER    invoices.csv in the grid, with the flagged rows on screen.

Beat 4 opens the file beat 3 had just written, read off disk at record time.
Nothing in this file knows what is in that CSV; if extract.py did not write it,
`read_table` raises and there is no clip.

Beat 2 renders the sample PDF itself with pypdfium2, which pdfplumber already
brings in — the page on screen is the file in samples/, not a picture of an
invoice.

The invoices are invented. No real vendor, customer or client data appears here
or in the recording.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "demo" / "lib"))

import sheet  # noqa: E402

# The one sample shown whole. Its rows are the first rows of the output, so the
# AFTER frame is the same invoice the viewer has just read.
SHOWN = "01_northwind_print.pdf"

# Invoice-level fields plus the line item, which is the shape a client checks
# first: did it get the header right, and did it get the lines under it.
CSV_COLUMNS = [
    "source_file", "invoice_number", "invoice_date", "description",
    "quantity", "unit_price", "line_total", "total", "needs_review", "issues",
]
# vendor is deliberately not shown: it repeats what source_file already says
# and the column it frees is what makes invoice_number and the numbers legible.
WIDTHS = {"source_file": 2.0, "description": 2.2, "issues": 1.6,
          "invoice_number": 1.15, "invoice_date": 1.0, "needs_review": 0.85,
          "quantity": 0.6, "unit_price": 0.8, "line_total": 0.85, "total": 0.8}


def page_png(pdf_path: Path, scale: float = 2.0,
             max_aspect: float = 0.82) -> tuple[bytes, bool]:
    """Page 1 of a real PDF, as PNG bytes, plus whether it was cropped.

    pypdfium2 arrives with pdfplumber, so this adds no dependency the piece did
    not already have. If it is somehow absent the message says what is missing
    rather than letting the scene fall back to something invented.

    A4 is 1:1.41 and the frame is 16:9, so a whole page fits at about a third
    of the width and nothing on it can be read — which defeats the point of
    showing it. The margins go first (crop to the ink), and if the result is
    still taller than `max_aspect` the bottom goes, from the bottom, so what
    survives is the top of the page in reading order. The caller is told, and
    says so in the caption: a cropped page presented as a whole one is the kind
    of small lie this clip exists to avoid.
    """
    try:
        import pypdfium2
        from PIL import ImageOps
    except ImportError:  # pragma: no cover - the venv installs both with pdfplumber
        raise SystemExit(
            "scene.py: pypdfium2/Pillow are not installed, so the sample page "
            "cannot be rendered. They ship with pdfplumber; delete .venv and "
            "re-run ./demo/setup.sh."
        ) from None

    document = pypdfium2.PdfDocument(pdf_path)
    try:
        image = document[0].render(scale=scale).to_pil().convert("RGB")
    finally:
        document.close()

    ink = ImageOps.invert(image.convert("L")).getbbox()
    if ink:
        pad = int(8 * scale)
        image = image.crop(
            (max(0, ink[0] - pad), max(0, ink[1] - pad),
             min(image.width, ink[2] + pad), min(image.height, ink[3] + pad))
        )

    cropped = False
    limit = int(image.width * max_aspect)
    if image.height > limit:
        image = image.crop((0, 0, image.width, limit))
        cropped = True

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), cropped


def record(video_dir: Path) -> Path:
    samples = REPO / "samples"

    # Both BEFORE beats are built before the tool runs, so neither can be
    # showing anything the run produced.
    listing = sheet.view(sheet.read_dir(samples, "*.pdf", base=REPO), limit=13)
    page, cropped = page_png(samples / SHOWN)

    command = sheet.run_command(
        [sys.executable, "extract.py", "samples/", "-o", "invoices.csv", "--report"],
        cwd=REPO,
    )

    rows = sheet.read_table(REPO / "invoices.csv", base=REPO)
    flagged = sheet.rows_where(rows, "needs_review", "yes")
    after = sheet.tint(
        sheet.view(rows, CSV_COLUMNS, rows=sheet.head_and(rows, flagged), widths=WIDTHS),
        flagged,
        "flag",
    )

    with sheet.Scene(video_dir) as scene:
        scene.show(
            sheet.grid_html(
                listing,
                step="BEFORE",
                said="twelve invoices, twelve vendors, twelve layouts",
                kind="before",
            ),
            sheet.HOLD_BEFORE / 2,
        )
        scene.show(
            sheet.document_html(
                page,
                step="BEFORE",
                said="no template was written for this one, or for any of them",
                caption=f"samples/{SHOWN} · page 1 of 1"
                + (" · top of the page" if cropped else ""),
            ),
            sheet.HOLD_BEFORE / 2,
        )
        scene.show(
            sheet.terminal_html(
                command,
                said="one command: read every page, write one CSV",
            ),
            sheet.HOLD_COMMAND,
        )
        scene.show(
            sheet.grid_html(
                after,
                step="AFTER",
                said="invoices.csv, opened — header fields and the lines under them",
                legend={"flag": f"{len(flagged)} rows flagged: a field it would not guess"},
            ),
            sheet.HOLD_AFTER,
        )

    return scene.video_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    args.video_dir.mkdir(parents=True, exist_ok=True)
    print(record(args.video_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
