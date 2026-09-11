PY := .venv/bin/python

.PHONY: help setup run test samples demo clean

help:
	@echo "make setup    create .venv and install"
	@echo "make run      extract samples/ into invoices.csv"
	@echo "make test     run the test suite"
	@echo "make samples  regenerate the synthetic sample PDFs"
	@echo "make demo     regenerate demo/out/demo.gif, headless"

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

clean:
	rm -rf invoices.csv demo/out demo/.toolchain .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
