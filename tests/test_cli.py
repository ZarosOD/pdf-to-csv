"""CLI behaviour: CSV shape, the --report line, exit codes."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from pdf_to_csv.cli import main, summarise
from pdf_to_csv.csv_out import COLUMNS, invoice_rows, write_csv
from pdf_to_csv.models import Invoice, LineItem

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "samples"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class TestCsvShape:
    def test_one_row_per_line_item_with_invoice_fields_repeated(self):
        invoice = Invoice(
            source_file="a.pdf",
            vendor="Acme",
            invoice_number="1",
            invoice_date="2024-03-15",
            subtotal=30.0,
            tax=0.0,
            total=30.0,
            line_items=[LineItem("X", 1, 10.0, 10.0), LineItem("Y", 2, 10.0, 20.0)],
        )
        rows = invoice_rows(invoice)
        assert [r["line_no"] for r in rows] == ["1", "2"]
        assert {r["vendor"] for r in rows} == {"Acme"}
        assert {r["total"] for r in rows} == {"30.00"}

    def test_a_document_with_no_line_items_still_produces_one_row(self):
        rows = invoice_rows(Invoice(source_file="a.pdf", vendor="Acme"))
        assert len(rows) == 1
        assert rows[0]["description"] == ""
        assert rows[0]["needs_review"] == "yes"

    def test_missing_values_are_empty_strings_never_zero(self):
        rows = invoice_rows(Invoice(source_file="a.pdf"))
        assert rows[0]["total"] == ""
        assert rows[0]["subtotal"] == ""
        assert "missing:" in rows[0]["issues"]

    def test_header_is_written_once(self):
        stream = io.StringIO()
        count = write_csv([Invoice(source_file="a.pdf"), Invoice(source_file="b.pdf")], stream)
        lines = stream.getvalue().strip().splitlines()
        assert lines[0] == ",".join(COLUMNS)
        assert count == 2
        assert len(lines) == 3


class TestSummary:
    def test_counts(self):
        clean = Invoice(
            source_file="a.pdf",
            vendor="A",
            invoice_number="1",
            invoice_date="2024-01-01",
            subtotal=1.0,
            tax=0.0,
            total=1.0,
            line_items=[LineItem("X", 1, 1.0, 1.0)],
        )
        assert summarise([clean, Invoice(source_file="b.pdf")]) == (
            "2 files, 1 parsed clean, 1 needing review"
        )


class TestMain:
    def test_runs_over_the_sample_folder(self, tmp_path, capsys):
        out = tmp_path / "out.csv"
        assert main([str(SAMPLES), "-o", str(out), "--report"]) == 0
        report = capsys.readouterr().out
        assert "12 files, 11 parsed clean, 1 needing review" in report

        rows = read_csv(out)
        assert len(rows) == 76  # every line item across the 12 documents, none dropped
        assert {r["source_file"] for r in rows} == {p.name for p in SAMPLES.glob("*.pdf")}
        flagged = {r["source_file"] for r in rows if r["needs_review"] == "yes"}
        assert flagged == {"09_harborview_supplies_no_total.pdf"}

    def test_single_file(self, tmp_path):
        out = tmp_path / "out.csv"
        assert main([str(SAMPLES / "01_northwind_print.pdf"), "-o", str(out)]) == 0
        rows = read_csv(out)
        assert len(rows) == 3
        assert rows[0]["vendor"] == "Northwind Print Co."
        assert rows[0]["invoice_date"] == "2024-03-15"
        assert rows[0]["total"] == "563.98"

    def test_writes_to_stdout_when_no_output_given(self, capsys):
        assert main([str(SAMPLES / "01_northwind_print.pdf")]) == 0
        assert "Northwind Print Co." in capsys.readouterr().out

    def test_report_goes_to_stderr_when_csv_goes_to_stdout(self, capsys):
        main([str(SAMPLES / "01_northwind_print.pdf"), "--report"])
        captured = capsys.readouterr()
        assert "1 files, 1 parsed clean" in captured.err
        assert "1 files, 1 parsed clean" not in captured.out

    def test_fail_on_review_exit_code(self, tmp_path):
        out = tmp_path / "out.csv"
        assert main([str(SAMPLES), "-o", str(out), "--fail-on-review"]) == 1
        clean = SAMPLES / "01_northwind_print.pdf"
        assert main([str(clean), "-o", str(out), "--fail-on-review"]) == 0

    def test_missing_input_exits_2(self, tmp_path, capsys):
        assert main([str(tmp_path / "nope")]) == 2
        assert "no such file" in capsys.readouterr().err

    def test_empty_directory_exits_2(self, tmp_path, capsys):
        assert main([str(tmp_path)]) == 2
        assert "no PDFs found" in capsys.readouterr().err

    def test_date_order_switch(self, tmp_path):
        out = tmp_path / "out.csv"
        # Every sample date is unambiguous, so the switch must not change them.
        main([str(SAMPLES), "-o", str(out), "--date-order", "dmy"])
        dmy = {r["source_file"]: r["invoice_date"] for r in read_csv(out)}
        main([str(SAMPLES), "-o", str(out), "--date-order", "mdy"])
        mdy = {r["source_file"]: r["invoice_date"] for r in read_csv(out)}
        assert dmy == mdy
