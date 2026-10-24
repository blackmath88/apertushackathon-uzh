.PHONY: audit run test reproduce docker-build evaluate mvp-setup hf-launch-dry hf-launch hf-collect hf-spend s1-setup s1-fetch s1-validate s1-manifest s1-check s1-smoke s1-smoke-live federal-pilot-demo federal-pilot-live federal-pilot-viewer b4-oracle b4-alignment b4-probe b4-check
SHELL := /bin/bash

VENV ?= .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
RUN = PYTHONPATH=src $(PYTHON)

IMAGE ?= uzh-rsd-lost-in-switzerland:local
# Committed measured run that `make reproduce` re-scores offline.
RESULT ?= $(notdir $(lastword $(sort $(wildcard results/2*))))

docker-build:
	docker build -t $(IMAGE) .

# Judge entrypoint, two explicit modes.
#
# MODE=pilot (default, unchanged): B0 + B2 on the fixed dev manifest against the
#   Apertus endpoint in LLM_NAME / LLM_BASE_URL / LLM_API_KEY, then evaluation.
#   Without those variables it stops with BLOCKED (exit 3).
# MODE=final: final B2 inference only (no scoring) via `python -m uzh_rsd.final`.
#   Needs FINAL_CONTRACT and FINAL_INPUT (mounted read-only), FINAL_OUT_DIR (host
#   directory, mounted read-write) and FINAL_RUN_ID (a new subdirectory). It checks
#   them before building and never falls back to the pilot or cached predictions.
#   The contract must be confirmed, otherwise uzh_rsd.final stops with BLOCKED.
MODE ?= pilot
FINAL_ARGS ?=
FINAL_DOCKER_ARGS ?=
SOURCE_COMMIT := $(shell git rev-parse HEAD 2>/dev/null)
SOURCE_DIRTY := $(if $(SOURCE_COMMIT),$(if $(shell git status --porcelain -- src 2>/dev/null),true,false))

run:
ifeq ($(MODE),pilot)
	$(MAKE) docker-build
	mkdir -p runs
	docker run --rm -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -v "$(CURDIR)/runs:/app/runs" $(IMAGE) run
else ifeq ($(MODE),final)
	@missing=""; for v in FINAL_CONTRACT FINAL_INPUT FINAL_OUT_DIR FINAL_RUN_ID; do \
	  eval "val=\$${$$v}"; [ -n "$$val" ] || missing="$$missing $$v"; done; \
	  if [ -n "$$missing" ]; then echo "BLOCKED: MODE=final needs$$missing (no fallback to the pilot)"; exit 3; fi
	@test -f "$(FINAL_CONTRACT)" || { echo "BLOCKED: FINAL_CONTRACT $(FINAL_CONTRACT) not found"; exit 3; }
	@test -f "$(FINAL_INPUT)" || { echo "BLOCKED: FINAL_INPUT $(FINAL_INPUT) not found"; exit 3; }
	@test ! -e "$(FINAL_OUT_DIR)/$(FINAL_RUN_ID)" || { echo "BLOCKED: $(FINAL_OUT_DIR)/$(FINAL_RUN_ID) exists; final runs never overwrite"; exit 3; }
	$(MAKE) docker-build
	mkdir -p "$(FINAL_OUT_DIR)"
	docker run --rm --user "$$(id -u):$$(id -g)" --add-host=host.docker.internal:host-gateway $(FINAL_DOCKER_ARGS) \
	  -e LLM_NAME -e LLM_BASE_URL -e LLM_API_KEY -e UZH_SOURCE_COMMIT=$(SOURCE_COMMIT) -e UZH_SOURCE_DIRTY=$(SOURCE_DIRTY) \
	  -v "$(abspath $(FINAL_CONTRACT)):/final/contract.json:ro" \
	  -v "$(abspath $(FINAL_INPUT)):/final/input.jsonl:ro" \
	  -v "$(abspath $(FINAL_OUT_DIR)):/final/out" \
	  --entrypoint python $(IMAGE) -m uzh_rsd.final \
	  --contract /final/contract.json --input /final/input.jsonl --out /final/out/$(FINAL_RUN_ID) $(FINAL_ARGS)
else
	@echo "BLOCKED: unknown MODE=$(MODE); use MODE=pilot (default) or MODE=final"; exit 3
endif

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

federal-pilot-demo:
	$(RUN) -m uzh_rsd.live_government_pilot demo --fixtures tests/fixtures/live_government_pilot --policy live_government_pilot/v1/policy/bfe-policy-review-20261013.json --out live_government_pilot/v1/demo

federal-pilot-live:
	$(RUN) -m uzh_rsd.live_government_pilot live --confirm-live --policy live_government_pilot/v1/policy/bfe-policy-review-20261013.json --out runs/live-government-pilot.json

federal-pilot-viewer:
	$(PYTHON) -m http.server 8765 --directory live_government_pilot/v1/demo

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

# B4 uses the immutable B2/B3 30-ID manifest. OUT must not already exist.
B4_MANIFEST ?= experiments/b2-projection-evidence/manifest.json
B4_OUT ?= runs/b4

b4-oracle:
	$(RUN) -m uzh_rsd.b4 oracle --manifest $(B4_MANIFEST) --out $(B4_OUT)-oracle --split dev

b4-alignment:
	$(RUN) -m uzh_rsd.b4 alignment --manifest $(B4_MANIFEST) --cache data/upstream/diffalign --out $(B4_OUT)-alignment --split dev

# Capability-only: exactly 16 local calls. Requires explicit confirmation and the
# pinned Apertus runtime already listening on loopback port 11436.
b4-probe:
	@test "$(CONFIRM_B4_PROBE)" = yes || { echo "BLOCKED: set CONFIRM_B4_PROBE=yes; this makes 16 model calls"; exit 3; }
	$(RUN) -m uzh_rsd.b4_probe --base-url http://127.0.0.1:11436 --out $(B4_OUT)-probe --split dev

b4-check:
	$(RUN) -m unittest tests.test_b4 -v
	$(RUN) -m unittest tests.test_b4_probe -v
	@if $(RUN) -m uzh_rsd.b4 oracle --manifest $(B4_MANIFEST) --out $(B4_OUT)-forbidden --split test; then echo "B4 accepted test split"; exit 1; else echo "B4 test split refused (expected)"; fi
