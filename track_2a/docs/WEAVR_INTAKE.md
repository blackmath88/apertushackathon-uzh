# Weavr intake and Codex review handoff

Status: repository preparation completed; live registration/ingress/runner unverified.
Current boundary: S1 only; see S1_DELIVERY_CONTRACT.md and .weavr/staged/s1-delivery.json. Activation and dispatch remain pending. Native stage-dependency enforcement is unverified.
Authoritative project roadmap: SUBMISSION_ROADMAP.md; tracking issue #8.
Repository: blackmath88/apertushackathon-uzh.

## Prepared artifacts
- .github/workflows/weavr-command-bus.yml: canonical workflow copied from blackmath88/weavr (inspected main 9ba96fdcb8a8ccd6ad3f4be686dc2c0030fdb5c0).
- .weavr/staged/intake.json: proposed project registration payload, six proposed mission contracts as roadmap inventory and one future S1 create_mission command template. S2–S6 are deferred; their broad scopes require later refinement. STAGED ONLY; not an inbox command and not canonical Weavr state.
- Missions follow current code validator rather than the older simplified documentation example.

## Bootstrap steps for an authenticated operator
1. Read live /api/state. Match repository before creating anything; reuse registered Project and check existing missions/runs to avoid duplicate/overwriting work.
2. If absent, register Project using authenticated POST /api/projects with the staged payload. Project registration is not supported by current GitHub command bus.
3. Configure repository secret WEAVR_GITHUB_INGRESS_TOKEN from existing approved setup. Never commit credentials.
4. Confirm deployed command bus supports create_mission and the live contract schema matches inspected source.
5. Only after explicit S1 intake authorization and registration/secret verification, materialize a fresh immutable S1 create_mission inbox command; verify its applied result and canonical Mission state. Do not copy S2–S6, reuse the template command ID or blindly replay a rejected command.
6. Submit a schema-valid plan for S1 using the current Weavr plan contract and compile Needs. Do not fabricate the plan schema.
7. Verify runner repository access, workspace, provider availability and routing. The current instruction is S1 readiness refinement; activation and dispatch remain pending explicit intent and live accepted gates.

## Review and progression intent
Claude: builder. Codex: required independent reviewer for this trial; unavailable Codex is a blocker, not permission to substitute.
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
Current trial requires human approval AND integration before the next Mission. Pin its workspace to the resulting integrated commit, reread canonical state and require explicit next-Mission authorization. Do not continue from an unmerged predecessor candidate under this trial contract.

## Closure ownership
Owner retains merge, visibility/license decisions, publication and final portal submission.
No commands have been dispatched by merely committing these files.

## Factory readiness boundary
A Weavr -> Orca coding run does not by itself prove Faictory's delivery path. Demonstrate Faictory workspace/attempt/capture/proposal/evidence records and independent Codex review ingestion before calling this the complete factory trial. Faictory #16 and #15 remain open; native Codex review and the connected envelope/evidence bridge are unverified. Resolve those in separately authorized factory work, not by adding orchestration to this benchmark repository. Background notifications are excluded.
