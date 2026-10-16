# Technical report — Lost in Switzerland

**Final-delivery candidate, updated 16 October 2026; BLOCKED.** Method, setup and evaluation protocol are implemented and tested, but no complete held-out prediction set exists and no submission-readiness claim is made. The documented deadline has passed without extension evidence. A bounded long-input candidate (`b2-windowed-v2`, freeze `70fc85e`) was tested on a fixed six-document long/asymmetric dev set and rejected: 0/6 strict complete, 5/39 truncated responses and 34/39 invalid-evidence responses. It removed context overflow (largest prompt plus reserved output 2,344/8,192 tokens) but did not solve output discipline or exact excerpt location; no final input was opened and no final run was started. The first measured Apertus run remains committed as run `20261012T062327Z-ff965461` (HF job `6acc7ce1095c578089328f6d`), stored in [`results/20261012T062327Z-ff965461/`](results/20261012T062327Z-ff965461/results.md). It is a nine-document dev pilot; it is not a benchmark result.

- **Track:** Track 2A — UZH: Detecting Cross-Lingual Semantic Differences in Swiss Government Websites (SwissGov-RSD)
- **Event:** Online
- **Team:** `team name` — `members` (owner to fill)
- **Demo:** offline authored source → comparison → evidence → human-review viewer at `live_government_pilot/v1/demo/viewer.html`; it is product demonstration evidence, not benchmark validation.

## 1. Summary

Final delivery keeps the original B2/C0 method. Later evidence does not support
a semantic-accuracy improvement: the larger PR #44 validation measured C1
macro −0.01325 versus saved B0 0.00166, and the final paired-evidence verifier
reduced its unchanged C1 control from 0.06148 to 0.05806 on 18 fixed dev cases.
Only 6/18 generators were parseable in that verifier experiment. The historical
held-out run likewise parsed 88/168 and emitted no prediction files. These are
coverage and readiness failures, not scores to hide or repair. Full results and
the frozen execution contract are in `docs/FINAL_EXECUTION_PACKAGE_2026-10-16.md`.

SwissGov-RSD asks for a semantic-difference score for every token of an English government page and its German, French or Italian version. We compare two ways of using Apertus v1.5 8B on identical dev documents. **B0** reproduces the paper's prompted baseline: the model re-emits every token with a 0–5 similarity label. **B2** asks the model only for the passages whose meaning differs (verbatim excerpts, kind, severity 1–5). Deterministic code then locates those excerpts in the benchmark tokens and projects severities onto them. Uncovered tokens score 0.

**Pilot result (nine fixed dev documents, three per language pair; indicative only):**

- **Coverage.** B2 output was parseable for 9 of 9 documents. B0 output was parseable for only 3 of 9, and none of those three is strictly valid (46 of 541 tokens fell back to "no difference"). Three B0 responses hit the 4096-token cap. Three more stopped normally but were malformed JSON, so the parser could not read them.
- **Like-for-like comparison.** On the three language pairs where both methods are parseable (one document per language, all sharing one English source), macro Spearman is 0.136 for B0 and 0.138 for B2. Nearly equal; neither method shows an accuracy advantage.
- **All parseable output.** Over all of its 9 documents, B2 reaches macro 0.175.
- **B2 cost.** B2 used about a fifth of B0's completion tokens and generation time.
- **Paper-protocol view.** Missing documents scored as zero difference give B0 0.268. That figure is an artefact of between-document offsets, not token-level skill (§5).

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
- An excerpt longer than 40 whitespace tokens (`B2_MAX_EXCERPT_TOKENS`, `methods.py`) is dropped before location and counted as `spans_too_long`. The prompt asks for at most 15 words.
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

- **Matched:** documents where both methods produced parseable output. This is the like-for-like comparison.
- **Available:** every parseable document, per method.
- **Paper protocol:** missing documents scored as zero difference, i.e. what the upstream parser yields for an empty response. A sensitivity check only.

### Measured pilot: run `20261012T062327Z-ff965461`

- **Model and hardware:** Apertus v1.5 8B `a411d83`, bf16, transformers `5.14.0.dev0`, on 1× NVIDIA L40S. HF job `6acc7ce1095c578089328f6d` ran from 07:16:56 to 07:33:31 UTC on 12 October 2026, 994 s running time, after 53 min waiting for hardware. Total HF compute for the project is at most $0.75; see `compute.json`.
- **Provenance:** source commit `19b6183`. The bundle sha256 `ff965461…` was verified inside the job.
- **Calls:** 18 attempted, 0 failed, 0 skipped at the deadline.
- **Re-scoring:** re-scoring the committed `raw.jsonl` offline reproduces `results.json` and the predictions byte for byte.

**Matched documents (like-for-like, n = 3: `admin_{de,fr,it}_43`)**

These are one document per language, and all three share the same English source. They are B0's shortest document (88 English tokens), and each per-language Spearman covers about 160–170 unmasked tokens. They are not three independent samples, and B2 is compared on the one case where B0 survived.

| Setup | EN–DE | EN–FR | EN–IT | Macro |
|---|---|---|---|---|
| B0 paper baseline | 0.143 | 0.133 | 0.132 | **0.136** |
| B2 spans + projection | 0.324 | −0.093 | 0.183 | **0.138** |

**All parseable documents per method, with cost**

| Setup | EN–DE | EN–FR | EN–IT | Macro | Valid docs | Calls | Completion tokens | Generation time (total / median) |
|---|---|---|---|---|---|---|---|---|
| B0 paper baseline | 0.143 | 0.133 | 0.132 | 0.136 | 3 / 9 | 9 | 22,945 | 732.8 s / 86.3 s |
| B2 spans + projection | 0.355 | 0.075 | 0.095 | 0.175 | 9 / 9 | 9 | 4,682 | 149.8 s / 15.4 s |

**Paper protocol (sensitivity check only):** B0 macro is 0.268, with 6 of 9 documents zero-filled; B2 is 0.175, with none zero-filled. B0's higher figure is not evidence of token-level skill:

- B0 parsed only document 43 in each language, the documents with the most gold differences (gold mean difference 0.20–0.30). It predicted high difference there (mean 0.62–0.72).
- The zero-filled documents are the ones with the fewest differences (gold mean 0.01–0.18).
- So the global per-language Spearman rewards this offset between documents.

**Coverage and parse diagnostics**

- **B0.** Three documents parsed (`*_43`) and six are `unparseable`:
  - `*_197` (all three languages) reached `max_new_tokens` = 4096, giving truncated JSON.
  - `*_136` (all three languages) stopped normally but are malformed JSON. Apertus dropped opening brackets, e.g. `"\'s", 0]`, `"of", 1]`. Neither `json.loads` nor `ast.literal_eval` can read this, and upstream `eval` would fail too.
  - None of the three parsed documents is strictly valid. In them, 46 of 541 tokens (8.5 %) fell back to "no difference" (upstream fallback, similarity 5). The model gave a `-1` (punctuation) label to 9 tokens, which are scored 0 (deviation 3).
- **B2.** All nine parsed. 41 difference items, so 82 excerpts (two per item; 2 are empty by design, one-sided additions). Excerpts: 62 located exactly (1 of them ambiguous: `admin_de_197`, severity 1, 4 occurrences marked), 0 by normalised match, 4 not found (all in `admin_fr_43`), **14 over the 40-token cap**. Items: 30 projected completely, 4 partially (one excerpt located: 2 with the other over the cap, 2 with it not found), 7 not at all (6 with both excerpts over the cap, 1 with both not found). So 34 items reached the tokens, and the cap alone explains 6 of the 7 unprojected items. Details: [audit supplement](diagnostics/20261012T062327Z-ff965461/audit_supplement.md), regenerated by `make -C track_2a audit` from the frozen raw responses. This count is in `results.json` (`spans_too_long`) but missing from `results.md`, whose renderer predates this review. The committed file is left unchanged (see [review](docs/review/REVIEW_2026-10-13.md)). No invalid items, severities or kinds.
- **Official-evaluator parity.** For all 18 per-language cells across the three views, our Spearman equals the pinned official `compute_correlations` to within 5.6e-17.

**Interpretation.** On three matched language pairs from one English source, B0 and B2 are nearly equal on correlation, and the pilot cannot rank them. B2's EN–FR matched score (−0.093) rests on the single document `admin_fr_43`, where four excerpts could not be located:

- two de-spaced `www . stelle . admin . ch` URLs;
- one curly apostrophe changed to a straight one;
- one garbled copy.

As a diagnostic only, not a repair, placing them by hand gives about +0.02. So they do not fully account for the negative score. The clear, measured difference is **robustness and cost**:

- B2 returned usable output for every document.
- B2 used about 20 % of B0's completion tokens and generation time.
- The paper's full-regeneration format failed on six of nine documents with this 8B model and greedy decoding.

This supports continuing with B2 on a larger, predeclared dev slice. It does not establish that B2 correlates better.

## 6. Limitations

- **Sample size.** Nine dev documents, three per pair, are a pilot. Per-language Spearman over roughly 1,000–1,700 tokens from three documents is dominated by those documents. No significance test is run and no superiority claim is made from it.
- **Test-set evaluation.** None is run; development is dev-only by design. The UZH Q&A (read 13 Oct) says judges score on the test split and teams run their system on it at the end. A separate final-evaluation run has not been authorized or performed (N-RULES-1).
- **B0 output length and format.** B0 regenerates every token. In the pilot, all three `*_197` documents hit the 4096-token cap and produced truncated, unparseable output. All three `*_136` documents ended normally but were malformed JSON. B0 therefore has parseable output for only 3 of 9 documents (none strictly valid), and the matched comparison rests on those three. A larger cap or a JSON-repair step would be a deviation from the paper baseline. Neither is applied.
- **B2 excerpts.** B2 depends on verbatim copying. Paraphrased excerpts are lost and counted as `spans_not_found`. Marking every occurrence of ambiguous excerpts can over-mark.
- **Untuned B2.** No prompt tuning on dev beyond this pilot. The prompt version is frozen per run.
- **Untested settings.** Single seed (greedy); no 70B; no self-consistency.

## 7. Reproducibility

- **Committed run:** `results/20261012T062327Z-ff965461/` holds the following:
  - `raw.jsonl`: every prompt and raw response, with token counts, latency and finish reason
  - `run_meta.json`
  - `launch.json`
  - `results.{json,md}`
  - `predictions/`
  - `job.log`: the HF job log, without the base64 result bundle
  - `compute.json`: the cost reconciliation
- **Offline re-score (no model inference, not air-gapped):** `make reproduce` builds the Docker image (base image from Docker Hub), fetches pinned dev data (Hugging Face) and evaluator files (GitHub raw), and re-parses and re-scores the newest committed `results/<run_id>/raw.jsonl`.
- **Judge run with an endpoint:** `LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=… make run`.
- **Measured GPU run (owner machine with `hf auth login`):** `make -C track_2a mvp-setup s1-fetch`, then `make -C track_2a hf-launch`, then `make -C track_2a hf-collect RUN_ID=<id>`, then `make -C track_2a evaluate RUN_ID=<id>`.
- **Run metadata.** Every run records the model revision, image, GPU, torch/transformers/CUDA versions, prompt versions and hashes, manifest hash, bundle hash, source commit, token counts and per-call latency.

## 8. Next steps

- Expand to a larger, predeclared dev slice: drafted in [NEXT_EXPERIMENT_PROTOCOL.md](docs/NEXT_EXPERIMENT_PROTOCOL.md) (24 English sources, grouped bootstrap, frozen settings; not run, needs compute approval). Keep tuning and validation documents disjoint (upstream `dev/train` / `dev/val`).
- Run B2 at a few severity scales and alignment variants (B2a binary localisation).
- 70B comparison.
- A small "Lost in Switzerland" viewer built from measured outputs.

## License

- **Our documentation and report:** Creative Commons Attribution 4.0 (CC BY 4.0), per the HackApertus terms.
- **Our code:** intended Apache-2.0, per the HackApertus terms. No LICENSE file has been added yet; that is an owner decision.
- **Third-party material keeps its own terms.** None of the following is relicensed by this repository:
  - SwissGov-RSD labels (CC BY 4.0, ZurichNLP).
  - Source texts (© Swiss federal authorities, admin.ch terms of use).
  - Upstream SwissGov-RSD prompts and evaluator (no top-level licence). They are fetched at run time, and the prompt text is also embedded in committed `raw.jsonl`.
  - Apertus model and outputs (Apache-2.0, gated access).

Open publication questions are in [PUBLICATION_REVIEW.md](docs/PUBLICATION_REVIEW.md).

## References

- SwissGov-RSD paper (ACL 2026): https://aclanthology.org/2026.acl-long.1437/
- Dataset: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD · Code: https://github.com/ZurichNLP/SwissGov-RSD
- Apertus v1.5: https://huggingface.co/swiss-ai/Apertus-v1.5-8B
