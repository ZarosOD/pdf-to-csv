"""Generate the synthetic sample invoices used by the demo and the tests.

Everything here is invented. No real vendor, customer, address, or amount appears
in this file or in anything it produces.

Run:  python samples/generate_samples.py
Writes: samples/*.pdf  and  tests/ground_truth.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

SAMPLES_DIR = Path(__file__).resolve().parent
REPO_ROOT = SAMPLES_DIR.parent
GROUND_TRUTH = REPO_ROOT / "tests" / "ground_truth.json"

PAGE_W, PAGE_H = letter


@dataclass
class Item:
    description: str
    qty: float
    unit_price: float

    @property
    def amount(self) -> float:
        return round(self.qty * self.unit_price, 2)


@dataclass
class Invoice:
    filename: str
    layout: str
    vendor: str
    invoice_number: str
    date_text: str
    date_iso: str
    items: list[Item]
    tax_rate: float = 0.0
    tax_label: str = "Tax"
    currency: str = "USD"
    omit_total: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def subtotal(self) -> float:
        return round(sum(i.amount for i in self.items), 2)

    @property
    def tax(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)


def money(v: float) -> str:
    return f"{v:,.2f}"


# --------------------------------------------------------------------------
# Layout A: classic ruled table, right-aligned totals block
# --------------------------------------------------------------------------
def draw_classic(c: canvas.Canvas, inv: Invoice) -> None:
    y = PAGE_H - 0.9 * inch
    c.setFont("Helvetica-Bold", 17)
    c.drawString(0.9 * inch, y, inv.vendor)
    c.setFont("Helvetica", 9)
    c.drawString(0.9 * inch, y - 14, "410 Kingfisher Way, Suite 20")
    c.drawString(0.9 * inch, y - 26, "Port Meridian, ZZ 00042")

    c.setFont("Helvetica-Bold", 26)
    c.drawRightString(PAGE_W - 0.9 * inch, y, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(PAGE_W - 0.9 * inch, y - 20, f"Invoice Number: {inv.invoice_number}")
    c.drawRightString(PAGE_W - 0.9 * inch, y - 34, f"Invoice Date: {inv.date_text}")

    y -= 72
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.9 * inch, y, "BILL TO")
    c.setFont("Helvetica", 9)
    c.drawString(0.9 * inch, y - 13, "Quill Demo Holdings")
    c.drawString(0.9 * inch, y - 25, "1 Example Plaza, Sample City")

    y = _classic_table(c, inv, y - 55)
    _classic_totals(c, inv, y - 18)
    _footer(c, inv)


def _classic_table(c: canvas.Canvas, inv: Invoice, y: float) -> float:
    left = 0.9 * inch
    right = PAGE_W - 0.9 * inch
    cols = (left, right - 230, right - 150, right)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(cols[0], y, "Description")
    c.drawRightString(cols[1], y, "Qty")
    c.drawRightString(cols[2], y, "Unit Price")
    c.drawRightString(cols[3], y, "Amount")
    c.setLineWidth(0.6)
    c.line(left, y - 5, right, y - 5)

    c.setFont("Helvetica", 9)
    y -= 20
    for item in inv.items:
        if y < 2.2 * inch:
            c.showPage()
            y = PAGE_H - 1.0 * inch
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left, y, "Description")
            c.drawRightString(cols[1], y, "Qty")
            c.drawRightString(cols[2], y, "Unit Price")
            c.drawRightString(cols[3], y, "Amount")
            c.line(left, y - 5, right, y - 5)
            c.setFont("Helvetica", 9)
            y -= 20
        c.drawString(cols[0], y, item.description)
        c.drawRightString(cols[1], y, f"{item.qty:g}")
        c.drawRightString(cols[2], y, money(item.unit_price))
        c.drawRightString(cols[3], y, money(item.amount))
        y -= 15
    c.line(left, y + 6, right, y + 6)
    return y


def _classic_totals(c: canvas.Canvas, inv: Invoice, y: float) -> None:
    right = PAGE_W - 0.9 * inch
    c.setFont("Helvetica", 10)
    c.drawRightString(right - 90, y, "Subtotal")
    c.drawRightString(right, y, money(inv.subtotal))
    if inv.tax_rate:
        y -= 15
        c.drawRightString(right - 90, y, f"{inv.tax_label} ({inv.tax_rate * 100:g}%)")
        c.drawRightString(right, y, money(inv.tax))
    if not inv.omit_total:
        y -= 19
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(right - 90, y, "Total Due")
        c.drawRightString(right, y, f"${money(inv.total)}")


def _footer(c: canvas.Canvas, inv: Invoice) -> None:
    c.setFont("Helvetica-Oblique", 8)
    for n, note in enumerate(inv.notes):
        c.drawString(0.9 * inch, 0.85 * inch + n * 11, note)


# --------------------------------------------------------------------------
# Layout B: narrow thermal-style receipt, centered, no table rules
# --------------------------------------------------------------------------
def draw_receipt(c: canvas.Canvas, inv: Invoice) -> None:
    mid = PAGE_W / 2
    y = PAGE_H - 1.1 * inch
    c.setFont("Courier-Bold", 13)
    c.drawCentredString(mid, y, inv.vendor.upper())
    c.setFont("Courier", 8)
    y -= 14
    c.drawCentredString(mid, y, "88 Harbor Lane  ~  Port Meridian")
    y -= 11
    c.drawCentredString(mid, y, "(000) 555-0144")
    y -= 22
    c.setFont("Courier", 9)
    c.drawCentredString(mid, y, "-" * 44)
    y -= 14
    c.drawString(mid - 140, y, f"Receipt No. {inv.invoice_number}")
    y -= 12
    c.drawString(mid - 140, y, f"Date: {inv.date_text}")
    y -= 12
    c.drawCentredString(mid, y, "-" * 44)
    y -= 18

    for item in inv.items:
        c.drawString(mid - 140, y, item.description[:26])
        c.drawRightString(mid + 140, y, money(item.amount))
        y -= 11
        c.setFont("Courier-Oblique", 8)
        c.drawString(mid - 132, y, f"{item.qty:g} x {money(item.unit_price)}")
        c.setFont("Courier", 9)
        y -= 15

    c.drawCentredString(mid, y, "-" * 44)
    y -= 16
    c.drawString(mid - 140, y, "SUBTOTAL")
    c.drawRightString(mid + 140, y, money(inv.subtotal))
    y -= 13
    c.drawString(mid - 140, y, f"{inv.tax_label.upper()}")
    c.drawRightString(mid + 140, y, money(inv.tax))
    y -= 16
    c.setFont("Courier-Bold", 10)
    c.drawString(mid - 140, y, "TOTAL")
    c.drawRightString(mid + 140, y, f"${money(inv.total)}")
    y -= 26
    c.setFont("Courier", 8)
    c.drawCentredString(mid, y, "THANK YOU FOR YOUR BUSINESS")


# --------------------------------------------------------------------------
# Layout C: two-column "statement" style with VAT wording
# --------------------------------------------------------------------------
def draw_statement(c: canvas.Canvas, inv: Invoice) -> None:
    left = 0.85 * inch
    right = PAGE_W - 0.85 * inch
    y = PAGE_H - 1.0 * inch

    c.setFont("Helvetica-Bold", 20)
    c.drawString(left, y, inv.vendor)
    c.setFont("Helvetica", 9)
    y -= 16
    c.drawString(left, y, "Unit 6, Stonebridge Works, Sample City")
    y -= 30

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "TAX INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(left + 150, y, f"Invoice No. {inv.invoice_number}")
    c.drawRightString(right, y, f"Dated {inv.date_text}")
    y -= 8
    c.setLineWidth(1.1)
    c.line(left, y, right, y)
    y -= 24

    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Item")
    c.drawString(left + 260, y, "Quantity")
    c.drawString(left + 330, y, "Rate")
    c.drawRightString(right, y, "Line Total")
    y -= 16
    c.setFont("Helvetica", 9)
    for item in inv.items:
        c.drawString(left, y, item.description)
        c.drawString(left + 260, y, f"{item.qty:g}")
        c.drawString(left + 330, y, money(item.unit_price))
        c.drawRightString(right, y, money(item.amount))
        y -= 14

    y -= 12
    c.setLineWidth(0.5)
    c.line(left + 300, y, right, y)
    y -= 16
    c.setFont("Helvetica", 10)
    c.drawString(left + 300, y, "Net Amount")
    c.drawRightString(right, y, money(inv.subtotal))
    y -= 14
    c.drawString(left + 300, y, f"{inv.tax_label} @ {inv.tax_rate * 100:g}%")
    c.drawRightString(right, y, money(inv.tax))
    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left + 300, y, "Amount Payable")
    c.drawRightString(right, y, f"{money(inv.total)} {inv.currency}")
    _footer(c, inv)


# --------------------------------------------------------------------------
# Layout D: modern minimal, big numbers, no rules
# --------------------------------------------------------------------------
def draw_modern(c: canvas.Canvas, inv: Invoice) -> None:
    left = 1.1 * inch
    right = PAGE_W - 1.1 * inch
    y = PAGE_H - 1.3 * inch

    c.setFont("Helvetica-Bold", 30)
    c.drawString(left, y, "Invoice")
    y -= 34
    c.setFont("Helvetica", 11)
    c.drawString(left, y, f"From  {inv.vendor}")
    y -= 15
    c.drawString(left, y, f"#  {inv.invoice_number}")
    y -= 15
    c.drawString(left, y, f"Issued  {inv.date_text}")

    y -= 46
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "DESCRIPTION")
    c.drawRightString(right - 170, y, "QTY")
    c.drawRightString(right - 85, y, "RATE")
    c.drawRightString(right, y, "TOTAL")
    y -= 20
    c.setFont("Helvetica", 10)
    for item in inv.items:
        c.drawString(left, y, item.description)
        c.drawRightString(right - 170, y, f"{item.qty:g}")
        c.drawRightString(right - 85, y, money(item.unit_price))
        c.drawRightString(right, y, money(item.amount))
        y -= 18

    y -= 20
    c.setFont("Helvetica", 10)
    c.drawRightString(right - 85, y, "Subtotal")
    c.drawRightString(right, y, money(inv.subtotal))
    if inv.tax_rate:
        y -= 16
        c.drawRightString(right - 85, y, inv.tax_label)
        c.drawRightString(right, y, money(inv.tax))
    y -= 24
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(right - 85, y, "Amount Due")
    c.drawRightString(right, y, f"${money(inv.total)}")
    _footer(c, inv)


LAYOUTS = {
    "classic": draw_classic,
    "receipt": draw_receipt,
    "statement": draw_statement,
    "modern": draw_modern,
}


# --------------------------------------------------------------------------
# The sample set. Fixed, not random, so tests can assert exact values.
# --------------------------------------------------------------------------
def build_invoices() -> list[Invoice]:
    return [
        Invoice(
            filename="01_northwind_print.pdf",
            layout="classic",
            vendor="Northwind Print Co.",
            invoice_number="INV-2024-0417",
            date_text="2024-03-15",
            date_iso="2024-03-15",
            tax_rate=0.0825,
            tax_label="Sales Tax",
            items=[
                Item("Business cards, 16pt matte, 500ct", 4, 42.50),
                Item("Tri-fold brochure, gloss, 250ct", 2, 138.00),
                Item("Rush production surcharge", 1, 75.00),
            ],
            notes=["Payment due within 30 days. Synthetic sample document."],
        ),
        Invoice(
            filename="02_bayside_coffee.pdf",
            layout="receipt",
            vendor="Bayside Coffee Roasters",
            invoice_number="R-88431",
            date_text="03/15/2024",
            date_iso="2024-03-15",
            tax_rate=0.09,
            tax_label="Tax",
            items=[
                Item("Espresso blend 1kg", 6, 21.75),
                Item("Filter papers box", 2, 8.40),
                Item("Cold brew concentrate", 3, 14.95),
            ],
        ),
        Invoice(
            filename="03_orbit_cloud.pdf",
            layout="modern",
            vendor="Orbit Cloud Services",
            invoice_number="OCS-99120",
            date_text="March 15, 2024",
            date_iso="2024-03-15",
            tax_rate=0.0,
            tax_label="Tax",
            items=[
                Item("Compute hours, standard tier", 720, 0.09),
                Item("Object storage, TB-month", 3.5, 19.00),
                Item("Support plan, monthly", 1, 99.00),
            ],
            notes=["Auto-renewing subscription. Synthetic sample document."],
        ),
        Invoice(
            filename="04_ferrier_hardware.pdf",
            layout="statement",
            vendor="Ferrier & Sons Hardware",
            invoice_number="FS/2024/1188",
            date_text="15/03/2024",
            date_iso="2024-03-15",
            tax_rate=0.20,
            tax_label="VAT",
            currency="GBP",
            items=[
                Item("Galvanised bolt M10 (box of 50)", 8, 11.20),
                Item("Heavy duty hinge, 150mm", 12, 6.75),
                Item("Threadlock compound 50ml", 3, 9.40),
                Item("Delivery", 1, 18.00),
            ],
        ),
        Invoice(
            filename="05_lumen_design.pdf",
            layout="modern",
            vendor="Lumen Design Studio",
            invoice_number="2024-041",
            date_text="15-Mar-2024",
            date_iso="2024-03-15",
            tax_rate=0.0,
            tax_label="Tax",
            items=[
                Item("Brand identity workshop", 1, 1800.00),
                Item("Logo concepts, 3 routes", 3, 450.00),
                Item("Style guide production", 1, 950.00),
            ],
        ),
        Invoice(
            filename="06_cascade_freight_multipage.pdf",
            layout="classic",
            vendor="Cascade Freight LLC",
            invoice_number="CF-2024-77310",
            date_text="2024-03-18",
            date_iso="2024-03-18",
            tax_rate=0.06,
            tax_label="Fuel Surcharge Tax",
            items=[
                Item(f"Pallet shipment leg {n:02d}, zone {1 + n % 5}", 1, 128.00 + n * 3.25)
                for n in range(1, 43)
            ],
            notes=["Multi-page sample. Synthetic document."],
        ),
        Invoice(
            filename="07_pike_street_deli.pdf",
            layout="receipt",
            vendor="Pike Street Deli",
            invoice_number="0004-2291",
            date_text="18/03/2024",
            date_iso="2024-03-18",
            tax_rate=0.101,
            tax_label="Tax",
            items=[
                Item("Catering tray, sandwiches", 2, 64.00),
                Item("Side salad, large", 4, 18.50),
                Item("Beverage service", 1, 42.00),
            ],
        ),
        Invoice(
            filename="08_vector_analytics.pdf",
            layout="statement",
            vendor="Vector Analytics Ltd",
            invoice_number="VA-0031-24",
            date_text="20/03/2024",
            date_iso="2024-03-20",
            tax_rate=0.20,
            tax_label="VAT",
            currency="GBP",
            items=[
                Item("Data pipeline audit", 1, 2400.00),
                Item("Dashboard build, per screen", 5, 380.00),
                Item("Handover session", 2, 220.00),
            ],
        ),
        Invoice(
            filename="09_harborview_supplies_no_total.pdf",
            layout="classic",
            vendor="Harborview Supplies",
            invoice_number="HV-5521",
            date_text="2024-03-21",
            date_iso="2024-03-21",
            tax_rate=0.07,
            tax_label="Sales Tax",
            omit_total=True,
            items=[
                Item("Packing tape, 48mm (case)", 5, 27.60),
                Item("Stretch wrap roll", 10, 14.25),
                Item("Corrugated mailer, medium", 200, 0.86),
            ],
            notes=["DRAFT - total pending approval. Synthetic sample document."],
        ),
        Invoice(
            filename="10_meridian_auto_parts.pdf",
            layout="classic",
            vendor="Meridian Auto Parts",
            invoice_number="MAP 24-0876",
            date_text="March 22, 2024",
            date_iso="2024-03-22",
            tax_rate=0.0875,
            tax_label="Sales Tax",
            items=[
                Item("Brake pad set, front", 2, 88.40),
                Item("Oil filter", 6, 12.15),
                Item("Synthetic oil 5W-30, 5qt", 4, 34.90),
                Item("Shop supplies", 1, 15.00),
            ],
        ),
        Invoice(
            filename="11_stonebridge_courier.pdf",
            layout="modern",
            vendor="Stonebridge Courier Network",
            invoice_number="SCN/24/0455",
            date_text="22-Mar-2024",
            date_iso="2024-03-22",
            tax_rate=0.05,
            tax_label="Service Tax",
            items=[
                Item("Same-day delivery, metro", 14, 22.00),
                Item("Oversize parcel handling", 3, 17.50),
            ],
        ),
        Invoice(
            filename="12_greywater_utilities.pdf",
            layout="statement",
            vendor="Greywater Utilities Board",
            invoice_number="GU-2024-003914",
            date_text="25/03/2024",
            date_iso="2024-03-25",
            tax_rate=0.125,
            tax_label="Levy",
            items=[
                Item("Metered supply, 000 litres", 138, 1.42),
                Item("Standing charge, quarterly", 1, 46.00),
                Item("Wastewater treatment", 138, 0.98),
            ],
        ),
    ]


def render(inv: Invoice, out_dir: Path) -> Path:
    path = out_dir / inv.filename
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle(f"{inv.vendor} {inv.invoice_number}")
    c.setAuthor("pdf-to-csv synthetic sample generator")
    LAYOUTS[inv.layout](c, inv)
    c.save()
    return path


def ground_truth(inv: Invoice) -> dict:
    return {
        "source_file": inv.filename,
        "layout": inv.layout,
        "vendor": inv.vendor,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.date_iso,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total": None if inv.omit_total else inv.total,
        "line_items": [
            {
                "description": i.description,
                "quantity": i.qty,
                "unit_price": i.unit_price,
                "line_total": i.amount,
            }
            for i in inv.items
        ],
    }


def main() -> None:
    invoices = build_invoices()
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH.parent.mkdir(parents=True, exist_ok=True)

    for inv in invoices:
        path = render(inv, SAMPLES_DIR)
        print(f"wrote {path.relative_to(REPO_ROOT)}")

    GROUND_TRUTH.write_text(
        json.dumps([ground_truth(i) for i in invoices], indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {GROUND_TRUTH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
