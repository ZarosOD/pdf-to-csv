"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .csv_out import write_csv, write_csv_file
from .models import Invoice
from .pdf import collect_pdfs, parse_pdf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="extract.py",
        description="Extract invoice and receipt fields from text-layer PDFs into one CSV.",
    )
    parser.add_argument("input", type=Path, help="a PDF file, or a directory of PDFs")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="CSV file to write (default: stdout)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="print a one-line summary: files seen, parsed clean, needing review",
    )
    parser.add_argument(
        "--date-order",
        choices=("mdy", "dmy"),
        default="mdy",
        help="how to read an ambiguous all-numeric date such as 03/04/2024 "
        "(default: mdy). Unambiguous dates are read correctly either way.",
    )
    parser.add_argument(
        "--fail-on-review",
        action="store_true",
        help="exit 1 if any document needs review (useful in a pipeline)",
    )
    return parser


def summarise(invoices: list[Invoice]) -> str:
    review = [i for i in invoices if i.needs_review]
    return (
        f"{len(invoices)} files, {len(invoices) - len(review)} parsed clean, "
        f"{len(review)} needing review"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        pdfs = collect_pdfs(args.input)
    except FileNotFoundError:
        print(f"extract.py: no such file or directory: {args.input}", file=sys.stderr)
        return 2

    if not pdfs:
        print(f"extract.py: no PDFs found under {args.input}", file=sys.stderr)
        return 2

    invoices = [parse_pdf(path, args.date_order) for path in pdfs]

    if args.output:
        write_csv_file(invoices, args.output)
    else:
        write_csv(invoices, sys.stdout)

    if args.report:
        stream = sys.stdout if args.output else sys.stderr
        print(summarise(invoices), file=stream)
        for invoice in invoices:
            if invoice.needs_review:
                detail = list(invoice.issues)
                if invoice.missing_fields:
                    detail.insert(0, "missing: " + ", ".join(invoice.missing_fields))
                print(f"  review  {invoice.source_file}: {'; '.join(detail)}", file=stream)

    if args.fail_on_review and any(i.needs_review for i in invoices):
        return 1
    return 0
