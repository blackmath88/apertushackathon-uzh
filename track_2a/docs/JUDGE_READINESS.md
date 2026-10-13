# Judge readiness

Second pass on 13 October 2026, by the coordinator, after the first pass by the Packet B subagent the same day. Branch `feat/b0-b2-mvp`. Every source below was retrieved on 2026-10-13. A page that could not be read is listed as unread, never as confirmation.

**Correction (13 Oct, second pass).** The first pass said Docker replay had not been re-run. In fact Docker `make reproduce` at `662e14d` exited 0 with identical metrics ([review](review/REVIEW_2026-10-13.md#packet-d--verification-coordinator-13-oct-owners-mac)). The first pass also listed the Notion challenge pages as unreadable. With a short wait for rendering they are readable, and they, together with the linked Q&A file, change N-RULES-1 below.

## Sources

| Source | Read? | Relevant content (short excerpts) |
|---|---|---|
| [Track 2A: UZH](https://hackapertus.notion.site/track-2a-uzh) (official Notion) | yes | Expected outputs: code / reproducible implementation, model predictions, short method description. Metric: token-level Spearman per pair, macro-averaged; "The provided evaluation script defines preprocessing and punctuation handling." Test set "must not be used during development". Says nothing about endpoints, the 34 dropped IDs or the file format. |
| [How to Submit a Project](https://hackapertus.notion.site/how-to-submit-a-project) (official Notion) | yes | Submit at hackapertus.ch/online-hack/submissions until **16 Oct 12:00 CEST, no extension**. The submission must "run in a docker container launched with the specified CLI entry point" and "run end-to-end when the judges try to run it", and must "follow the specified input/output format". |
| [UZH Q&A file](https://docs.google.com/document/d/1jDeo03BDQ3RdaI2h985RiyOTT_W2K5QaanBK7dbaB-4/mobilebasic) (linked from the track page; answers by the challenge provider) | yes | Judges score "on the test split". Teams should "run your systems only on the test split in the end", and "Include the full-set order" while keeping results reproducible "as if you wouldn't submit the predictions". Baseline: "Choose the one that is closer to your submitted system." CSCS inference API (`api.swissai.svc.cscs.ch/v1`) has a 60 s gateway timeout; the advice is to serve the model in one's own CSCS container. |
| [HackApertus project-template](https://github.com/HackApertus/project-template/tree/main/track_2a) | yes | `make run` from the root on a clean checkout, in Docker, "since that is how the judges will run it". The template is now at `09f8e9e` (2026-10-11); the repo pins `7f23822`. The root README lists `LLM_NAME` ("name and version of the model"), `LLM_BASE_URL` ("endpoint base URL") and `LLM_API_KEY` ("your API key"). "Your" hints that the team supplies the key, but nothing says who provides the endpoint at judging time. |
| [Submission form](https://hackapertus.ch/online-hack/submissions) | partly | Form fields appear only after choosing a track; not inspected (no form interaction). |
| [FAQ](https://hackapertus.ch/faq) | no | No relevant text rendered; not retried. |

## Status of the open questions

| ID | Official text | Repository assumption | Still open |
|---|---|---|---|
| **N-RULES-1** test procedure | **Answered by the provider (Q&A):** judges score on the test split; teams run their system on test only at the end and include the predictions. | Dev only. The split guard refuses `test` in every CLI path, and no test predictions exist. | **New blocker.** A final test-split run needs: (a) an owner decision to add a separate, explicit final-evaluation path (the split guard stays for development); (b) new inference on 224 documents × 3 pairs, which is not authorized; (c) clarification of "full-set order" (all documents in the official order, or only test IDs in that order). |
| **N-JUDGE-1** endpoint | Judges run `make run` end to end in Docker with `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` (template). No official text says who supplies the endpoint. The Q&A shows a CSCS inference API exists for participants, with a 60 s gateway timeout. | `make run` is BLOCKED (exit 3) without `LLM_*`. | **Which endpoint judges will use.** An unconfirmed endpoint is not proof that none exists. **Timeout risk:** on the pilot (transformers on an L40S), 5 of 9 B0 calls took more than 60 s (86–131 s); no B2 call did (max 26 s). This is untested on CSCS, where serving may be faster, but longer B0 generations could exceed a 60 s gateway limit. |
| **N-RULES-2** 34 dropped IDs | The track page says to use the provided evaluation script; nothing on `list_to_drop.txt`. | The manifest excludes the 34 upstream IDs. | Whether test scoring drops them, and whether predictions for them are expected. |
| **N-RULES-4** file format | "Follow the specified input/output format" (submit page); no format is specified on the track page. | Encoder-style `{id,text_a,text_b,labels_a,labels_b}` per language, in manifest order. | The exact files and naming, and whether "full-set order" means one line per document in the official dataset order. |
| Baseline choice | "Choose the one that is closer to your submitted system." | B0 = paper prompting baseline (closer to B2's prompting than DiffAlign). | Resolved; no change needed. |

## Execution modes (distinct)

| Mode | What it does | Network | Status |
|---|---|---|---|
| HF Jobs batch (transformers) | Ran the measured pilot on an L40S | HF Hub (model, bundle) | Executed once; run `20261012T062327Z-ff965461` |
| Offline replay `make reproduce` | Re-parses and re-scores committed `raw.jsonl`; **no model inference** | **Not air-gapped.** Docker Hub for the base image, plus `cli fetch` downloads the pinned dev data (HF) and the evaluator/prompt files (GitHub raw), hash-verified | Docker exit 0 at `662e14d` (13 Oct); venv re-score byte-identical at `9874189` |
| Live endpoint `make run` | Fetches pinned data, then calls `LLM_*` for 18 calls (B0 + B2 on the 9-document dev manifest) | Endpoint + HF + GitHub raw | **Never executed against a real Apertus endpoint.** Tested only against a mock server; BLOCKED, exit 3, without `LLM_*` |

Replay is **not** claimed to satisfy the judge requirement. The Q&A answer means judges expect a reproducible system plus test predictions, and `make run` currently runs the dev manifest only.

## Final inference path (implemented 13 Oct, synthetic tests only)

`python -m uzh_rsd.final` (source: `src/uzh_rsd/final.py`) is the separate operation that will produce final B2 predictions **once a real run is approved**. It is not part of `cli.py`, `make run`, `make reproduce` or any Make target. The development split guard is unchanged.

**What it does**

| Step | Behaviour | Exit |
|---|---|---|
| 1. Configuration (before reading input or building a backend) | Needs `--contract`, a confirmed contract: schema `uzh-rsd.final-contract/v1`, `status: confirmed`, a non-empty `evidence` reference, and decisions `full_set_order` / `dropped_ids` / `output_layout` none of which is `unresolved`. Only the `per_language_jsonl` layout is implemented, and `order` must be unique `{id, language}` entries. Also needs `LLM_*` and an `--out` directory that does not exist and is not inside `results/`, `diagnostics/`, `manifests/` or `data/`. | 3 BLOCKED |
| 2. Input (`--input`, JSONL) | Each record has exactly `id`, `language`, `text_a`, `text_b`. Any other field (e.g. `labels_a`, `gold`) is rejected by name; its value is never echoed or forwarded. The ID set must equal the contract's, languages must match, there are no duplicates or empty texts, and documents are processed in **contract order** (no reordering, no dropping, no reuse of dev exclusions). | 2 invalid_input |
| 3. Inference | Frozen B2: `render_b2`, `parse_b2`, `projection.py`, 40-token excerpt cap, `max_new_tokens` 1024. One attempt per call, `--timeout-s` (default 300), no retries. `raw.jsonl` holds one record per call. | — |
| 4. Validation and output | Every document needs a parsed B2 output whose vectors match the token counts and are finite in [0, 1]. A B2 output with no located spans is a valid all-zero vector (pilot behaviour). Call failures, unparseable responses or invalid vectors keep `final_meta.json` at `status: incomplete`, write `diagnostics.json`, and produce **no** prediction files. | 4 incomplete |
| 5. Complete | `predictions/predictions_{de,fr,it}.jsonl` in contract order (provisional schema `uzh-rsd.final-predictions/provisional-v1`: `{id, text_a, text_b, labels_a, labels_b}`). Then `final_meta.json` is set to `complete`. | 0 |

**Recorded in `final_meta.json`:**

- source commit and src-dirty flag;
- strategy identity (prompt version, parser, projection, cap, decoding);
- backend description (endpoint, timeout, `max_attempts: 1`; the key is never recorded);
- model name plus `--model-revision` recorded as *declared, not verified*, with a note that a name does not pin weights;
- contract sha256, evidence and decisions;
- input sha256 and per-language counts;
- output schema;
- start and finish times.

It never imports the scorer and never calls the official evaluator loaders or the dataset fetch/load functions. The tests patch those functions to fail and check `sys.modules`.

**Tested synthetically** (`tests/test_final_infer.py`, 16 tests, fake backend plus a 127.0.0.1 mock endpoint):

- the template contract is refused;
- unresolved decisions, missing evidence, an unsupported layout or duplicate order entries block before input is read;
- missing `LLM_*` blocks;
- existing or protected output directories are refused;
- sentinel gold fields are rejected without leaking;
- duplicate, missing, unexpected, language-mismatched and empty inputs are rejected;
- order is preserved;
- a failed call, an unparseable response or an interrupt leaves the run incomplete with no predictions;
- malformed vectors are rejected;
- the CLI works end to end against the mock endpoint, and the API key appears in no artefact;
- dev commands still refuse `--split test` before I/O;
- the path is not wired into the dev CLI or Make.

Mutation checks (each safeguard disabled in turn) made the suite fail every time.

**Not verified**

- Never run against a real Apertus endpoint. Behaviour under a real server's timeouts (e.g. CSCS's 60 s gateway), rate limits or response format is unknown.
- Never run on real test data.

**Unresolved, deliberately left open**

- **Official input.** The HF/GitHub test files bundle labels with text. Producing the gold-blind `--input` needs a separate gold-stripping step; that step is **not built**. Doing it means opening the test file, which needs owner approval. Then strip to the four fields only, with the labels never written to the input or any run directory.
- **Order and exclusions.** What "full-set order" means, and whether the 34 `list_to_drop.txt` IDs are predicted, must be written into the contract from the organisers' answer. The code does not guess them.
- **Format.** The exporter is provisional until N-RULES-4 is answered. A different layout means adding it explicitly; the contract only selects among implemented layouts.

**After approval (commands)**

1. Fill a copy of `final/contract.template.json` from the organiser answer: `order`, `decisions`, `evidence` and `status: confirmed`.
2. Build `final_input.jsonl` (gold-stripped; separate approval).
3. Run:

```bash
cd track_2a
LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=… PYTHONPATH=src python -m uzh_rsd.final \
  --contract final_contract.json --input final_input.jsonl --out final_runs/<run id> \
  --timeout-s 300 --model-revision <provider-stated revision, if any>
```

Exit 0 means `complete`, and only then are prediction files present. This does **not** close N-RULES-1 or N-JUDGE-1: no real test run or endpoint run has happened.

## DRAFT — NOT SENT: one consolidated message to the UZH challenge provider / organisers

> Subject: Track 2A (UZH SwissGov-RSD) — five short questions before submission
>
> Hello, thank you for the Q&A answers. We use Apertus v1.5 8B via `make run` (Docker, `LLM_NAME`/`LLM_BASE_URL`/`LLM_API_KEY`).
>
> 1. **Endpoint:** will judges provide an Apertus v1.5 endpoint through these variables, and with what timeout? The CSCS API's 60 s gateway limit would cut off our baseline's longer generations.
> 2. **Test predictions:** by "include the full-set order", do you mean one prediction line for every document of the full set in the official order, or only the test documents in that order? Which file layout and names should we use?
> 3. **Dropped IDs:** should the 34 IDs in `list_to_drop.txt` be excluded from our predictions?
> 4. **Fallback:** if a live judge rerun is impossible, may judges re-score our committed raw model outputs offline (`make reproduce`, no model calls) instead?
> 5. **Publication:** our public repository would contain raw model outputs that include the dev source texts and the paper's prompt templates (which have no licence in the GitHub repo). Is that acceptable, with attribution?
>
> Thank you, [team name]
