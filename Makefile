PY := .venv/bin/python

.PHONY: help setup run test samples demo demo-terminal clean

help:
	@echo "make setup    create .venv and install"
	@echo "make run      extract samples/ into invoices.csv and invoices.xlsx"
	@echo "make test     run the test suite"
	@echo "make samples  regenerate the synthetic sample PDFs"
	@echo "make demo     regenerate demo/out/demo.gif with Playwright, headless"
	@echo "make demo-terminal  the same story recorded with VHS instead"

setup:
	@./demo/setup.sh

run: setup
	$(PY) extract.py samples/ -o invoices.csv --report

test: setup
	$(PY) -m pytest -q

samples: setup
	$(PY) samples/generate_samples.py

demo:
	@./demo/record.sh

demo-terminal:
	@DEMO_RECIPE=vhs DEMO_OUT_DIR=demo/out-terminal ./demo/record.sh

clean:
	rm -rf invoices.csv invoices.xlsx demo/out demo/out-terminal demo/.toolchain demo/.scratch .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
