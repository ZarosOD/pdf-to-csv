"""The rows, defined once — invoice-level fields with the line items under them.

One row per line item, the invoice-level fields repeated on each. That shape
drops straight into a spreadsheet pivot or a bookkeeping import without any
further reshaping, which is what the fields are usually wanted for. A document
with no line items still gets exactly one row so nothing disappears silently.

This module holds the definition and nothing else. `csv_out.py` renders it to
`invoices.csv` and `xlsx_out.py` renders it to `invoices.xlsx`: two writers
over one table, rather than two derivations with a test holding them level.
There is nothing for the CSV and the sheet to disagree about.

Values are the strings the CSV writes. The workbook turns the numeric columns
back into numbers on the way out — see `xlsx_out.NUMERIC_COLUMNS` — so the
conversion lives in the one place that needs it and the CSV stays the
authority on how a value is spelled.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class Table:
    """One output table: its header row and its records, defined once.

    `flagged` names the records a renderer should draw attention to — the rows
    of a document this tool would not vouch for. It is a property of the table
    (which rows are doubtful), not of the renderer, which is why it lives here
    and not in the xlsx code. The CSV says the same thing in its
    `needs_review` column; both read it off the same records.
    """

    name: str
    columns: list[str]
    records: list[dict[str, str]]
    flagged: frozenset[int] = field(default_factory=frozenset)

    def __len__(self) -> int:
        return len(self.records)

    def cells(self, record: dict[str, str]) -> list[str]:
        return [record.get(column, "") for column in self.columns]


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


def invoices_table(invoices: Iterable[Invoice]) -> Table:
    """Every document's rows, in the order they were parsed.

    The single callee. `extract.py` builds this once and hands the same object
    to both writers, so a column added here appears in the CSV and in the
    workbook in the same run, and a value cannot be formatted one way for one
    of them.
    """
    records: list[dict[str, str]] = []
    flagged: set[int] = set()
    for invoice in invoices:
        for row in invoice_rows(invoice):
            if row["needs_review"] == "yes":
                flagged.add(len(records))
            records.append(row)
    return Table("Invoices", list(COLUMNS), records, frozenset(flagged))
