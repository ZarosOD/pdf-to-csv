"""Print a few CSV columns as a fixed-width table, for the demo recording.

Recipe-layer helper: change or delete it for another portfolio piece.
Usage: python demo/preview.py invoices.csv vendor invoice_number total
"""

from __future__ import annotations

import csv
import sys

MAX_ROWS = 6
MAX_CELL = 34


def main() -> int:
    path, *columns = sys.argv[1:]
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    # The CSV repeats the invoice-level fields on every line item, so a view of
    # only those columns would show the same row several times over.
    selected: list[list[str]] = []
    for row in rows:
        cells = [(row.get(c) or "")[:MAX_CELL] for c in columns]
        if not selected or cells != selected[-1]:
            selected.append(cells)
        if len(selected) == MAX_ROWS:
            break

    table = [columns] + selected
    widths = [max(len(r[i]) for r in table) for i in range(len(columns))]

    for n, row in enumerate(table):
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip())
        if n == 0:
            print("  ".join("-" * w for w in widths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
