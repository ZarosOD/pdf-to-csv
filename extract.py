#!/usr/bin/env python3
"""Thin wrapper so the tool runs as `python extract.py ...` from the repo root."""

import sys

from pdf_to_csv.cli import main

if __name__ == "__main__":
    sys.exit(main())
