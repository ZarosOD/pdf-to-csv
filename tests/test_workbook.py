"""invoices.xlsx: the same rows, in the file a client actually opens.

The thing worth testing is not that openpyxl can write a file. It is:

  * the workbook and the CSV cannot disagree — they are rendered from one
    `Table` rather than built twice, and these tests read both files back and
    compare them rather than comparing two builders;
  * the numbers are numbers, so a client can sum the total column, and they
    still print the decimals the CSV wrote;
  * the flagged documents are visible as flagged, which is the one thing the
    clip's closing frame promises;
  * two runs produce byte-identical bytes, so "run it again and nothing
    changed" is something `cmp` can answer.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from pdf_to_csv import xlsx_out
from pdf_to_csv.cli import main
from pdf_to_csv.csv_out import write_csv_file
from pdf_to_csv.models import Invoice, LineItem
from pdf_to_csv.table import invoices_table

openpyxl = pytest.importorskip("openpyxl")

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "samples"

CLEAN = Invoice(
    source_file="a.pdf",
    vendor="Acme Supplies",
    invoice_number="0042",
    invoice_date="2024-03-15",
    currency="USD",
    subtotal=1299.0,
    tax=0.0,
    total=1299.0,
    line_items=[LineItem("Toner", 2, 649.5, 1299.0)],
)
# No total, no line items: the document the tool will not vouch for.
FLAGGED = Invoice(source_file="b.pdf", vendor="Unknown Co.")


def build(tmp_path: Path, *invoices: Invoice) -> tuple[Path, Path]:
    table = invoices_table(invoices)
    csv_path, xlsx_path = tmp_path / "invoices.csv", tmp_path / "invoices.xlsx"
    write_csv_file(table, csv_path)
    xlsx_out.write_workbook(xlsx_path, table)
    return csv_path, xlsx_path


def sheet_of(path: Path):
    return openpyxl.load_workbook(path)[xlsx_out.SHEET_NAME]


def load_sheet_lib():
    """demo/lib/sheet.py, by path — it is a demo file, not an installed one."""
    import importlib.util

    path = REPO_ROOT / "demo" / "lib" / "sheet.py"
    spec = importlib.util.spec_from_file_location("demo_sheet_for_workbook", path)
    module = importlib.util.module_from_spec(spec)
    # Registered before it executes: @dataclass looks its own module up in
    # sys.modules while the class body is still being built.
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestOneDefinitionTwoRenderers:
    """The property that replaces a test asserting the two agree: there is one
    definition, so there is nothing to disagree."""

    def test_the_sheet_and_the_csv_hold_the_same_header(self, tmp_path):
        csv_path, xlsx_path = build(tmp_path, CLEAN, FLAGGED)
        from_csv = next(csv.reader(csv_path.open(encoding="utf-8")))
        from_sheet = [cell.value for cell in sheet_of(xlsx_path)[1]]
        assert from_csv == from_sheet

    def test_the_sheet_and_the_csv_hold_the_same_values(self, tmp_path):
        csv_path, xlsx_path = build(tmp_path, CLEAN, FLAGGED)
        from_csv = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        sheet = sheet_of(xlsx_path)
        header = [cell.value for cell in sheet[1]]
        for index, row in enumerate(sheet.iter_rows(min_row=2)):
            record = dict(zip(header, ["" if c.value is None else c.value for c in row]))
            for column, text in from_csv[index].items():
                # The sheet stores numbers as numbers; compare what each one
                # means, not how it is typed.
                if column in xlsx_out.NUMERIC_COLUMNS and text != "":
                    assert float(record[column]) == float(text), column
                else:
                    assert str(record[column]) == text, column

    def test_the_row_count_matches_the_csv(self, tmp_path):
        csv_path, xlsx_path = build(tmp_path, CLEAN, FLAGGED)
        rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
        assert sheet_of(xlsx_path).max_row == len(rows) + 1

    def test_the_whole_sample_folder_round_trips(self, tmp_path):
        """Not two hand-made invoices: the twelve the clip is recorded on."""
        assert main([str(SAMPLES), "-o", str(tmp_path / "invoices.csv")]) == 0
        rows = list(csv.DictReader((tmp_path / "invoices.csv").open(encoding="utf-8")))
        sheet = sheet_of(tmp_path / "invoices.xlsx")
        assert sheet.max_row == len(rows) + 1 == 77
        header = [cell.value for cell in sheet[1]]
        assert header == list(rows[0])


class TestWhatTheClientOpens:
    def test_money_is_a_number_you_can_sum(self, tmp_path):
        """A total stored as text is a total nobody can add up, which is most
        of why a client asked for Excel rather than the CSV."""
        _, xlsx_path = build(tmp_path, CLEAN)
        sheet = sheet_of(xlsx_path)
        header = [cell.value for cell in sheet[1]]
        total = sheet.cell(row=2, column=header.index("total") + 1)
        assert isinstance(total.value, (int, float))
        assert total.value == 1299.0

    def test_money_still_prints_its_two_decimals(self, tmp_path):
        """1299.0 with no format reads "1299" and invoices.csv says "1299.00".
        The value is the same; without the format the screen disagrees."""
        _, xlsx_path = build(tmp_path, CLEAN)
        sheet = sheet_of(xlsx_path)
        header = [cell.value for cell in sheet[1]]
        assert sheet.cell(row=2, column=header.index("total") + 1).number_format == "0.00"

    def test_quantity_is_a_number_but_keeps_no_forced_decimals(self, tmp_path):
        """The CSV writes `%g`, so a quantity of 2 is "2". Giving it the money
        format would print "2.00" and disagree with the file next to it."""
        _, xlsx_path = build(tmp_path, CLEAN)
        sheet = sheet_of(xlsx_path)
        header = [cell.value for cell in sheet[1]]
        cell = sheet.cell(row=2, column=header.index("quantity") + 1)
        assert cell.value == 2
        assert cell.number_format == "General"

    def test_an_identifier_stays_text(self, tmp_path):
        """"0042" is an invoice number, not the number 42. Excel eats the
        leading zero the moment anything decides otherwise."""
        _, xlsx_path = build(tmp_path, CLEAN)
        sheet = sheet_of(xlsx_path)
        header = [cell.value for cell in sheet[1]]
        assert sheet.cell(row=2, column=header.index("invoice_number") + 1).value == "0042"

    def test_flagged_rows_are_tinted_and_clean_rows_are_not(self, tmp_path):
        _, xlsx_path = build(tmp_path, CLEAN, FLAGGED)
        sheet = sheet_of(xlsx_path)
        clean_fill = sheet.cell(row=2, column=1).fill.start_color.rgb
        flagged_fill = sheet.cell(row=3, column=1).fill.start_color.rgb
        assert "FFF4D6" in str(flagged_fill)
        assert "FFF4D6" not in str(clean_fill)

    def test_the_header_row_stays_put_when_you_scroll(self, tmp_path):
        _, xlsx_path = build(tmp_path, CLEAN)
        assert sheet_of(xlsx_path).freeze_panes == "A2"

    def test_the_sheet_is_named_for_what_is_in_it(self, tmp_path):
        _, xlsx_path = build(tmp_path, CLEAN)
        assert openpyxl.load_workbook(xlsx_path).sheetnames == ["Invoices"]

    def test_an_empty_table_writes_a_readable_workbook(self, tmp_path):
        """Headers, no filter range. `A1:O1` as an auto-filter is a range with
        no rows in it, which some readers refuse to open."""
        xlsx_path = tmp_path / "empty.xlsx"
        xlsx_out.write_workbook(xlsx_path, invoices_table([]))
        sheet = sheet_of(xlsx_path)
        assert sheet.max_row == 1
        assert sheet.auto_filter.ref is None


class TestWhatTheClipShows:
    """The closing frame reads invoices.xlsx through demo/lib/sheet.py. What
    it puts on screen has to be what the CSV says, cell for cell — otherwise
    the clip is showing a spreadsheet that disagrees with the file the client
    downloads."""

    def test_the_workbook_renders_exactly_as_the_csv_does(self, tmp_path):
        sheet_lib = load_sheet_lib()
        assert main([str(SAMPLES), "-o", str(tmp_path / "invoices.csv")]) == 0
        from_xlsx = sheet_lib.read_table(tmp_path / "invoices.xlsx", "Invoices")
        from_csv = sheet_lib.read_table(tmp_path / "invoices.csv")
        assert from_xlsx.headers == from_csv.headers
        assert from_xlsx.rows == from_csv.rows

    def test_the_flagged_rows_are_findable_in_the_workbook(self, tmp_path):
        """Beat 4 tints the rows `needs_review` says are doubtful. An empty
        list there is a clip with nothing to point at."""
        sheet_lib = load_sheet_lib()
        assert main([str(SAMPLES), "-o", str(tmp_path / "invoices.csv")]) == 0
        rows = sheet_lib.read_table(tmp_path / "invoices.xlsx", "Invoices")
        assert sheet_lib.rows_where(rows, "needs_review", "yes") == [64, 65, 66]


def with_a_moved_clock(data: bytes) -> bytes:
    """The same workbook as a machine whose clock reads differently wrote it.

    Both clocks move: the zip member stamps and the Office document's own
    `dcterms` timestamps. This exists because writing the file twice inside
    one test proves nothing — both saves land in the same second, so the check
    passes whether or not anything was flattened. Moving the clock by hand is
    what makes the assertion load-bearing.
    """
    import zipfile

    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            body = source.read(item.filename)
            if item.filename == "docProps/core.xml":
                body = xlsx_out._TIMESTAMP.sub(
                    rb"\g<1>2031-07-04T11:22:33Z\g<2>", body
                )
            info = zipfile.ZipInfo(item.filename, date_time=(2031, 7, 4, 11, 22, 32))
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.create_system = 0
            target.writestr(info, body)
    return out.getvalue()


class TestReproducible:
    """Two runs over the same PDFs leave the same bytes, so `cmp` can stand in
    for "trust me". An .xlsx is a zip of timestamped members and an Office
    document with its own clock; both are flattened in `_repack`."""

    def test_a_run_on_a_different_clock_produces_the_same_bytes(self, tmp_path):
        """The real claim: what the file holds decides its bytes, and when it
        was written does not. Feeding `_repack` a copy with both clocks moved
        has to give back exactly what the tool wrote."""
        _, xlsx_path = build(tmp_path, CLEAN, FLAGGED)
        written = xlsx_path.read_bytes()
        assert xlsx_out._repack(with_a_moved_clock(written)) == written

    def test_two_runs_produce_identical_bytes(self, tmp_path):
        first = tmp_path / "first.xlsx"
        second = tmp_path / "second.xlsx"
        xlsx_out.write_workbook(first, invoices_table([CLEAN, FLAGGED]))
        xlsx_out.write_workbook(second, invoices_table([CLEAN, FLAGGED]))
        assert first.read_bytes() == second.read_bytes()

    def test_two_cli_runs_over_the_samples_produce_identical_bytes(self, tmp_path):
        """The check a client would actually perform, on the real input."""
        main([str(SAMPLES), "-o", str(tmp_path / "a.csv")])
        main([str(SAMPLES), "-o", str(tmp_path / "b.csv")])
        assert (tmp_path / "a.xlsx").read_bytes() == (tmp_path / "b.xlsx").read_bytes()
        assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()

    def test_the_document_clock_is_flattened_not_just_the_zip(self, tmp_path):
        """Two clocks, two fixes. Rewriting only the zip member timestamps
        would leave docProps/core.xml differing every run, and the file would
        still fail `cmp` while looking like it had been handled.

        Measured on openpyxl 3.1.5: `created` honours the workbook property
        and `modified` is refreshed to the save time regardless, so both
        timestamps are checked by name. Asserting the epoch appears *somewhere*
        in core.xml passes on `created` alone while `modified` still moves.
        """
        import re
        import zipfile

        _, xlsx_path = build(tmp_path, CLEAN)
        with zipfile.ZipFile(xlsx_path) as book:
            core = book.read("docProps/core.xml").decode("utf-8")
            stamps = dict(re.findall(r"<dcterms:(created|modified)[^>]*>([^<]*)<", core))
            assert stamps == {
                "created": "1980-01-01T00:00:00Z",
                "modified": "1980-01-01T00:00:00Z",
            }
            assert all(item.date_time == (1980, 1, 1, 0, 0, 0) for item in book.infolist())
