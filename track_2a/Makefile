.PHONY: run test s1-setup s1-fetch s1-validate s1-manifest s1-check s1-smoke s1-smoke-live
SHELL := /bin/bash

VENV ?= .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
RUN = PYTHONPATH=src $(PYTHON)

# Scaffold dry run; the Docker-based judge entrypoint is S2 scope.
run:
	$(RUN) -m uzh_rsd.cli --strategy dry-run --split dev

test:
	$(RUN) -m unittest discover -s tests -v

# Ignored virtualenv with the evaluator-parity dependencies.
s1-setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements-s1.lock

# Downloads the three pinned dev files (never test) and the pinned official evaluator files.
s1-fetch:
	$(RUN) -m uzh_rsd.cli fetch --split dev

s1-validate:
	$(RUN) -m uzh_rsd.cli validate --split dev

# Rebuilds manifests/s1-dev.json from the predeclared rule.
s1-manifest:
	$(RUN) -m uzh_rsd.cli manifest --split dev

# S1 gate: every suite runs (no skips allowed), manifest reproduces, test split is refused.
s1-check:
	@$(RUN) -m unittest discover -s tests -v 2>&1 | tee runs/s1-check.log; \
	  status=$${PIPESTATUS[0]}; \
	  if [ $$status -ne 0 ]; then exit $$status; fi; \
	  if grep -q "skipped" runs/s1-check.log; then echo "s1-check: skipped tests are not accepted"; exit 1; fi
	$(RUN) -m uzh_rsd.cli manifest --split dev --check
	@if $(RUN) -m uzh_rsd.cli --strategy dry-run --split test; then echo "test split was accepted"; exit 1; else echo "test split refused (expected)"; fi

# Without --confirm-live no request is sent; writes a BLOCKED record.
s1-smoke:
	$(RUN) -m uzh_rsd.cli smoke

# Exactly one real request to LLM_BASE_URL using LLM_NAME / LLM_API_KEY from the environment.
s1-smoke-live:
	$(RUN) -m uzh_rsd.cli smoke --confirm-live
