"""Data shapes shared by the parser, the CSV writer and the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field

# Invoice-level fields the tool promises to try for. A field that is missing
# from this list is a nice-to-have; one that is in it and comes back empty
# flags the document for review.
REQUIRED_FIELDS = (
    "vendor",
    "invoice_number",
    "invoice_date",
    "subtotal",
    "total",
)


@dataclass
class LineItem:
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    line_total: float | None = None


@dataclass
class Invoice:
    source_file: str
    vendor: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None  # ISO yyyy-mm-dd
    currency: str | None = None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    line_items: list[LineItem] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def missing_fields(self) -> list[str]:
        return [f for f in REQUIRED_FIELDS if getattr(self, f) in (None, "")]

    @property
    def needs_review(self) -> bool:
        return bool(self.missing_fields or self.issues)
