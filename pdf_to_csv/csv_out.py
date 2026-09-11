"""CSV output: one row per line item, invoice-level fields repeated.

That shape drops straight into a spreadsheet pivot or a bookkeeping import
without any further reshaping, which is what the fields are usually wanted for.
A document with no line items still gets exactly one row so nothing disappears
silently.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import IO

from .models import Invoice

COLUMNS = [
    "source_file",
    "vendor",
    "invoice_number",
    "invoice_date",
    "currency",
    "line_no",
    "description",
    "quantity",
    "unit_price",
    "line_total",
    "subtotal",
    "tax",
    "total",
    "needs_review",
    "issues",
]


def _money(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def _quantity(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:g}"


def invoice_rows(invoice: Invoice) -> list[dict[str, str]]:
    issues = list(invoice.issues)
    if invoice.missing_fields:
        issues.insert(0, "missing: " + ", ".join(invoice.missing_fields))

    base = {
        "source_file": invoice.source_file,
        "vendor": invoice.vendor or "",
        "invoice_number": invoice.invoice_number or "",
        "invoice_date": invoice.invoice_date or "",
        "currency": invoice.currency or "",
        "subtotal": _money(invoice.subtotal),
        "tax": _money(invoice.tax),
        "total": _money(invoice.total),
        "needs_review": "yes" if invoice.needs_review else "no",
        "issues": "; ".join(issues),
    }

    if not invoice.line_items:
        return [{**base, "line_no": "", "description": "", "quantity": "",
                 "unit_price": "", "line_total": ""}]

    rows = []
    for n, item in enumerate(invoice.line_items, start=1):
        rows.append({
            **base,
            "line_no": str(n),
            "description": item.description,
            "quantity": _quantity(item.quantity),
            "unit_price": _money(item.unit_price),
            "line_total": _money(item.line_total),
        })
    return rows


def write_csv(invoices: Iterable[Invoice], stream: IO[str]) -> int:
    """Write all rows to an open text stream. Returns the number of rows."""
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    count = 0
    for invoice in invoices:
        for row in invoice_rows(invoice):
            writer.writerow(row)
            count += 1
    return count


def write_csv_file(invoices: Iterable[Invoice], path: Path) -> int:
    with path.open("w", encoding="utf-8", newline="") as handle:
        return write_csv(invoices, handle)
