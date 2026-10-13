.PHONY: audit run test reproduce docker-build evaluate mvp-setup hf-launch-dry hf-launch hf-collect hf-spend s1-setup s1-fetch s1-validate s1-manifest s1-check s1-smoke s1-smoke-live
SHELL := /bin/bash

VENV ?= .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
RUN = PYTHONPATH=src $(PYTHON)

IMAGE ?= uzh-rsd-lost-in-switzerland:local
# Committed measured run that `make reproduce` re-scores offline.
RESULT ?= $(notdir $(lastword $(sort $(wildcard results/2*))))

docker-build:
	docker build -t $(IMAGE) .

# Judge entrypoint: B0 + B2 on the fixed dev manifest against the Apertus
# endpoint in LLM_NAME / LLM_BASE_URL / LLM_API_KEY, then evaluation.
# Without those variables it stops with a clear BLOCKED message (exit 3).
run: docker-build
	mkdir -p runs
	docker run --rm -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -v "$(CURDIR)/runs:/app/runs" $(IMAGE) run

# No model needed: re-parse and re-score the committed raw Apertus responses.
reproduce: docker-build
	@test -n "$(RESULT)" || { echo "no committed run under results/"; exit 1; }
	docker run --rm --entrypoint sh $(IMAGE) -c "python -m uzh_rsd.cli fetch >/dev/null && python -m uzh_rsd.cli evaluate --run results/$(RESULT)"

# Local scoring of a run directory or a run id under runs/.
evaluate:
	$(RUN) -m uzh_rsd.cli evaluate --run $(RUN_ID)

# Accounting supplement for a committed run (no model, no scores): writes only diagnostics/<run id>/.
audit:
	$(RUN) -m uzh_rsd.cli audit --run results/$(RESULT)

# Owner machine: venv with evaluator parity deps + huggingface_hub (HF Jobs).
mvp-setup: s1-setup
	$(VENV)/bin/pip install -r requirements-hf.txt

# HF batch GPU (owner machine, uses the saved `hf auth login` token).
hf-launch-dry:
	$(RUN) -m uzh_rsd.hf_launch launch --dry-run

hf-launch:
	$(RUN) -m uzh_rsd.hf_launch launch --confirm-spend $(HF_ARGS)

hf-collect:
	$(RUN) -m uzh_rsd.hf_launch collect --wait --run-id $(RUN_ID)

hf-spend:
	$(RUN) -m uzh_rsd.hf_launch spend

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
