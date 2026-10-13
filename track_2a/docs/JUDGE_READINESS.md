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

## Final inference path (implemented 13 Oct, synthetically tested; not run with real Apertus or real test data)

**Correction (13 Oct, fourth pass).** The third pass said an interrupt leaves "no `predictions/` directory". That holds only for an interrupt *before* the staged directory is renamed. Between the rename and the metadata commit, `predictions/` can exist while `final_meta.json` says `incomplete`. **`final_meta.json` is the only completion authority**; use `--verify` to check a run. Nothing is promised for SIGKILL or power loss beyond what is already on disk.

### Workflow

| Stage | Command | What it guarantees (tested) |
|---|---|---|
| 1. Prepare input | `python -m uzh_rsd.final_input --source de=… --source fr=… --source it=… --out PREP` | Reads official-shaped JSONL (dev-row field names), one file per language, and writes `final_input.jsonl` with `id`, `language` and the **tokenized** `text_a`/`text_b` copied verbatim, so vectors align with official tokens (checked against label lengths). Labels and untokenized fields are recognised and never read. Unknown fields, malformed records, duplicates and id/language mismatches are rejected with file:line and field names only. No dev exclusions; no download. Also writes `final_input.provenance.json` (source sha256, counts, **mechanical** source order) and `contract.draft.json` (status `unresolved`; refused by stage 2). |
| 2. Confirm contract | edit a copy of `PREP/contract.draft.json` | `order`, `decisions` and `evidence` come from the organiser answer. Mechanical source order is **not** the organisers' "full-set order" until they say so. |
| 3. Final inference | `make run MODE=final FINAL_CONTRACT=… FINAL_INPUT=PREP/final_input.jsonl FINAL_OUT_DIR=… FINAL_RUN_ID=…` (root) | Checks the four variables, that the files exist and that the run dir is new, **before** building. Mounts contract and input read-only and writes the host directory as the host uid. Passes the host commit and src-dirty flag. Inside: `python -m uzh_rsd.final`, BLOCKED (exit 3) unless the contract is confirmed and `LLM_*` are set. Frozen B2, one attempt per call, `--timeout-s` via `FINAL_ARGS`. `MODE=pilot` (default) is unchanged; an unknown `MODE` is refused; there is no fallback. |
| 4. Accept | `PYTHONPATH=src python -m uzh_rsd.final --verify OUT/RUN_ID` | Accepted only if `final_meta.json` is `complete`, no staging dir remains, and the prediction files match the recorded names, sha256, record counts and contract order. |

**Failure behaviour (tested):**

- A failed call or unparseable response: exit 4, meta `incomplete`, `diagnostics.json` kept, no prediction files.
- An ordinary exception: exit 4, meta `incomplete` with `interrupted.type`.
- KeyboardInterrupt: exit 130, meta `incomplete`.
- In every case `raw.jsonl` and any staged or renamed prediction files are kept for diagnosis.
- Existing run directories are never overwritten or resumed.

A valid all-zero B2 vector (the model returned no located spans) is kept as pilot behaviour; a failed request is never turned into zeros.

### Synthetic verification (13 Oct)

- **Unit tests:** `tests/test_final_input.py` (10) and `tests/test_final_infer.py` (21), in `make s1-check`.
  - Converter: sentinel annotation and untokenized values never reach prepared input, prompts, raw records, metadata or predictions.
  - Interruption: the exact post-rename window is tested and rejected by `--verify`; tampered files are detected.
  - Make: `MODE=final` blocks before build without configuration; `MODE=pilot` stays the default.
- **Docker end-to-end:** `PYTHONPATH=src .venv/bin/python tests/e2e_final_docker.py` (needs Docker; outside unittest discovery). It runs official-shaped synthetic rows → converter → root `make run MODE=final` (Docker) → a mock endpoint on the host loopback via `host.docker.internal` → `--verify`.
  - All 13 checks passed at `ef50e10`: unresolved draft BLOCKED inside Docker with no request sent; exit 0; same run ID refused; accepted by verify; host commit with `src_dirty: false`; input and contract sha256; order; vector lengths; one request per document; no sentinel or key in any artefact; host-owned outputs.

**Not verified:** any real Apertus endpoint (timeouts, rate limits, response format), any real test data, the official file layout.

### Real-run plan (one run; NOT executed, needs the approvals at the end)

Organiser position (Q&A, recorded above): judges score on test; development stays on dev; teams run the final system on test at the end and include predictions plus reproducible code; the baseline is the one closest to the submitted system (B0, the paper prompt). **Permission to run final inference is answered.**

Still open (do not assume): the meaning of "full-set order", the 34 dropped IDs, the output layout (N-RULES-4), and whether judges host an endpoint (N-JUDGE-1).

| Item | Plan |
|---|---|
| Frozen system | Branch head at approval time (record the SHA). B2 `b2-spans-v1`, `parse_b2`, `project_differences`, 40-token cap, `max_new_tokens` 1024, greedy, one attempt per call. No B0 on test unless the organisers ask. |
| Model | `swiss-ai/Apertus-v1.5-8B`. Revision `a411d83` (as the pilot) on the HF route; on an endpoint route the revision is whatever the provider serves, recorded as *declared*. |
| Data preparation | Owner-approved: download the pinned test files for de/fr/it from `ZurichNLP/SwissGov-RSD` (outside the dev code paths, which still refuse `test`), then `python -m uzh_rsd.final_input --source de=… --source fr=… --source it=… --out prep/`. Nothing is scored; labels are not read. |
| Contract | Copy `prep/contract.draft.json`; set `order`, `decisions` and `evidence` from the organiser reply; `status: confirmed`. |

**Route A: OpenAI-compatible Apertus endpoint.** Supported now, no code change. Command: `make run MODE=final FINAL_CONTRACT=… FINAL_INPUT=prep/final_input.jsonl FINAL_OUT_DIR=final_runs FINAL_RUN_ID=test-<date> FINAL_ARGS="--timeout-s 55 --model-revision <stated>"` with `LLM_*` set.

- Candidates are the CSCS API, if the team has access, or a paid hosted endpoint.
- **Risk:** the CSCS 60 s gateway. B2 took ≤ 26 s per call on the L40S pilot, but test documents are not length-filtered and serving speed on CSCS is unknown.
- A timed-out call leaves the run incomplete; there is no silent zero.
- Weights are not pinned by name.

**Route B: HF Jobs batch, L40S, pinned revision.** **Not runnable yet.**

- `hf_job.py` is bound to the dev manifest (`fetch_split(dev)`, `manifest_records`) and cannot run `uzh_rsd.final`.
- **Smallest adapter:**
  1. `hf_job.py --final-contract C --final-input I`: call `final.main([...], backend_factory=lambda t: TransformersBackend(model, revision))` instead of the manifest path, and upload `OUT/RUN_ID` with the existing `Uploader`.
  2. `hf_launch.py`: put the contract and input files in the private bundle.
  3. Reuse the existing spend ledger, `attempts=1` and job timeout.
- Estimated size: about 60–100 lines plus synthetic tests. The prepared test texts would go to the private HF dataset repo used for pilot bundles.

**Expected artefacts:** `OUT/RUN_ID/{final_meta.json, raw.jsonl, diagnostics.json, predictions/predictions_{de,fr,it}.jsonl}`, plus `prep/final_input.provenance.json` and the confirmed contract. Commit them under a new directory, never under `results/<pilot>`.

**Cost (Route B; assumptions):**

- Assumes 56 test documents per language (224 − 168 dev; **unverified**), so 168 B2 calls.
- Pilot B2 speed: median 15 s, max 26 s per call; long test documents assumed ≤ 35 s (`max_new_tokens` 1024).
- Expected ≈ 168 × 16 s + 5 min load ≈ 50 min, about $1.50 at $0.03/min `l40sx1`.
- Upper bound ≈ 168 × 35 s + 5 min ≈ 103 min. **Proposed enforceable ceiling: job timeout 110 min = $3.30**, plus raising the ledger cap from $3.00 to $4.50 total ($0.75 already committed).
- Route A cost depends on the provider; CSCS terms are not known here.

**Decisions before launch:**

1. Organiser answers for order, dropped IDs and layout (the message is drafted).
2. Approve opening the test files and running the converter.
3. Choose the route: A, with a named endpoint and credentials, or B, which first needs the adapter implemented and reviewed.
4. Approve spend: the Route B ceiling above, or Route A provider terms.

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
