.PHONY: run reproduce test

# Judges: `make run` from a clean checkout (Docker; LLM_NAME, LLM_BASE_URL, LLM_API_KEY).
# Default MODE=pilot (dev manifest, unchanged). Final B2 inference is explicit:
#   make run MODE=final FINAL_CONTRACT=… FINAL_INPUT=… FINAL_OUT_DIR=… FINAL_RUN_ID=…
# Relative paths are resolved from this directory before handing over to track_2a/.
FINAL_PATHS = $(foreach v,FINAL_CONTRACT FINAL_INPUT FINAL_OUT_DIR,$(if $($(v)),$(v)="$(abspath $($(v)))"))
run:
	$(MAKE) -C track_2a run $(FINAL_PATHS)

# Re-score the committed Apertus run without any model call (Docker).
reproduce:
	$(MAKE) -C track_2a reproduce

test:
	$(MAKE) -C track_2a test
