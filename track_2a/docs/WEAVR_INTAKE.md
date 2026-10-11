# Weavr intake and Codex review handoff

> **Historical plan.** For the 11 October submission focus, read [MVP_PLAN.md](MVP_PLAN.md) and [STATUS.md](STATUS.md). The broader canton/factory scope below is deferred. This document and staged commands do not authorize dispatch or change canonical Weavr state.

Status: repository preparation completed; live registration/ingress/runner unverified.
Authoritative project roadmap: SUBMISSION_ROADMAP.md; tracking issue #8.
Repository: blackmath88/apertushackathon-uzh.

## Prepared artifacts
- .github/workflows/weavr-command-bus.yml: canonical workflow copied from blackmath88/weavr (inspected main 9ba96fdcb8a8ccd6ad3f4be686dc2c0030fdb5c0).
- .weavr/staged/intake.json: proposed project registration payload, six typed mission contracts and create_mission commands. STAGED ONLY; not an inbox command and not canonical Weavr state.
- Missions follow current code validator rather than the older simplified documentation example.

## Bootstrap steps for an authenticated operator
1. Read live /api/state. Match repository before creating anything; reuse registered Project and check existing missions/runs to avoid duplicate/overwriting work.
2. If absent, register Project using authenticated POST /api/projects with the staged payload. Project registration is not supported by current GitHub command bus.
3. Configure repository secret WEAVR_GITHUB_INGRESS_TOKEN from existing approved setup. Never commit credentials.
4. Confirm deployed command bus supports create_mission and the live contract schema matches inspected source.
5. Add fresh immutable create_mission commands under .weavr/inbox only after registration/secret verification; check each applied result and actual mission state. Do not blindly replay a rejected command ID.
6. Submit a schema-valid plan for S1 using the current Weavr plan contract and compile Needs. Do not fabricate the plan schema.
7. Verify runner repository access, workspace, provider availability and routing. User has approved project intake and asked for progression; dispatch only within live accepted authority and gates.

## Review and progression intent
Claude: builder. Codex: preferred independent reviewer; use only an approved available fallback if Codex unavailable.
Weavr: authoritative gate enforcement. Reviewer recommendation is evidence, never a human identity or permission override.
Sequence S1 -> S2 -> S3 -> S4 -> S5 -> S6. Definitions reside in the roadmap; staged list order is not an enforced Weavr dependency graph.

Each review must use exact immutable builder commit and artifact hashes, inspect diff/scope, run relevant independent checks in isolation and verify claims against actual logs/artifacts.
Reviewer must not author the reviewed change. Do not pass builder self-evaluation as independent evidence.
Review output: PASS / REVISE / BLOCKED; checked commit and artifact hashes; checks/exit codes; acceptance-by-acceptance findings; unresolved Needs; next mission ID; provenance/provider identity.
PASS requires every prerequisite gate, not merely green unit tests. Missing live Apertus results stays BLOCKED for applicable gates.
REVISE routes focused repair inside the same scope; retry limit must come from approved runtime policy, never invented unlimited loops.
No automatic fallback to costly providers, no Need waiver, no widening, no test access and no auto integration.

## Current control-plane limitation
Current cloud/src/index.ts authorizes /api/runs/:id/decision as human; cloud/src/github-bus.ts exposes no run-decision command.
Codex can return review evidence and recommend continuation. It cannot impersonate a human KEEP decision.
Automatic transition requires an explicitly supported delegated policy and deterministic dependency check in Weavr. Until implemented/verified, pause at human-only decision gates; do not claim auto progression is active.
To permit continuation without merging, next mission must be pinned to the verified predecessor candidate commit/branch in an isolated workspace. Never assume unmerged outputs are on main.

## Closure ownership
Owner retains merge, visibility/license decisions, publication and final portal submission.
No commands have been dispatched by merely committing these files.
