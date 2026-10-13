# Judge readiness

Prepared 2026-10-13 by Packet B (read-only research subagent), integrated by the coordinator. Branch `feat/b0-b2-mvp`, base 9874189. "Retrieved" = 2026-10-13. An unreadable page is NOT confirmation.

## Source access today
| Source | Result |
|---|---|
| https://hackapertus.notion.site/track-2a-uzh | Not readable (JS-rendered Notion; browser pane returned an empty body). Brief in repo (`docs/challenge-source/CHALLENGE.md`) is user-pasted text captured 2026-10-08, `review_status: imported_source_not_reconciled_with_live_notion`. |
| https://hackapertus.notion.site/how-to-submit-a-project | Not readable (empty "Notion" shell). |
| https://github.com/HackApertus/project-template | Readable. |
| https://hackapertus.ch/terms-and-conditions | Readable. |
| https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD | Readable. |

## Items
| ID | Confirmed (source) | Unresolved |
|---|---|---|
| N-JUDGE-1 endpoint / runtime | Template README: judges run `make run` from root on a clean checkout, in Docker; `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` (github.com/HackApertus/project-template, retrieved 2026-10-13). Same page does not say whether organisers supply the endpoint or how teams get access. T&C page has nothing on judging execution/endpoints (hackapertus.ch/terms-and-conditions). | Whether judges inject their own `LLM_*` (and which model/size, timeout, rate limits, network egress, whether dev data fetch from HF/GitHub at runtime is allowed). Notion pages unreadable. Repo notes Swisscom auth failed and HF/Featherless returned 1010 (SUBMISSION_CHECKLIST N-JUDGE-1; unverified here). |
| N-RULES-1 code execution vs held-out predictions | Brief (pasted, 2026-10-08) lists deliverables "Code, model predictions, short method description"; test set must not enter development. Nothing found stating who runs the test set. HF dataset page (retrieved) gives no evaluation procedure. | Whether teams submit test predictions, judges rerun code on test, or only dev is used. Repo never touches test (split guard), so no test predictions exist. |
| N-RULES-2 34 dropped IDs | Repo: `list_to_drop.txt` from upstream GitHub commit 1807a42 (34 ids); manifest excludes them (SOURCES.md, checklist). HF dataset page does not mention the file. | Whether the organiser/judge scoring drops them for LLM methods, and whether predictions for them are expected or forbidden. |
| N-RULES-4 prediction schema | HF page: labels per language side are per-word scores 0..1 on whitespace tokens, punctuation -1 (retrieved). Repo exports encoder-style `{id,text_a,text_b,labels_a,labels_b}` per language. | Whether the judge expects exactly this file layout/naming, one file per language or combined, and whether LLM predictions use `1 - s/5` severity convention as exported. |

## Execution modes are distinct
- **HF Jobs batch** (run `20261012T062327Z-ff965461`, job `6acc7ce1...`): transformers backend on an L40S. Batch job, not an endpoint; judges cannot call it.
- **Cached replay** (`make reproduce`): re-parses and re-scores committed `raw.jsonl` offline in Docker; no model call. Docker replay verified on 12 Oct (checklist E3, inherited). On 13 Oct the Docker daemon was not running on the coordinator host, so Docker replay was **not** re-run; the same re-score ran in the Python venv from a clean worktree at `9874189` and reproduced `results.json` and `predictions/` byte for byte (git clean after rewrite).
- **Live endpoint** (`make run`): `OpenAICompatibleBackend` against `LLM_*`. Without all three variables it prints BLOCKED and exits 3 (`cli.py` `_infer`; observed 13 Oct in the venv at `9874189`: BLOCKED, exit 3. Root Docker `make run` could not build because the Docker daemon was not running). Tested only against a mock HTTP endpoint.

Replay is NOT claimed to satisfy judge requirements. Status: candidate prepared with blockers; not "submission ready".

## What live judge execution requires from this repo
- Docker; root `make run`, with `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` in the environment (the Makefile passes them with `-e`).
- OpenAI-compatible chat-completions endpoint serving Apertus v1.5; 18 calls on the 9-doc manifest (B0+B2); one attempt per call; output in `runs/endpoint-<UTC>/`.
- Container must reach the endpoint and (at run time) HF + GitHub raw to fetch pinned dev data, evaluator, prompts (hash-verified).
- **Status: never executed against a real Apertus endpoint.** Only the mock endpoint was used. Output differences (finish reasons, token usage fields) against real serving are unknown.

## DRAFT — NOT SENT (organiser message)
> Subject: Track 2A (UZH SwissGov-RSD) – judging procedure
>
> Hello, we are preparing a Track 2A submission using Apertus v1.5 8B (`make run`, Docker, `LLM_NAME/LLM_BASE_URL/LLM_API_KEY`). Four questions: (1) Will judges supply an Apertus v1.5 endpoint via these variables, and with what model, timeout and network access? If not, which endpoint may we use? (2) Is the held-out test set scored by judges running our code, or should we submit test predictions? (3) For LLM methods, are the 34 ids in the upstream `list_to_drop.txt` excluded from scoring? (4) What prediction file format is required (we export the SwissGov-RSD encoder-style `{id,text_a,text_b,labels_a,labels_b}` per language)? Until answered, we will state that our committed cached-replay path (`make reproduce`) is not live judge execution. Thank you.
