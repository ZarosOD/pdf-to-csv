#!/usr/bin/env bash
# Project-specific preparation, run by demo/record.sh before the tape plays.
# EDIT THIS FILE for a new portfolio piece: it is the only place that knows
# the project is Python.
#
# It must be safe to run repeatedly and must leave the repo ready for the tape.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

VENV=".venv"
PY="$VENV/bin/python"

log() { printf '  %s\n' "$*" >&2; }

if [ ! -x "$PY" ]; then
  if command -v uv >/dev/null 2>&1; then
    log "creating $VENV with uv"
    uv venv --python 3.12 "$VENV" >/dev/null
    VIRTUAL_ENV="$REPO_ROOT/$VENV" uv pip install --quiet -e '.[dev]'
  elif python3 -m venv --help >/dev/null 2>&1 && python3 -c 'import ensurepip' 2>/dev/null; then
    log "creating $VENV with python -m venv"
    python3 -m venv "$VENV"
    "$PY" -m pip install --quiet --upgrade pip
    "$PY" -m pip install --quiet -e '.[dev]'
  else
    echo "setup.sh: need either uv (https://astral.sh/uv) or a python3 with ensurepip" >&2
    exit 1
  fi
fi

if ! "$PY" -c 'import pdfplumber' 2>/dev/null; then
  echo "setup.sh: $VENV exists but pdfplumber is missing; delete $VENV and re-run" >&2
  exit 1
fi

# The sample PDFs are committed, but regenerate them if the checkout lacks them.
if ! ls samples/*.pdf >/dev/null 2>&1; then
  log "generating synthetic samples"
  "$PY" samples/generate_samples.py >/dev/null
fi

# Nothing from a previous run should appear in the recording.
rm -f invoices.csv
