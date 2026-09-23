"""CSV output: one renderer over the table defined in `table.py`.

`invoices.csv` is the file that pipes, diffs and imports. It holds the same
records as the workbook — see `xlsx_out.py` — because both are handed one
`Table` rather than each deriving rows of their own.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import IO

from .table import COLUMNS, Table

__all__ = ["COLUMNS", "write_csv", "write_csv_file"]


def write_csv(table: Table, stream: IO[str]) -> int:
    """Write the table to an open text stream. Returns the number of rows."""
    writer = csv.DictWriter(stream, fieldnames=table.columns, lineterminator="\n")
    writer.writeheader()
    for record in table.records:
        writer.writerow(record)
    return len(table)


def write_csv_file(table: Table, path: Path) -> int:
    with path.open("w", encoding="utf-8", newline="") as handle:
        return write_csv(table, handle)
