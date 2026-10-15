# Submission checklist — Hack Apertus Track 2A, UZH SwissGov-RSD

These rules come from the pinned sources in [SOURCES.md](SOURCES.md): the UZH brief in `docs/challenge-source/CHALLENGE.md` and the HackApertus template at `7f23822`. Status is as of 13 October 2026 (second pass), on the B0/B2 MVP branch (review pass: [ORCA_TASK_LEDGER.md](ORCA_TASK_LEDGER.md)).

Legend: ✅ done and verified · 🟡 implemented, evidence pending · ⬜ not started · ⛔ blocked / owner decision

## Event and template

| # | Requirement | Status | Evidence / next step |
|---|---|---|---|
| E1 | Submit at hackapertus.ch/online-hack/submissions by **16 Oct 2026, 12:00 CEST** (not Devpost) | ⬜ | Owner, after results |
| E2 | Keep `track_2a/` as-is; delete other tracks | ✅ | Only `track_2a/` exists |
| E3 | `make run` from the project root on a clean checkout runs the project **in Docker** | 🟡 | Docker image + root `make run` implemented. Without an endpoint it stops with BLOCKED (exit 3); the full path ran in the container against a mock endpoint. On 12 Oct, verified from a clean clone of `2adaeda` on the owner's Mac (Docker Desktop): `make -C track_2a reproduce` exits 0 and reproduces the committed scores exactly, and root `make run` without `LLM_*` stops with BLOCKED (inner exit 3). A live `make run` against a real endpoint is still blocked by N-JUDGE-1. |
| E4 | Model access via `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` | ✅ | `backends.OpenAICompatibleBackend`; key never recorded (tested) |
| E5 | Follow the input/output format; runs end to end when judges run it | 🟡 | Official encoder-style predictions `{id,text_a,text_b,labels_a,labels_b}` per language. Judges also need a working Apertus v1.5 endpoint (see N-JUDGE-1). |
| E6 | `data/` ≤ 100 MB | ✅ | Raw data ignored; fetched at run time |
| E7 | Built with Apertus; other open models only in support roles, described | ✅ | Only Apertus v1.5 8B; no other model anywhere |
| E8 | Open source (T&C: code Apache-2.0, docs CC BY 4.0) | ⛔ | Owner decision, see [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md): no LICENSE file exists yet; the unscoped CC BY line in the report could be read as covering third-party text (admin.ch source text, unlicensed upstream prompts embedded in `raw.jsonl`). Repo PRIVATE (re-checked 13 Oct). |
| E9 | `technical_report.md` sections 1–8 | 🟡 | Measured pilot (run `20261012T062327Z-ff965461`) filled into §1, §5 and §6. Team name/members and the final expanded dev comparison are still open. |
| E10 | No secrets or weights committed | ✅ | Token only as an HF Jobs secret; ledger and launch records hold no token. Committed run artefacts were scanned (no `hf_` tokens, keys or auth headers). |

## UZH challenge

| # | Requirement | Status | Evidence / next step |
|---|---|---|---|
| U1 | Data from `ZurichNLP/SwissGov-RSD` | ✅ | Pinned HF revision, dev only |
| U2 | **Test set never used in development** | ✅ | No test path in code; split guard before I/O, covering every CLI command (tests) |
| U3 | Token-level Spearman per pair, macro over DE/FR/IT; official preprocessing | ✅ | Parity with the pinned official `compute_correlations`; cross-check reported with every result |
| U4 | Apertus v1.5 8B or 70B | ✅ | `swiss-ai/Apertus-v1.5-8B@a411d83` measured on HF Jobs L40S: run `20261012T062327Z-ff965461`, job `6acc7ce1…`. 18/18 calls returned. |
| U5 | Reproduce a paper baseline with your Apertus model | 🟡 | B0 measured. Only 3 of 9 documents are parseable, and none is strictly valid (46/541 fallback tokens): 3 truncated at 4096 tokens, 3 malformed JSON. Matched macro 0.136; paper protocol 0.268 is a zero-fill artefact. Expanded dev slice still open. |
| U6 | Code, **model predictions**, short method description | ⛔ | Code ✅, method ✅, dev predictions ✅ in `results/20261012T062327Z-ff965461/predictions/`. The judge's prediction format (N-RULES-4) is unconfirmed. The UZH Q&A asks for **test** predictions in full-set order (N-RULES-1); none exist. |
| U7 | Secondary: efficiency, innovation | ✅ | Measured: B2 used 4,682 completion tokens and 150 s of generation; B0 used 22,945 tokens and 733 s, on the same 9 documents |

## Open questions and blockers

| ID | Question | Impact | Owner action |
|---|---|---|---|
| N-RUN-1 | ~~First measured B0/B2 GPU run~~ | Done 12 Oct: run `20261012T062327Z-ff965461`; total HF compute ≤ $0.75 | Decide whether to fund an expanded, predeclared dev slice (new compute authorisation needed) |
| N-JUDGE-1 | Which Apertus v1.5 endpoint can judges use for `make run`? Swisscom auth failed; HF/Featherless returned 1010; HF Jobs is batch, not an endpoint. | A live judge rerun is unconfirmed, not proven impossible. A CSCS API exists with a 60 s gateway timeout. 5 of 9 B0 pilot calls took more than 60 s on the L40S; this is untested on CSCS but could exceed the limit. `make reproduce` re-scores committed raw outputs with no model inference. | Organiser message drafted, **not sent**: [JUDGE_READINESS.md](JUDGE_READINESS.md). Live endpoint execution never performed against real Apertus. |
| N-RULES-1 | How is the held-out test evaluated? | **Answered in the UZH Q&A (read 13 Oct):** judges score on the test split; teams run on test only at the end and include predictions in "full-set order". The repo is dev-only and has no test predictions. | **Blocker.** Owner: authorize a separate final-evaluation path and a test run (new compute). Clarify "full-set order" (message drafted in [JUDGE_READINESS.md](JUDGE_READINESS.md)). Final workflow implemented and synthetically verified. **Real HF final run (job `6ace4b04…`, 13 Oct): 88/168 parsed, 80 unparseable (76 hit the 1024-token cap); run incomplete, no prediction files.** Owner decision needed (JUDGE_READINESS). |
| N-RULES-2 | Are the 34 `list_to_drop.txt` ids excluded for LLM systems? | Manifest already excludes them | Confirm |
| N-RULES-4 | Exact prediction file format | We export the encoder-style format | Confirm |
| N-LIC-1 | Upstream repo has no top-level licence | Evaluator and prompts are fetched at run time, not vendored | Keep, or ask UZH |
| N-PUB-1 | Publication of dev-text-bearing artefacts (options in [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md)) (raw responses, predictions) | Required "model predictions" contain dev text. They are now committed on `feat/b0-b2-mvp` in `results/20261012T062327Z-ff965461/`; the repository is **private** (checked 12 Oct). | Owner decision before the repository goes public |
