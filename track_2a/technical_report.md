# Technical report — Lost in Switzerland

**Draft, 11 October 2026.** Method, setup and evaluation protocol are implemented and tested. **Measured Apertus results are pending the first HF GPU run**; every result cell below stays empty until it is filled from a committed `results/<run_id>/results.md`.

- **Track:** Track 2A — UZH: Detecting Cross-Lingual Semantic Differences in Swiss Government Websites (SwissGov-RSD)
- **Event:** Online
- **Team:** `team name` — `members` (owner to fill)
- **Demo:** none yet (optional results viewer deferred)

## 1. Summary

SwissGov-RSD asks for a semantic-difference score for every token of an English government page and its German, French or Italian version. We compare two ways of using Apertus v1.5 8B on identical dev documents. **B0** reproduces the paper's prompted baseline: the model re-emits every token with a 0–5 similarity label. **B2** asks the model only for the passages whose meaning differs (verbatim excerpts, kind, severity 1–5). Deterministic code then locates those excerpts in the benchmark tokens and projects severities onto them. Uncovered tokens score 0. Headline result: *pending*. The pilot covers nine fixed dev documents (three per language pair), so any difference between methods will be reported as indicative, not established.

## 2. Architecture

```
pinned dev JSONL ──► InferenceInput (tokens only, no labels) ──► prompt (B0 | B2)
                                                                     │
                     Apertus v1.5 8B (HF GPU job or OpenAI-compatible endpoint)
                                                                     │
raw.jsonl (prompt, raw response, tokens, latency, failures) ◄────────┘
      │  offline, deterministic
      ▼
parse (B0: upstream parse_token_labels | B2: excerpt location + projection)
      ▼
exact-length 0–1 vectors ──► official-format predictions ──► Spearman (+ official evaluator cross-check)
```

- `src/uzh_rsd/prompts.py`: pinned upstream B0 templates and the versioned B2 prompt.
- `src/uzh_rsd/runner.py`: both methods on the same manifest documents. One raw record per call is written immediately; deadline skips are explicit.
- `src/uzh_rsd/methods.py`: parsing. Every document is `ok`, `unparseable` or `call_failed`. Failures never become all-zero predictions.
- `src/uzh_rsd/scoring.py`: per-language and macro Spearman, coverage, usage and prediction export.
- `src/uzh_rsd/backends.py`: two backends. The transformers backend (HF batch GPU) is used for the measured runs. The OpenAI-compatible backend (`LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY`) is the judge path behind `make run`.
- `src/uzh_rsd/hf_job.py`, `hf_launch.py`: one HF Jobs GPU job. Code arrives as a hash-checked bundle from a private dataset repo. Results are uploaded after every call, with a log-bundle fallback. A spend ledger enforces the budget.

## 3. Use of Apertus

- **Model:** `swiss-ai/Apertus-v1.5-8B` at revision `a411d838600baf0e3635a3daf66fb7c55fc97bb6` (Apache-2.0, gated). This model is allowed by the UZH brief ("Apertus v1.5 — 8B and 70B"; "both cloud and local").
- **How it is used:** inference only. No fine-tuning, and no other model is involved anywhere in the pipeline.
- **Where it runs:** for the measured runs, Hugging Face Jobs `l40sx1` (1× L40S 48 GB). The image is `ghcr.io/swiss-ai/vllm_apertus_1.5_release:latest-amd64`, using its transformers build with `AutoModelForMultimodalLM`, bf16 (`dtype="auto"`) and an explicit `.to("cuda")`. The image has no accelerate, so `device_map="auto"` fails there. For judges, any OpenAI-compatible Apertus endpoint works.
- **Chat template:** `enable_thinking=False`. Content format is verified at load time, because some processors drop plain-string content; the chosen format is recorded in `run_meta.json`.
- **Decoding:** greedy (`do_sample=False` / `temperature=0`), as in upstream `predict_llama.py`. `max_new_tokens`: B0 4096 (upstream value), B2 1024.

### B0 — paper baseline, and deviations

The prompt is the upstream `prompt_templates/template_{de,fr,it}_admin.txt` at commit `1807a42`: three few-shot examples, a 0–5 similarity scale and −1 for punctuation. It is fetched at run time and its sha256 verified. Model labels are mapped with the official `1 − s/5`. Parsing uses the pinned upstream `parse_token_labels`, including its fallback: a token the model does not return counts as similarity 5, i.e. no difference.

Deviations, each deliberate and recorded:

1. **Token list format.** The upstream full-document script renders `json.dumps(text)`, which escapes non-ASCII characters. We pass the whitespace token list (`json.dumps(tokens, ensure_ascii=False)`), the same format as the template's few-shot examples.
2. **No `eval`.** Upstream parses model output with `eval`. We use `json.loads`, then `ast.literal_eval`, which is literal-only and never executes model output.
3. **Model `-1` on a token.** Upstream keeps −1, which ranks below 0. Our valid predictions lie in [0, 1], so a model −1 is scored 0. The count is reported (`model_punctuation_labels`). Labels outside −1…5 fall back like missing tokens, and are counted too.
4. **Backend and decoding.** The paper used other LLMs and providers. Here the Apertus v1.5 8B model runs through transformers, with greedy decoding and the chat template's thinking mode off.

Fallback tokens are **counted**, both per document and in total, so it stays visible how much of the B0 score comes from tokens the model never labelled.

### B2 — difference spans with deterministic projection

Prompt `b2-spans-v1` is zero-shot. It sends both texts and asks for `{"differences": [{"a", "b", "kind", "severity"}]}`. Kind is CHANGE, OMISSION or ADDITION. Severity is an integer 1–5. Excerpts are short and verbatim. Validation and projection work as follows:

- Each excerpt is located as a contiguous whitespace-token sequence: an exact match first, then a case- and quote-insensitive one.
- Every occurrence of an ambiguous excerpt is marked, and the ambiguity is counted.
- An unlocatable excerpt is dropped and counted.
- Severity outside 1–5 makes the item invalid, and it is counted.
- An unknown kind becomes `UNKNOWN`; it is counted and still projected.
- Projection reuses `projection.py`: the maximum severity per token, uncovered tokens 0, then `difference = severity / 5`.

## 4. Data

`ZurichNLP/SwissGov-RSD`, HF revision `f16aa05…`. **Only the `dev` split is used.** The test split is never downloaded, opened, prompted or evaluated, and the code enforces this (see `splits.py` and the tests). Labels are CC BY 4.0; the text is © Swiss federal authorities (dataset `LICENSE.md`).

The fixed manifest `manifests/s1-dev.json` has nine pairs: documents 43, 136 and 197 for each of EN–DE, EN–FR and EN–IT, at 88–267 tokens per side. It was selected gold-blind before any experiment. Raw data is not committed.

Committed run artefacts (raw responses, predictions) contain dev text. Their redistribution in a public repository is part of the publication decision.

## 5. Evaluation

Spearman correlation per language pair, computed globally over all tokens with gold punctuation (−1) masked, then the macro average over EN–DE, EN–FR and EN–IT. Our implementation matches the pinned official `compute_correlations` to 1e-10, and every reported value carries the official cross-check.

Views, with no silent filling or dropping:

- **Matched:** documents where both methods produced valid output. This is the like-for-like comparison.
- **Available:** every valid document, per method.
- **Paper protocol:** missing documents scored as zero difference, i.e. what the upstream parser yields for an empty response. A sensitivity check only.

| Setup | EN–DE | EN–FR | EN–IT | Macro | Valid docs | Calls | Completion tokens | Latency |
|---|---|---|---|---|---|---|---|---|
| B0 paper baseline (Apertus v1.5 8B) | pending | pending | pending | pending | pending | | | |
| B2 spans + projection (Apertus v1.5 8B) | pending | pending | pending | pending | pending | | | |

## 6. Limitations

- **Sample size.** Nine dev documents, three per pair, are a pilot. Per-language Spearman over roughly 1,000–1,700 tokens from three documents is dominated by those documents. No significance test is run and no superiority claim is made from it.
- **Test-set evaluation.** None is run, by design. How judges evaluate on held-out data is unconfirmed (N-RULES-1).
- **B0 output length.** B0 regenerates every token. Long documents can hit the 4096-token cap; truncated JSON is `unparseable` and reported as such.
- **B2 excerpts.** B2 depends on verbatim copying. Paraphrased excerpts are lost and counted as `spans_not_found`. Marking every occurrence of ambiguous excerpts can over-mark.
- **Untuned B2.** No prompt tuning on dev beyond this pilot. The prompt version is frozen per run.
- **Untested settings.** Single seed (greedy); no 70B; no self-consistency.

## 7. Reproducibility

- **Offline re-score (no model):** `make reproduce` builds the Docker image, fetches pinned dev data and evaluator files, and re-parses and re-scores the newest committed `results/<run_id>/raw.jsonl`.
- **Judge run with an endpoint:** `LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=… make run`.
- **Measured GPU run (owner machine with `hf auth login`):** `make -C track_2a mvp-setup s1-fetch`, then `make -C track_2a hf-launch`, then `make -C track_2a hf-collect RUN_ID=<id>`, then `make -C track_2a evaluate RUN_ID=<id>`.
- **Run metadata.** Every run records the model revision, image, GPU, torch/transformers/CUDA versions, prompt versions and hashes, manifest hash, bundle hash, source commit, token counts and per-call latency.

## 8. Next steps

- Expand to a larger, predeclared dev slice. Keep tuning and validation documents disjoint (upstream `dev/train` / `dev/val`).
- Run B2 at a few severity scales and alignment variants (B2a binary localisation).
- 70B comparison.
- A small "Lost in Switzerland" viewer built from measured outputs.

## License

Creative Commons Attribution 4.0 (CC-BY-4.0). All HackApertus projects are open-sourced.

## References

- SwissGov-RSD paper (ACL 2026): https://aclanthology.org/2026.acl-long.1437/
- Dataset: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD · Code: https://github.com/ZurichNLP/SwissGov-RSD
- Apertus v1.5: https://huggingface.co/swiss-ai/Apertus-v1.5-8B
