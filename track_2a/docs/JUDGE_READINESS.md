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
| **N-JUDGE-1** endpoint | Judges run `make run` end to end in Docker with `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` (template). No official text says who supplies the endpoint. The Q&A shows a CSCS inference API exists for participants, with a 60 s gateway timeout. | `make run` is BLOCKED (exit 3) without `LLM_*`. | **Which endpoint judges will use.** An unconfirmed endpoint is not proof that none exists. **Timeout risk:** on the L40S pilot, 5 of 9 B0 calls took more than 60 s (86–131 s); no B2 call did (max 26 s). Latency on CSCS will differ, but B0 through a 60 s gateway would probably fail on longer documents. |
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
