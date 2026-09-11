"""Layout-agnostic invoice parsing.

Everything in this module works on plain text, so it is testable without a PDF.
The rules are deliberately conservative: when a value cannot be read off the
page it stays ``None`` and the document is flagged. Nothing is inferred from a
value that is not printed on the document.
"""

from __future__ import annotations

import calendar
import re

from .models import Invoice, LineItem

# --------------------------------------------------------------------------
# numbers
# --------------------------------------------------------------------------

# A standalone numeric token: optional currency symbol, optional thousands
# separators, optional decimals. Parenthesised values are negative (accounting
# style). Percentages are matched so they can be explicitly skipped.
# The digit body is either comma-grouped or a plain run, never a mix, so that
# "12345.67" reads as one number rather than "123" followed by "45.67".
_NUMBER = r"[$£€]?-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
NUMBER_TOKEN_RE = re.compile(rf"^(?:\({_NUMBER}\)|{_NUMBER})$")
# Scanning mid-line needs a left boundary, otherwise the "88431" in "R-88431"
# would come back as a negative number.
NUMBER_SCAN_RE = re.compile(rf"(?<![\w.,\-])(?:\({_NUMBER}\)%?|{_NUMBER}%?)")

CURRENCY_SYMBOLS = {"$": "USD", "£": "GBP", "€": "EUR"}
CURRENCY_CODE_RE = re.compile(r"\b(USD|GBP|EUR|CAD|AUD|NZD|CHF|JPY|SEK|INR)\b")


def parse_number(token: str) -> float | None:
    """Parse a single numeric token. Returns None if the token is not a number."""
    token = token.strip()
    if not token or token.endswith("%"):
        return None
    if not NUMBER_TOKEN_RE.match(token):
        return None
    negative = token.startswith("(") and token.endswith(")")
    cleaned = token.strip("()").lstrip("$£€").replace(",", "")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def numbers_in(line: str) -> list[float]:
    """All numeric values on a line, in reading order. Percentages are skipped."""
    out = []
    for match in NUMBER_SCAN_RE.finditer(line):
        value = parse_number(match.group(0))
        if value is not None:
            out.append(value)
    return out


def trailing_run(line: str) -> tuple[list[str], list[float]]:
    """Split a line into (all tokens, the values of the trailing numeric run)."""
    tokens = line.split()
    values: list[float] = []
    for token in reversed(tokens):
        value = parse_number(token)
        if value is None:
            break
        values.insert(0, value)
    return tokens, values


def trailing_numbers(line: str) -> tuple[str, list[float]]:
    """Split a line into (leading text, trailing numeric tokens)."""
    tokens, values = trailing_run(line)
    keep = len(tokens) - len(values)
    return " ".join(tokens[:keep]), values


def detect_currency(*lines: str) -> str | None:
    for line in lines:
        code = CURRENCY_CODE_RE.search(line)
        if code:
            return code.group(1)
    for line in lines:
        for symbol, code in CURRENCY_SYMBOLS.items():
            if symbol in line:
                return code
    return None


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------

MONTHS = {name.lower(): n for n, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): n for n, name in enumerate(calendar.month_abbr) if name})

ISO_RE = re.compile(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b")
NUMERIC_RE = re.compile(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b")
MONTH_FIRST_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
DAY_FIRST_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?[-\s]([A-Za-z]{3,9})\.?,?[-\s](\d{4})\b")

DATE_LABELS = (
    "invoice date",
    "receipt date",
    "date of issue",
    "date issued",
    "issue date",
    "issued",
    "dated",
    "date",
)


def _valid(year: int, month: int, day: int) -> bool:
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        return False
    return day <= calendar.monthrange(year, month)[1]


def _iso(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_date(text: str, date_order: str = "mdy") -> tuple[str | None, bool]:
    """Find the first date in ``text``.

    Returns ``(iso_date, ambiguous)``. ``ambiguous`` is True when a numeric date
    could be read either day-first or month-first and ``date_order`` had to
    break the tie.
    """
    match = ISO_RE.search(text)
    if match:
        year, month, day = (int(g) for g in match.groups())
        if _valid(year, month, day):
            return _iso(year, month, day), False

    match = DAY_FIRST_RE.search(text)
    if match:
        day, name, year = int(match.group(1)), match.group(2).lower(), int(match.group(3))
        month = MONTHS.get(name)
        if month and _valid(year, month, day):
            return _iso(year, month, day), False

    match = MONTH_FIRST_RE.search(text)
    if match:
        name, day, year = match.group(1).lower(), int(match.group(2)), int(match.group(3))
        month = MONTHS.get(name)
        if month and _valid(year, month, day):
            return _iso(year, month, day), False

    match = NUMERIC_RE.search(text)
    if match:
        first, second, year = (int(g) for g in match.groups())
        if year < 100:
            year += 2000
        day_first = _valid(year, second, first)
        month_first = _valid(year, first, second)
        if day_first and not month_first:
            return _iso(year, second, first), False
        if month_first and not day_first:
            return _iso(year, first, second), False
        if day_first and month_first:
            if date_order == "dmy":
                return _iso(year, second, first), True
            return _iso(year, first, second), True
    return None, False


def find_date(lines: list[str], date_order: str) -> tuple[str | None, bool]:
    """Prefer a date sitting next to an explicit date label, else the first one."""
    for label in DATE_LABELS:
        pattern = re.compile(rf"\b{re.escape(label)}\b\s*:?\s*(.*)", re.IGNORECASE)
        for line in lines:
            match = pattern.search(line)
            if not match:
                continue
            found, ambiguous = parse_date(match.group(1), date_order)
            if found:
                return found, ambiguous
    for line in lines:
        found, ambiguous = parse_date(line, date_order)
        if found:
            return found, ambiguous
    return None, False


# --------------------------------------------------------------------------
# vendor
# --------------------------------------------------------------------------

DOC_TYPE_RE = re.compile(
    r"^(tax\s+)?(invoice|receipt|bill|statement|credit\s+note|pro\s*-?forma|quote|estimate)"
    r"\s*[:#]?\s*$",
    re.IGNORECASE,
)
VENDOR_PREFIX_RE = re.compile(
    r"^(from|bill\s+from|billed\s+by|sold\s+by|vendor|supplier|seller|remit\s+to)\b\s*[:\-]?\s*",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"^[\s()+\d.\-]{7,}$")
ADDRESS_HINT_RE = re.compile(
    r"\b(suite|unit|floor|p\.?o\.?\s*box|street|st\.|road|rd\.|avenue|ave\.|lane|way|"
    r"drive|dr\.|boulevard|blvd\.|works|plaza)\b",
    re.IGNORECASE,
)

VENDOR_SEARCH_LINES = 8


def find_vendor(lines: list[str]) -> str | None:
    """The vendor is the first line at the top of page 1 that reads like a name.

    Document-type headings, addresses, phone numbers and rule characters are
    skipped. A ``From:`` / ``Sold by:`` prefix is stripped when present.
    """
    for raw in lines[:VENDOR_SEARCH_LINES]:
        line = raw.strip()
        if not line or not re.search(r"[A-Za-z]", line):
            continue
        if DOC_TYPE_RE.match(line):
            continue
        prefixed = VENDOR_PREFIX_RE.match(line)
        if prefixed:
            candidate = line[prefixed.end() :].strip()
            if candidate:
                return candidate
            continue
        if PHONE_RE.match(line):
            continue
        # An address hint only counts alongside a number, so a business called
        # "Pike Street Deli" is not mistaken for a street address.
        has_digit = any(ch.isdigit() for ch in line)
        if line[0].isdigit() or (ADDRESS_HINT_RE.search(line) and has_digit):
            continue
        if numbers_in(line) and len(line.split()) <= 2:
            continue
        return line
    return None


# --------------------------------------------------------------------------
# invoice number
# --------------------------------------------------------------------------

INVOICE_NO_RE = re.compile(
    r"\b(?:invoice|receipt|bill|order|document|ref(?:erence)?)\s*"
    r"(?:number|no\.?|num\.?|nbr|#|id)\s*[:#]?\s*(.+)$",
    re.IGNORECASE,
)
HASH_RE = re.compile(r"(?:^|\s)#\s*(.+)$")
STOP_WORDS = {
    "dated",
    "date",
    "issued",
    "due",
    "page",
    "of",
    "to",
    "for",
    "on",
    "customer",
    "account",
    "terms",
}


def _clean_invoice_number(tail: str) -> str | None:
    """Take tokens that look like part of an identifier and stop at the next label."""
    kept: list[str] = []
    for token in tail.split():
        word = token.strip(",;:")
        if not word:
            break
        if word.lower() in STOP_WORDS:
            break
        has_digit = any(ch.isdigit() for ch in word)
        short_code = word.isupper() and word.isalpha() and len(word) <= 5
        if not (has_digit or short_code):
            break
        kept.append(word)
    identifier = " ".join(kept).strip(" .,-")
    return identifier or None


def find_invoice_number(lines: list[str]) -> str | None:
    for line in lines:
        match = INVOICE_NO_RE.search(line)
        if match:
            identifier = _clean_invoice_number(match.group(1))
            if identifier:
                return identifier
    for line in lines:
        match = HASH_RE.search(line)
        if match:
            identifier = _clean_invoice_number(match.group(1))
            if identifier:
                return identifier
    return None


# --------------------------------------------------------------------------
# totals
# --------------------------------------------------------------------------

SUBTOTAL_RE = re.compile(r"\b(sub[\s\-]?total|net\s+(?:amount|total|value)|net)\b", re.IGNORECASE)
TAX_RE = re.compile(r"\b(sales\s+tax|tax|v\.?a\.?t\.?|gst|hst|pst|levy)\b", re.IGNORECASE)
TOTAL_RE = re.compile(
    r"\b(total\s+due|amount\s+due|amount\s+payable|balance\s+due|grand\s+total|"
    r"total\s+payable|total\s+amount|invoice\s+total|total)\b",
    re.IGNORECASE,
)

# A totals row carries one amount (sometimes two, when a rate is printed beside
# it) and a short label. These bounds are what keeps a heading like
# "TAX INVOICE  Invoice No. FS/2024/1188  Dated 15/03/2024" out of the totals
# block, and keep a line item whose description happens to say "tax" out of it
# too.
MAX_TOTALS_NUMBERS = 2
MAX_TOTALS_LABEL_WORDS = 6


def classify_total_line(line: str) -> str | None:
    """Which totals row (if any) a line represents. Order matters: a line saying
    ``Subtotal`` also contains ``total``, so subtotal wins."""
    values = numbers_in(line)
    if not 1 <= len(values) <= MAX_TOTALS_NUMBERS:
        return None
    label, _ = trailing_numbers(line)
    if len(label.split()) > MAX_TOTALS_LABEL_WORDS:
        return None
    if SUBTOTAL_RE.search(label):
        return "subtotal"
    if TAX_RE.search(label):
        return "tax"
    if TOTAL_RE.search(label):
        return "total"
    return None


# --------------------------------------------------------------------------
# line items
# --------------------------------------------------------------------------

HEADER_WORDS = (
    "description",
    "item",
    "qty",
    "quantity",
    "unit price",
    "unit cost",
    "rate",
    "amount",
    "price",
    "line total",
    "total",
)
QTY_TIMES_UNIT_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*[x×*@]\s*[$£€]?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)$", re.IGNORECASE
)
MONEY_2DP_RE = re.compile(r"^[$£€]?\d{1,3}(?:,\d{3})*\.\d{2}$")


def is_header_line(line: str) -> bool:
    lowered = line.lower()
    hits = sum(1 for word in HEADER_WORDS if word in lowered)
    return hits >= 2 and not numbers_in(line)


def _close(actual: float, expected: float, quantity: float) -> bool:
    """Allow for a unit price that was rounded to 2dp on the page."""
    tolerance = max(0.02, 0.005 * abs(quantity))
    return abs(actual - expected) <= tolerance


def find_line_items(lines: list[str]) -> list[LineItem]:
    """Pull line items out of the body of the document.

    Two row shapes are recognised:

    * ``description ... qty unit_price amount`` on one line, accepted only when
      ``qty * unit_price`` agrees with ``amount``;
    * ``description ... amount`` followed by a ``qty x unit_price`` line, the
      shape receipts use, accepted under the same cross-check.

    Collection stops at the totals block.
    """
    items: list[LineItem] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line:
            continue
        if is_header_line(line):
            continue

        tokens, values = trailing_run(line)

        # Try the item shapes first. A row whose description happens to contain
        # a totals word ("Rush production surcharge 1 75.00 75.00") is an item,
        # not the end of the table.
        #
        # Only the last three numbers are columns. A description that itself
        # ends in a digit ("Pallet shipment leg 01, zone 2") keeps that digit.
        if len(values) >= 3:
            quantity, unit_price, amount = values[-3], values[-2], values[-1]
            description = " ".join(tokens[: len(tokens) - 3])
            if description and quantity and _close(amount, quantity * unit_price, quantity):
                items.append(LineItem(description, quantity, unit_price, amount))
                continue

        description = " ".join(tokens[: len(tokens) - len(values)])

        if classify_total_line(line):
            break
        if not description:
            continue

        if len(values) == 1 and index < len(lines):
            token = line.split()[-1]
            follow = QTY_TIMES_UNIT_RE.match(lines[index].strip())
            if follow and MONEY_2DP_RE.match(token):
                quantity = float(follow.group(1))
                unit_price = float(follow.group(2).replace(",", ""))
                if quantity and _close(values[0], quantity * unit_price, quantity):
                    items.append(LineItem(description, quantity, unit_price, values[0]))
                    index += 1
                    continue
    return items


# --------------------------------------------------------------------------
# top level
# --------------------------------------------------------------------------

PENNY = 0.02


def parse_invoice(text: str, source_file: str, date_order: str = "mdy") -> Invoice:
    """Parse the full text of one document into an :class:`Invoice`."""
    lines = [line.strip() for line in text.splitlines()]
    invoice = Invoice(source_file=source_file)

    invoice.vendor = find_vendor(lines)
    invoice.invoice_number = find_invoice_number(lines)
    invoice.invoice_date, ambiguous = find_date(lines, date_order)
    if ambiguous:
        invoice.issues.append(f"ambiguous date, read as {date_order}")

    total_lines: dict[str, str] = {}
    for line in lines:
        kind = classify_total_line(line)
        if kind and kind not in total_lines:
            total_lines[kind] = line
    for kind, line in total_lines.items():
        setattr(invoice, kind, numbers_in(line)[-1])

    invoice.currency = detect_currency(*total_lines.values(), *lines[:2])
    invoice.line_items = find_line_items(lines)

    _cross_check(invoice)
    return invoice


def _cross_check(invoice: Invoice) -> None:
    """Record disagreements between the numbers on the page. Never repairs them."""
    if not invoice.line_items:
        invoice.issues.append("no line items found")

    line_sum = sum(i.line_total for i in invoice.line_items if i.line_total is not None)
    if invoice.line_items and invoice.subtotal is not None:
        if abs(line_sum - invoice.subtotal) > PENNY:
            invoice.issues.append(
                f"line items sum to {line_sum:.2f} but subtotal reads {invoice.subtotal:.2f}"
            )

    if invoice.subtotal is not None and invoice.total is not None:
        if invoice.tax is None:
            if abs(invoice.total - invoice.subtotal) <= PENNY:
                invoice.tax = 0.0
            else:
                invoice.issues.append("no tax line found and subtotal does not equal total")
        elif abs(invoice.subtotal + invoice.tax - invoice.total) > PENNY:
            invoice.issues.append(
                f"subtotal + tax = {invoice.subtotal + invoice.tax:.2f} "
                f"but total reads {invoice.total:.2f}"
            )
