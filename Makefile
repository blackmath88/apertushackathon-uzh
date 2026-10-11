.PHONY: run reproduce test

# Judges: `make run` from a clean checkout (Docker; LLM_NAME, LLM_BASE_URL, LLM_API_KEY).
run:
	$(MAKE) -C track_2a run

# Re-score the committed Apertus run without any model call (Docker).
reproduce:
	$(MAKE) -C track_2a reproduce

test:
	$(MAKE) -C track_2a test
