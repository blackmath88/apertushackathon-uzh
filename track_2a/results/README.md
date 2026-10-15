# Committed measured runs

Each `results/<run_id>/` holds one Apertus run on the fixed dev manifest:
`raw.jsonl` (prompts, raw responses, token counts, timing, failures), `run_meta.json`
(model, revision, hardware, versions), `results.json` / `results.md` (scores and
coverage) and `predictions/<method>/predictions_<lang>.jsonl` (official format).

`make reproduce` re-parses and re-scores the newest run here without any model call.
