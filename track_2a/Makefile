.PHONY: run test

run:
	PYTHONPATH=src python3 -m uzh_rsd.cli --strategy dry-run --split dev

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
