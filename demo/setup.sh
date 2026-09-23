#!/usr/bin/env bash
# Project-specific preparation, run by every `make` target and by
# demo/record.sh before the recipe.
# EDIT THIS FILE for a new portfolio piece — but only these few lines: the
# venv/uv/ensurepip ladder is generic and lives in lib/python-venv.sh.
#
# It must be safe to run repeatedly and must leave the repo ready to record.
#
#   ./demo/setup.sh            prepare, and delete nothing a run produced
#   ./demo/setup.sh --fresh    also remove invoices.csv, for the recording only
#
# Every `make` target that needs a venv depends on `setup`, so plain setup.sh
# runs before `make run`, `make test` and `make samples`. It must therefore
# leave invoices.csv alone: `make run` writes it, and deleting it as a side
# effect of running the tests would throw away the output the user just asked
# for. Only record.sh passes --fresh.

set -euo pipefail

DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DEMO_DIR/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '  %s\n' "$*" >&2; }

FRESH=0
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
    *)
      echo "setup.sh: unknown argument '$arg' (the only option is --fresh)" >&2
      exit 2
      ;;
  esac
done

# Generic: creates .venv however this machine allows, then proves the install
# by importing what this project actually needs. See lib/python-venv.sh, which
# fetches a pinned uv via lib/uv.sh when there is none. pdfplumber and openpyxl
# are the runtime dependencies — a run writes invoices.csv and invoices.xlsx,
# and the clip's AFTER frame opens the workbook, so a venv without openpyxl
# cannot record. reportlab is what writes the synthetic samples.
# shellcheck source=lib/python-venv.sh
. "$DEMO_DIR/lib/python-venv.sh"
ensure_venv .venv "pdfplumber openpyxl reportlab"

PY=".venv/bin/python"

# The sample PDFs are committed, but regenerate them if the checkout lacks them.
if ! ls samples/*.pdf >/dev/null 2>&1; then
  log "generating synthetic samples"
  "$PY" samples/generate_samples.py >/dev/null
fi

# demo/.scratch is this demo's own workspace — the Playwright scene renders a
# sample page into it — so it goes on every run: nobody else writes there and
# nothing in it is anyone's output.
rm -rf demo/.scratch

# invoices.csv and invoices.xlsx belong to whoever last ran the tool. It
# matters to the recording because the scene opens the workbook as the AFTER
# frame, so a file left behind by an older run would be filmed as though this
# run produced it. Both go, not just the one on screen: leaving the CSV would
# leave half of what the command on screen claims to have written.
# --fresh is the recording saying "this scene must open on an empty repo", not
# a general-purpose clean; `make clean` is the one the reader can ask for by
# name.
if [ "$FRESH" = 1 ]; then
  log "removing invoices.csv and invoices.xlsx so the recorded run really is a first run"
  rm -f invoices.csv invoices.xlsx
fi
