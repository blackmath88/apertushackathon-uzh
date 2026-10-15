# Orca task ledger — UZH submission candidate

Handoff: [ORCA_HANDOFF_2026-10-13.md](ORCA_HANDOFF_2026-10-13.md) · PR: https://github.com/blackmath88/apertushackathon-uzh/pull/12 (draft, unmerged)
Coordinator: Claude Code desktop session (Opus 5.5), host: owner's Mac, started 2026-10-13 14:22 CEST, window 30 min, max 2 concurrent workers, no new compute/paid spend.
Trusted base: `9874189` (fetched from origin; local checkout fast-forwarded from `d30559c`, tree clean).

## Pre-flight

| Check | Observation |
|---|---|
| Concurrent coordinators | No other running Claude desktop session; last Apertus session idle since 2026-10-12. No extra worktrees. Orca `orchestration worker-list` shows no apertus workers. Stale remote branch `claude/quirky-babbage-wi047n` (2026-10-11, pre-#11 merge) — not treated as live; cloud session liveness not observable from here. |
| Weavr live state | No supported read route to live Project/Mission/Session state from this session. Issue #9 (Weavr/Faictory trial) open and deferred; no open Weavr issue/PR claims this work. Recorded as *unavailable*, no conflicting ownership found. |
| Orca route | Runtime reachable (`orca status`: ready), supervised `orchestration worker-start/stop` exists. Credential isolation and enforced timeout for daemon-launched workers **not verified** within the window → Orca workers not used. |
| Route used | Local Claude Code subagents (Agent tool, same host/session credentials, model inherited/tier-routed; effective model and usage not read back = unknown). No enforced timeout beyond prompt deadline + coordinator stop capability. Writes restricted by instruction to scratch files only (not enforced). |

## Tasks

| ID | Owner / route | Base | Writable paths | Depends | Status | Evidence | Review commit | Blockers |
|---|---|---|---|---|---|---|---|---|
| A | subagent (general-purpose, `[tier:deep]`) | 9874189 | scratch `packet_A_findings.md` only | — | done, settled (completed ~4.4 min) | [review/packet_A_audit_2026-10-13.md](review/packet_A_audit_2026-10-13.md); 2 major (disclosure), 4 minor | `662e14d` (self-review; claims A1, A6 re-checked against `results.json`, `methods.py`, test) | none |
| B | subagent (general-purpose, `[tier:standard]`) | 9874189 | scratch `JUDGE_READINESS.md`, `PUBLICATION_REVIEW.md` | — | done, settled (completed ~1.2 min) | [JUDGE_READINESS.md](JUDGE_READINESS.md), [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md); coordinator added 13 Oct D observations + visibility re-check | `662e14d` (self-review) | Notion challenge pages unreadable; admin.ch terms not read |
| C | coordinator | 9874189 + A/B | `track_2a/docs/*`, README, technical_report.md, PR body; `src/uzh_rsd/` + tests only for evidenced defects | A, B | done | report disclosure (A1–A3), test assertion (A6), STATUS/checklist/README, [review summary](review/REVIEW_2026-10-13.md); scorer output repair deferred (would break re-score identity) | `662e14d` (self-review) | — |
| D | coordinator (offline) | 9874189 (clean worktree) and candidate tree | none (verification only) | C | done | s1-check 83 OK/0 skip on base and candidate; venv re-score byte-identical; Docker `make reproduce` exit 0 (same metrics) and Docker `make run` BLOCKED exit 3 at `662e14d` | self-review of `662e14d` | no independent review route qualified (blackmath88/weavr#128 still a draft) |

## Usage and routes (observed)

- Coordinator: Claude Code desktop, requested model Opus 5.5; usage not read back.
- Subagents A/B: Agent tool on the same host and credentials. Tier tags were passed for the routing mod; the effective model was not read back. Reported subagent token totals were about 108k (A) and 83k (B), from harness task metadata.
- No paid API, GPU or HF calls. No savings are claimed.
- Workers settled: both completed before integration. No live workers remain. Scratch worktree `wt-d` was removed. `wt-e` (detached at `662e14d`, in the coordinator scratchpad) is removed after this commit.

## Next action

Owner decisions are listed in the [review](review/REVIEW_2026-10-13.md) and the PR body. To get an independent review, run a qualified read-only reviewer pinned to the pushed head commit.

---

# Second pass — 13 Oct 2026, 14:38 CEST (owner away; 120-minute budget)

Coordinator: Claude Code desktop session (requested Opus 5.5), owner's Mac. **Route: coordinator only, no workers.** The first pass's shared-credential subagent setup was not repeated, and no route with verified credential isolation and enforced timeout was set up. Base `6b2816e` (matched the expected checkpoint). Isolated worktree `apertushackathon-uzh.worktrees/prep2`, pushed to `feat/b0-b2-mvp`. No other active coordinator (desktop sessions idle, no other worktrees, no Apertus Orca workers). Weavr live state: still no read route; no governance acceptance is claimed.

| ID | Work | Status | Evidence |
|---|---|---|---|
| S2-1 | Audit supplement command (`cli audit`, `make audit`) + tests | done | `src/uzh_rsd/audit.py`, `tests/test_audit.py` (4 tests), output [`diagnostics/20261012T062327Z-ff965461/`](../diagnostics/20261012T062327Z-ff965461/audit_supplement.md) generated at `43eb63c`; cross-checks `parse_b2` counters; run directory hashed unchanged |
| S2-2 | Submission story corrections (parseable vs valid, near-equality, shared EN source, B2 units, replay network, endpoint wording) | done | `1e5afec`: README, STATUS, checklist, report, JUDGE_READINESS |
| S2-3 | Bounded source research (about 10 min) | done | Notion track and submission pages plus the UZH Q&A doc are readable. **Judges score on the test split (N-RULES-1, new blocker)**; a CSCS API with a 60 s gateway timeout exists. Submission form fields were not inspected (no form interaction); FAQ did not render. |
| S2-4 | Publication inventory + recommended path | done | [PUBLICATION_REVIEW.md](PUBLICATION_REVIEW.md); logs contain no dataset or model text; the Docker image carries `raw.jsonl` and predictions |
| S2-5 | Next-experiment protocol (not run) | done | [NEXT_EXPERIMENT_PROTOCOL.md](NEXT_EXPERIMENT_PROTOCOL.md) |
| S2-6 | Verification, PR body, push | done | Code fix `67b7326`; final head = the commit adding this row (read back from the PR after push; reported in the PR body and handoff). s1-check 89 OK / 0 skips; frozen evidence diff vs `d30559c` empty; Docker reproduce exit 0 / run BLOCKED on the `6766a70`-equivalent tree; PR #12 body replaced, `isDraft` read back true |

Review: **self-review only**; the independent review gate remains open. No paid compute, model inference, organiser contact, merge or visibility change.

Second pass settled: no workers were started, so none remain. The scratch worktree `prep2` and local branch `prep/audit-supplement-20261013` are removed after push; the main checkout is fast-forwarded to the final head. Open owner action: inspect the submission form's Track 2A fields (not inspected, deadline 16 Oct 12:00 CEST).

---

# Third pass — 13 Oct 2026, 15:59 CEST (final-inference path; 90-minute budget)

Coordinator: Claude Code desktop session (requested Opus 5.5), owner's Mac. Base `9b31366` (matched the expected head; no newer work). Isolated worktree `apertushackathon-uzh.worktrees/final`, local branch `prep/final-infer-20261013`, pushed to `feat/b0-b2-mvp`. No other active coordinator; no Apertus Orca workers. Weavr live state still not readable; no governance acceptance claimed.

**Orca route check (concrete limitation, no dispatch):**

- `orca orchestration worker-start` exists, with `--timeout-ms`, worktree placement and `worker-stop` fencing.
- Local workers are agent terminals running as the same macOS user. `~/.cache/huggingface/token` and `~/.config/gh/hosts.yml` are readable to them, and Orca's orchestration guide documents no credential isolation. They are shared-credential workers and so ineligible under this task.
- Remote environment `Nebuchdnezzar` (`ws://100.100.19.54:6768`): `orca status` reports "host did not answer" (unverifiable).
- **No workers were started.** Packets A (implementation) and B (contract/leakage review) were done by the coordinator. Packet B's gap list is folded into the design and the tests (adversarial cases in `tests/test_final_infer.py`).

| ID | Work | Status | Evidence |
|---|---|---|---|
| F-A | `src/uzh_rsd/final.py` + `final/contract.template.json` | done | commit `1ab52ce` |
| F-B | Contract and leakage gap list → adversarial tests (16) | done | template refused; sentinel fields rejected; order, duplicates, failure, overwrite, evaluator and fetch isolation; mutation checks |
| F-C | Docs: JUDGE_READINESS (final path section), STATUS, checklist, ledger | done | this commit |
| F-D | Verification (full suite, frozen evidence), PR body | done | Code and test head `4fd2ece`: s1-check 106 OK / 0 skips; `git diff 9b31366 -- results/ diagnostics/` empty; pilot venv re-score byte-identical; run/reproduce sources (`cli.py`, `runner.py`, `methods.py`, `scoring.py`, `prompts.py`, Dockerfile, Makefiles) unchanged since `9b31366`, so Docker not re-run. PR #12 body replaced after this ledger commit; `isDraft` read back true. Self-review covers the pushed head that adds this row. |

Independent review: **not available.** No enforced, credential-isolated, read-only route exists (local Orca workers share credentials; Nebuchdnezzar unreachable). Self-review only; the gate stays open.

Third pass settled: this session started no Orca or other workers. The retained or unverifiable entries in `orca orchestration worker-list` belong to other workspaces (soul.me, buildradar, weavr) and were not touched. The scratch worktree `final` and local branch `prep/final-infer-20261013` are removed after push.

---

# Fourth pass — 13 Oct 2026, 16:28 CEST (final workflow end to end; 60-minute budget)

Coordinator: Claude Code desktop session (requested Opus 5.5), applying `orchestrate-work` plus the enclosed `route-orca-work` 1.0.0 (read this session, not installed; the Weavr #113 assignment in the same attachment was **not** executed). Base `3966e86` (matched). Isolated worktree `apertushackathon-uzh.worktrees/e2e`, branch `prep/final-e2e-20261013`, pushed to `feat/b0-b2-mvp`. No other coordinator; no Apertus Orca workers. Weavr live state not readable; no governance acceptance claimed.

**Route selection (route-orca-work order):**

| Candidate | Observation | Decision |
|---|---|---|
| Local / Morrow on Nebu | `orca status --environment Nebuchdnezzar`: host did not answer (one bounded re-probe; unchanged since 16:00) | unavailable |
| Mistral | No managed OpenCode account and no configured Mistral harness (`orca account list`); no spend authority | not configured |
| Orca Claude/Codex workers | `worker-start` supports `--timeout-ms` and `worker-stop` fencing. Workers run as the same macOS user, with `~/.cache/huggingface/token` and `~/.config/gh/hosts.yml` readable (unrelated publishing and control-plane credentials). Orca's guide documents no credential boundary. The isolation option, `vm recipe`, needs an `orca.yaml` `environmentRecipes` setup the repo lacks; creating one would be building sandbox infrastructure. | ineligible |
| Result | **No Orca delegation occurred.** All packets were executed directly by the coordinator. No ordinary subagents were used or relabelled. | — |

| ID | Work | Status | Evidence |
|---|---|---|---|
| E-1 | Converter `uzh_rsd.final_input` + 10 tests | done | `0ea3ab9` |
| E-2 | Interruption: exceptions and KeyboardInterrupt → incomplete (exit 4 / 130); `--verify`; exact post-rename window tested | done | `0ea3ab9` |
| E-3 | Docker `make run MODE=final` + Make guards + e2e script | done | `ef50e10`; e2e 13/13 at `ef50e10` |
| E-4 | Real-run plan (routes A and B, cost, ceiling, decisions); docs corrections | done | JUDGE_READINESS "Real-run plan"; this commit |
| E-5 | Verification | done | s1-check 120 OK / 0 skips; `git diff 3966e86 -- results/ diagnostics/` empty; Docker `make reproduce` exit 0 (identical metrics); pilot `make run` BLOCKED exit 3 |

| E-6 | Plan accuracy (unpinned test files, route discriminator, submission default), `verify_run` and source robustness | done | `7a38bb3`: s1-check 120 OK / 0 skips; Docker e2e 13/13 at `7a38bb3` (prediction sha256 `c9e635cd…`/`e7c109dc…`/`0018c5c8…`, identical to `ef50e10`); frozen diff vs `3966e86` empty |

Review: self-review only, covering code head `7a38bb3` and the docs-only head that adds this line. The independent gate stays open (no eligible read-only, credential-isolated route). PR #12 body is replaced after this commit, with `isDraft` read back. Workers: none started by this pass. Scratch worktree `e2e`, its synthetic `final_runs/e2e-*` output (gitignored) and the local branch are removed after push.

---

# Fifth pass — 13 Oct 2026, 17:06 CEST (HF final integration and one real final B2 run; owner-approved spend)

Coordinator: Claude Code desktop session (requested Opus 5.5), `orchestrate-work` plus `route-orca-work` 1.0.0. Base `8ed92ed` (matched). Worktree `apertushackathon-uzh.worktrees/hf`. **Routes:** Nebuchdnezzar did not answer (local/Morrow unavailable); no Mistral harness; local Orca workers share unrelated credentials (unchanged since the fourth pass). **No Orca delegation; no workers started.** Weavr live state not readable; no governance acceptance claimed.

| ID | Work | Status | Evidence |
|---|---|---|---|
| R-1 | Locate and pin the official test files | done | `ZurichNLP/SwissGov-RSD@1807a42` `data/evaluation/gold_labels/test/`; 56 per language; git blobs verified |
| R-2 | HF final mode (`hf_job --final-*`, `hf_launch final` / `collect-final`), provisional contract status | done | `a0d3476` (freeze); 10 HF tests; s1-check 130 OK |
| R-3 | Upstream output contract (synthetic) | done | `tests/upstream_eval_contract.py`; `docs/review/upstream_eval_contract_2026-10-13.json` |
| R-4 | Mechanical test fetch and conversion (private, outside VCS) | done | 168 records; input `7db64ddc…`; contract `c37eaaee…`; fetch script sha256 `6fc2b046…` (scratch) |
| R-5 | Preflight and launch of exactly one job | done | `6ace4b04c66288145222d55c` launched 15:15:16Z; about 74 min scheduling; running 4,402 s; terminal ERROR (exit 4 = incomplete) |
| R-6 | Collect and verify | done | from the private repo; 168/168 returned, ids in order, hashes consistent; 88 parsed, 80 unparseable (76 length); `--verify` rejects; no predictions; cost ≤ $2.26; cumulative $2.94 ledger / $3.01 conservative |

Workers: none. The GPU job is verified terminal (ERROR). No replacement launched. Remaining budget about $1.49 under the $4.50 cap. Review: self-review only; the independent gate is open.

---

# B2 projection evidence — 13 Oct 2026, Nebuchadnezzar

| ID | Owner / route | Base | Status | Evidence / limitations |
|---|---|---|---|---|
| B2-PROJ | Orca dispatched Codex worker `task_9a604f2b6c3f`; documented `orca-cli` + orchestration fallback because the named route-orca-work topic was unavailable | `a0d3476` = `origin/feat/b0-b2-mvp` | done | Dedicated branch `blackmath88/b2-projection-evidence`; preselection commit `17a8922`; 30 fixed dev pairs (10 de/fr/it); frozen replay plus one local Q8 B2 call per pair; [experiment report](../experiments/b2-projection-evidence/README.md). P2 infeasible because responses have no offsets. |

Controls: no official test access, HF final job, paid compute, fallback model,
prompt/parser tuning, retries, fuzzy matching, or invented offsets. The Q8 GGUF
is not claimed equivalent to the frozen BF16/HF pilot. Morrow stayed live and
unchanged on 11435; the worker-started 11436 server was stopped after the run.
Frozen pilot artifacts were hash-checked before and after and remained identical.

---

# B3 Semantic Decision Middleware — 13 Oct 2026, Nebuchadnezzar

| ID | Owner / route | Base | Status | Evidence / limitations |
|---|---|---|---|---|
| B3-SDM | Orca dispatched Codex worker `task_1028b45cd9cd`; documented `orca-cli` + supervised orchestration fallback | `5892e50` = `origin/feat/b3-semantic-decision-middleware` | implementation complete; settlement pending coordinator receipt | Dedicated branch `blackmath88/b3-sdm-implementation`; draft PR [#16](https://github.com/blackmath88/apertushackathon-uzh/pull/16); pre-inference checkpoint `f6d620c`; exact PR #14 30-ID manifest; 230 tasks, 219 model / 11 structural, 0 overflow. One local Q8 run: 219 calls, 442.277 s, 42 valid classifier responses, 0/30 complete semantic decisions, 30/30 exact vectors, 177 UNKNOWN, 0 abstentions. Verdict **NOT SUPPORTED**; [report](../experiments/b3-sdm/local-q8-20261013/report.md). |

Controls: no official test inspection, Zürich crawl, HF job, cloud endpoint,
paid compute, fallback model, retry, gold-informed routing, JSON repair or
invented offset. The contract-only Zürich adapter performs no network access.
The exact worker-started PID 45895/port 11436 was stopped; Morrow PID 1240 on
11435 remained healthy and byte-identical. No worker subdelegation occurred.

---

# Discovery delivery — 14 Oct 2026, 21:58 CEST (30-minute ceiling)

Coordinator: Codex desktop session using the installed `route-orca-work` and Orca's version-matched orchestration guide. Exact base `2f1f9c0775273531cb89cde63b2702b6720de85e`; isolated Orca worktree/branch `blackmath88/federal-discovery-34-36-20261014`; draft PR #39 targets `feat/federal-evidence-desk-20261014`. Observatory was absent. `.weavr/staged/intake.json` remained staged-not-applied and no Mission, Need, baseline, deployment or merge state was changed.

| Task | Route / settlement | Commit | Evidence | Remaining gate |
|---|---|---|---|---|
| #34 guarded Scout | Orca worker, local Claude subscription; first Codex start failed before task execution with `agent-update-prompt`, was positively released, then retried; settled/reused | `3e3cadf` | request ledger, pacing, pinned addresses, typed purposes, budgets/frontier; focused regression included in 84-pass suite | SQLite ResourceWarnings |
| #35 selectable inventory | same settled Orca terminal, serialized after #34 | `64e46fc` | fixture sitemap/index/gzip/feed/navigation and four-language family tests; persistent campaign scope | no authorised live observation |
| #36 capture backend | same terminal, serialized after #35 | `7345835` | content-addressed fixture capture, distinct retrieval provenance, completeness/omission gates | no authorised live capture |
| #36 UI repair | one focused follow-up on same terminal; settled and released | `3ea4170` | preparation UI + authored browser fixture/script | standalone Playwright script not executed locally |
| Browser fixture correction | coordinator | `05e3379` | fixed missing discovery fields found by embedded-browser review; desktop/mobile showed no overflow or console error | final capture click re-observation interrupted by Orca browser connection drops |

Route decision: Nebuchdnezzar was unreachable, so its baseline/resource state remained unverifiable and no work was placed there. No local/Mistral account or harness was configured. The worker therefore used the existing local Claude subscription account; effective model was not read back. Product/model API calls and new paid spend were zero. No upstream dependency was adopted, so Protego/Scrapy/Courlan code and licences were not imported.

Verification: 84 focused tests pass under cached Python 3.13. Full discovery found 205 tests: 204 passed, 13 skipped and one environment error because `huggingface_hub` is absent. Node syntax checks passed. Browser evidence is authored-fixture-only; live-observed federal results remain none. Worker review and coordinator review are self-review; no permission-enforced independent read-only route was available.

Next action: run the authored Playwright browser check where Playwright is already installed, resolve SQLite connection warnings, obtain independent review of exact commit `05e3379`, then consider a separately authorised live check only for an eligible reviewed profile. Issues #37 and #38 remain untouched.

---

# Federal application acceptance repairs — 15 Oct 2026 (30-minute ceiling)

Coordinator: ChatGPT Codex, direct foreground execution from PR #39 head `d25331ce93d95c7b58836506e21daf7643179e2b`. Orca executable unavailable in this runtime; no worker or subagent dispatch. Canonical Weavr operating contract read; isolated preparation only, no canonical Mission/Need/staged-intake mutation.

Delivered in this commit: context-managed capture/one-shot SQLite stores; stricter body/decompression/deadline accounting; enforced inventory candidate bound and final-URL resolution; per-side capture provenance; retained successful evidence on counterpart failure; hash-verified campaign-owned evidence downloads; capture-to-comparison navigation; scope preservation and report coverage/provenance improvements.

Verification: **92 focused Python tests passed, zero skips**, including a real loopback HTTP discovery→selection→capture→download flow using authored upstream responses. Actual JavaScript report function smoke test passed; application/browser-script syntax checks passed. Python 3.12; explicit closed-connection checks, not a Python 3.13 warning rerun. Partial checkout, not a full repository/benchmark suite.

Browser remains open: Chromium absent; automatic approval review rejected downloading it under the retained no-dependency-download instruction. No alternate installation attempted. Updated browser harness is ready for an environment with an existing approved browser. Prior desktop/mobile observations are not re-labelled as validation of these new changes.

No live federal crawl, model call, protected test access, new application dependency, merge or deployment. Baseline untouched. Self-review only. The live campaign gate stays closed; redirected-target robots enforcement, direct-capture robots checks, eligible policy and broader adapters remain prerequisites. #37/#38 unchanged. See [APP_ACCEPTANCE_2026-10-15.md](APP_ACCEPTANCE_2026-10-15.md) for exact acceptance scope and next commands.

---

# Federal policy + offline walkthrough follow-up — 15 Oct 2026

Base: PR #39 `ae6e2d52c8841d272817b929461acc9d757c4a8e`. User requested continued implementation. Fresh PR and canonical Weavr contract read; Observatory snapshot and AGENTS files absent at checked paths, staged intake remains staged-not-applied. Orca executable unavailable; direct foreground work, no delegated workers and no canonical Weavr changes.

Scope delivered: request-time per-host robots checks on guarded redirects; blocked-decision provenance in Scout/discovery; robots-first direct capture with both-side preflight; fixture-only legacy capture injection; normal app `--demo-discovery` mode, clear authored labels and a walkthrough document; serial discovery/capture scheduling within the campaign store.

Evidence: 105 focused tests passed, zero skips; normal app CLI launched against loopback and verified demo/initial campaign/inference-off state; actual report function and JavaScript syntax checks pass. No external requests in the authored-response tests. Self-review only. No Chromium download retry, real browser result, live government crawl, model call, protected benchmark access, new dependency, merge or deployment. No claim of benchmark improvement. Remaining gates and local commands are in APP_ACCEPTANCE_2026-10-15.md and OFFLINE_DISCOVERY_WALKTHROUGH.md.
