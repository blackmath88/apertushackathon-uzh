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
| F-D | Verification (full suite, frozen evidence), PR body | see final handoff | — |

Independent review: **not available.** No enforced, credential-isolated, read-only route exists (local Orca workers share credentials; Nebuchdnezzar unreachable). Self-review only; the gate stays open.
