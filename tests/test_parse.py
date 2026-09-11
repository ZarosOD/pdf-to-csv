"""Unit tests for the parsing rules. No PDFs involved."""

from __future__ import annotations

import pytest

from pdf_to_csv.parse import (
    classify_total_line,
    detect_currency,
    find_date,
    find_invoice_number,
    find_line_items,
    find_vendor,
    is_header_line,
    numbers_in,
    parse_date,
    parse_invoice,
    parse_number,
    trailing_numbers,
)


class TestNumbers:
    @pytest.mark.parametrize(
        "token,expected",
        [
            ("1,234.56", 1234.56),
            ("$563.98", 563.98),
            ("£12.00", 12.0),
            ("0.86", 0.86),
            ("200", 200.0),
            ("(45.00)", -45.0),
            ("-45.00", -45.0),
            ("8.25%", None),
            ("INV-2024", None),
            ("", None),
            ("GBP", None),
        ],
    )
    def test_parse_number(self, token, expected):
        assert parse_number(token) == expected

    def test_long_digit_run_is_one_number(self):
        # A regex that allowed "1,234" and "12345" to blend would read this as
        # 123 followed by 45.67.
        assert numbers_in("Total 12345.67") == [12345.67]

    def test_digits_inside_an_identifier_are_not_amounts(self):
        # Without a left boundary this would read as the number -88431.
        assert numbers_in("Receipt No. R-88431") == []
        assert numbers_in("Invoice Number: INV-2024-0417") == []

    def test_a_standalone_negative_still_parses(self):
        assert numbers_in("Discount -45.00") == [-45.0]

    def test_percentages_are_skipped(self):
        assert numbers_in("Sales Tax (8.25%) 42.98") == [42.98]

    def test_trailing_numbers_stops_at_text(self):
        text, values = trailing_numbers("Galvanised bolt M10 (box of 50) 8 11.20 89.60")
        assert text == "Galvanised bolt M10 (box of 50)"
        assert values == [8.0, 11.20, 89.60]

    def test_trailing_numbers_when_line_ends_in_text(self):
        text, values = trailing_numbers("Amount Payable 260.16 GBP")
        assert values == []
        assert text == "Amount Payable 260.16 GBP"


class TestDates:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Invoice Date: 2024-03-15", "2024-03-15"),
            ("Date: 03/15/2024", "2024-03-15"),  # 15 cannot be a month
            ("Dated 15/03/2024", "2024-03-15"),  # 15 cannot be a month
            ("Issued March 15, 2024", "2024-03-15"),
            ("Issued 15-Mar-2024", "2024-03-15"),
            ("22-Mar-2024", "2024-03-22"),
            ("1 Jan 2025", "2025-01-01"),
            ("Sept 2024", None),
            ("no date here", None),
        ],
    )
    def test_unambiguous(self, text, expected):
        found, ambiguous = parse_date(text)
        assert found == expected
        assert ambiguous is False

    def test_ambiguous_uses_the_requested_order_and_says_so(self):
        assert parse_date("03/04/2024", "mdy") == ("2024-03-04", True)
        assert parse_date("03/04/2024", "dmy") == ("2024-04-03", True)

    def test_impossible_date_is_rejected(self):
        assert parse_date("Invoice Date: 2024-02-31")[0] is None

    def test_label_wins_over_position(self):
        lines = ["Due 2024-04-30", "Invoice Date: 2024-03-15"]
        assert find_date(lines, "mdy") == ("2024-03-15", False)

    def test_falls_back_to_first_date_when_unlabelled(self):
        assert find_date(["Acme Ltd", "2024-03-15"], "mdy") == ("2024-03-15", False)


class TestVendor:
    def test_skips_the_document_heading(self):
        assert find_vendor(["INVOICE", "Northwind Print Co.", "410 Kingfisher Way"]) == (
            "Northwind Print Co."
        )

    def test_strips_a_from_prefix(self):
        assert find_vendor(["Invoice", "From Orbit Cloud Services"]) == "Orbit Cloud Services"

    def test_skips_addresses_and_phone_numbers(self):
        lines = ["RECEIPT", "88 Harbor Lane", "(000) 555-0144", "Bayside Coffee"]
        assert find_vendor(lines) == "Bayside Coffee"

    def test_returns_none_when_there_is_nothing_name_like(self):
        assert find_vendor(["INVOICE", "-------", "12/03/2024"]) is None


class TestInvoiceNumber:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("Invoice Number: INV-2024-0417", "INV-2024-0417"),
            ("Receipt No. R-88431", "R-88431"),
            ("Invoice No. FS/2024/1188 Dated 15/03/2024", "FS/2024/1188"),
            ("# OCS-99120", "OCS-99120"),
            ("Invoice Number: MAP 24-0876", "MAP 24-0876"),
            ("Reference #: 0004-2291", "0004-2291"),
        ],
    )
    def test_shapes(self, line, expected):
        assert find_invoice_number([line]) == expected

    def test_missing(self):
        assert find_invoice_number(["Northwind Print Co.", "Subtotal 10.00"]) is None


class TestTotalsClassification:
    @pytest.mark.parametrize(
        "line,kind",
        [
            ("Subtotal 521.00", "subtotal"),
            ("SUBTOTAL 192.15", "subtotal"),
            ("Net Amount 216.80", "subtotal"),
            ("Sales Tax (8.25%) 42.98", "tax"),
            ("VAT @ 20% 43.36", "tax"),
            ("Fuel Surcharge Tax (6%) 498.64", "tax"),
            ("Total Due $563.98", "total"),
            ("Amount Payable 260.16 GBP", "total"),
            ("TOTAL $209.44", "total"),
        ],
    )
    def test_recognised(self, line, kind):
        assert classify_total_line(line) == kind

    @pytest.mark.parametrize(
        "line",
        [
            "TAX INVOICE Invoice No. FS/2024/1188 Dated 15/03/2024",
            "Rush production surcharge 1 75.00 75.00",
            "Description Qty Unit Price Amount",
            "Espresso blend 1kg",
        ],
    )
    def test_not_a_totals_row(self, line):
        assert classify_total_line(line) is None

    def test_subtotal_beats_total(self):
        # "Subtotal" contains "total"; the more specific label has to win.
        assert classify_total_line("Subtotal 100.00") == "subtotal"


class TestLineItems:
    def test_table_rows(self):
        lines = [
            "Description Qty Unit Price Amount",
            "Business cards, 16pt matte, 500ct 4 42.50 170.00",
            "Rush production surcharge 1 75.00 75.00",
            "Subtotal 245.00",
            "Total Due $245.00",
        ]
        items = find_line_items(lines)
        assert [i.description for i in items] == [
            "Business cards, 16pt matte, 500ct",
            "Rush production surcharge",
        ]
        assert items[0].quantity == 4
        assert items[0].unit_price == 42.50
        assert items[0].line_total == 170.00

    def test_receipt_continuation_rows(self):
        lines = [
            "Espresso blend 1kg 130.50",
            "6 x 21.75",
            "Filter papers box 16.80",
            "2 x 8.40",
            "SUBTOTAL 147.30",
        ]
        items = find_line_items(lines)
        assert len(items) == 2
        assert items[0].quantity == 6
        assert items[0].unit_price == 21.75
        assert items[0].line_total == 130.50

    def test_description_ending_in_a_digit_is_kept_whole(self):
        # Only the last three numbers are columns; "zone 2" belongs to the text.
        items = find_line_items(["Pallet shipment leg 01, zone 2 1 131.25 131.25"])
        assert items[0].description == "Pallet shipment leg 01, zone 2"
        assert items[0].quantity == 1
        assert items[0].unit_price == 131.25

    def test_rows_that_do_not_cross_check_are_not_accepted(self):
        # 4 x 42.50 is 170.00, not 999.00, so this is not a line item.
        assert find_line_items(["Some heading 4 42.50 999.00"]) == []

    def test_repeated_header_on_page_two_is_skipped(self):
        lines = [
            "Widget A 1 10.00 10.00",
            "Description Qty Unit Price Amount",
            "Widget B 2 5.00 10.00",
        ]
        assert [i.description for i in find_line_items(lines)] == ["Widget A", "Widget B"]

    def test_collection_stops_at_the_totals_block(self):
        lines = ["Widget A 1 10.00 10.00", "Subtotal 10.00", "Stray 2 3.00 6.00"]
        assert len(find_line_items(lines)) == 1

    def test_header_detection(self):
        assert is_header_line("Description Qty Unit Price Amount")
        assert not is_header_line("Widget A 1 10.00 10.00")


class TestCurrency:
    def test_symbol(self):
        assert detect_currency("Total Due $563.98") == "USD"

    def test_code_beats_symbol(self):
        assert detect_currency("Amount Payable 260.16 GBP") == "GBP"

    def test_absent(self):
        assert detect_currency("Total Due 563.98") is None


INVOICE_TEXT = """INVOICE
Northwind Print Co.
Invoice Number: INV-2024-0417
Invoice Date: 2024-03-15
Description Qty Unit Price Amount
Business cards, 16pt matte, 500ct 4 42.50 170.00
Rush production surcharge 1 75.00 75.00
Subtotal 245.00
Sales Tax (8%) 19.60
Total Due $264.60
"""


class TestParseInvoice:
    def test_end_to_end_on_text(self):
        invoice = parse_invoice(INVOICE_TEXT, "demo.pdf")
        assert invoice.vendor == "Northwind Print Co."
        assert invoice.invoice_number == "INV-2024-0417"
        assert invoice.invoice_date == "2024-03-15"
        assert invoice.subtotal == 245.00
        assert invoice.tax == 19.60
        assert invoice.total == 264.60
        assert invoice.currency == "USD"
        assert len(invoice.line_items) == 2
        assert invoice.needs_review is False

    def test_a_missing_field_is_empty_and_flagged_not_guessed(self):
        text = INVOICE_TEXT.replace("Total Due $264.60\n", "")
        invoice = parse_invoice(text, "demo.pdf")
        assert invoice.total is None
        assert invoice.needs_review is True
        assert "total" in invoice.missing_fields

    def test_totals_that_disagree_are_reported_not_corrected(self):
        text = INVOICE_TEXT.replace("Total Due $264.60", "Total Due $999.00")
        invoice = parse_invoice(text, "demo.pdf")
        assert invoice.total == 999.00  # what the page says, not what adds up
        assert invoice.needs_review is True
        assert any("subtotal + tax" in issue for issue in invoice.issues)

    def test_line_items_that_disagree_with_the_subtotal_are_reported(self):
        text = INVOICE_TEXT.replace("Subtotal 245.00", "Subtotal 300.00")
        invoice = parse_invoice(text, "demo.pdf")
        assert any("line items sum" in issue for issue in invoice.issues)

    def test_no_tax_line_and_subtotal_equal_to_total_means_zero_tax(self):
        text = INVOICE_TEXT.replace("Sales Tax (8%) 19.60\n", "").replace(
            "Total Due $264.60", "Total Due $245.00"
        )
        invoice = parse_invoice(text, "demo.pdf")
        assert invoice.tax == 0.0
        assert invoice.needs_review is False

    def test_empty_document(self):
        invoice = parse_invoice("", "empty.pdf")
        assert invoice.needs_review is True
        assert invoice.line_items == []
