"""End-to-end: every sample PDF is checked against the values the generator used.

``tests/ground_truth.json`` is written by ``samples/generate_samples.py`` from
the same data it draws onto the page, so these tests compare the parser against
what is actually on the document rather than against itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdf_to_csv.pdf import collect_pdfs, parse_pdf

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "samples"
GROUND_TRUTH = json.loads((REPO_ROOT / "tests" / "ground_truth.json").read_text())
BY_FILE = {entry["source_file"]: entry for entry in GROUND_TRUTH}

# The one sample built without a total on the page. Everything else should come
# back clean.
EXPECTED_REVIEW = {"09_harborview_supplies_no_total.pdf"}


def approx(value, expected):
    return value is not None and abs(value - expected) < 0.005


@pytest.fixture(scope="module")
def parsed():
    return {p.name: parse_pdf(p) for p in collect_pdfs(SAMPLES)}


def test_every_sample_has_ground_truth(parsed):
    assert set(parsed) == set(BY_FILE)


@pytest.mark.parametrize("filename", sorted(BY_FILE))
class TestAgainstGroundTruth:
    def test_vendor(self, parsed, filename):
        # Case is not recoverable from a document that prints the name in caps.
        assert parsed[filename].vendor.casefold() == BY_FILE[filename]["vendor"].casefold()

    def test_invoice_number(self, parsed, filename):
        assert parsed[filename].invoice_number == BY_FILE[filename]["invoice_number"]

    def test_invoice_date(self, parsed, filename):
        assert parsed[filename].invoice_date == BY_FILE[filename]["invoice_date"]

    def test_subtotal(self, parsed, filename):
        assert approx(parsed[filename].subtotal, BY_FILE[filename]["subtotal"])

    def test_tax(self, parsed, filename):
        assert approx(parsed[filename].tax, BY_FILE[filename]["tax"])

    def test_total(self, parsed, filename):
        expected = BY_FILE[filename]["total"]
        if expected is None:
            assert parsed[filename].total is None
        else:
            assert approx(parsed[filename].total, expected)

    def test_line_items(self, parsed, filename):
        found = parsed[filename].line_items
        expected = BY_FILE[filename]["line_items"]
        assert len(found) == len(expected)
        for item, want in zip(found, expected, strict=True):
            assert item.description == want["description"]
            assert approx(item.quantity, want["quantity"])
            assert approx(item.unit_price, want["unit_price"])
            assert approx(item.line_total, want["line_total"])

    def test_review_flag(self, parsed, filename):
        assert parsed[filename].needs_review is (filename in EXPECTED_REVIEW)


def test_multi_page_invoice_keeps_every_row(parsed):
    invoice = parsed["06_cascade_freight_multipage.pdf"]
    assert len(invoice.line_items) == 42
    assert invoice.line_items[-1].description.endswith("leg 42, zone 3")


def test_the_draft_without_a_total_is_flagged_not_guessed(parsed):
    invoice = parsed["09_harborview_supplies_no_total.pdf"]
    assert invoice.total is None
    assert invoice.subtotal is not None
    assert "total" in invoice.missing_fields


def test_currencies(parsed):
    assert parsed["01_northwind_print.pdf"].currency == "USD"
    assert parsed["04_ferrier_hardware.pdf"].currency == "GBP"


def test_a_non_pdf_directory_entry_is_ignored(tmp_path):
    (tmp_path / "notes.txt").write_text("not a pdf")
    assert collect_pdfs(tmp_path) == []


def test_a_file_that_is_not_a_pdf_is_reported_not_raised(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a PDF")
    invoice = parse_pdf(broken)
    assert invoice.needs_review is True
    assert invoice.issues
