# Orca handoff — UZH submission candidate

Date: 13 October 2026 · timezone: Europe/Zurich  
Repository: blackmath88/apertushackathon-uzh  
Working branch: `feat/b0-b2-mvp` · draft PR: https://github.com/blackmath88/apertushackathon-uzh/pull/12  
Evidence baseline: `d30559c83723f7214a89c053d312dadd911a3456`

## Outcome and authority

Own the work breakdown, routing, dependencies, verification and handoff. Produce a reviewed, reproducible submission candidate and a short owner decision list. Do not stop at another plan: execute the independent, authorized preparation work when this handoff is started in Orca.

This document operationalizes the existing MVP scope; it does not activate the deferred Weavr/Faictory trial or broaden the submission. The 13 October user request authorizes recording this handoff for Orca, not dispatch from this chat. Preserve the later explicit instruction to keep PR #12 draft and unmerged; the older 11 October cleanup/merge permission is not authority to merge this candidate.

Allowed execution: read-only research, offline evaluation, bounded defect repairs and regression tests, report/checklist/documentation updates, private branch commits and pushes. Prepare a corrected PR description; applying that metadata correction is in scope when Orca executes this handoff.

Not authorized: new paid inference or GPU jobs, paid endpoints, HF uploads/dry-launch side effects, automatic retries of compute, merge/release, deployment, repository visibility change, organiser messages, portal submission, Weavr dispatch/waivers/scope changes. Remaining money under a historical ceiling is not spend authorization.

Keep test data entirely untouched. No new models, 70B, B2a, prompt tuning campaign, canton collection, production UI or orchestration infrastructure. A results viewer stays optional and deferred until required deliverables work; it is not this pass's acceptance criterion.

## Refresh before execution

1. Locate the local checkout, preserve dirty work, fetch current refs and inspect concurrent workers/branches/PR changes. Use isolated worktrees. Do not assume the evidence baseline is still the branch head.
2. Read applicable AGENTS.md instructions, an Observatory snapshot if present, README, MVP_PLAN.md, STATUS.md, SUBMISSION_CHECKLIST.md, technical_report.md and the challenge sources.
3. Read blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md. On 13 October the inspected tree had no AGENTS.md or Observatory artifacts; it did have staged Weavr intake and a command-bus workflow. Issue #9 defers activation. Staged JSON is not live Mission state.
4. Inspect live Weavr Project/Mission/Session/Need state if a supported read route exists. Record unavailable access honestly; do not create a Mission to unblock unrelated isolated preparation. Resolve any discovered conflicting active ownership before writes.
5. Load the orchestrate-work skill and its routing guidance when available. Inspect actual Orca capabilities rather than inventing CLI commands or assuming a daemon provides isolation.

## Known evidence — verify, do not rerun inference

- Experiment: `20261012T062327Z-ff965461`; HF job: `6acc7ce1095c578089328f6d`.
- Immutable evidence: `track_2a/results/20261012T062327Z-ff965461/`.
- Apertus v1.5 8B, nine dev pairs, 18 completed calls.
- B0: 3/9 parseable documents; even those use 46/541 fallback tokens. Three outputs truncate, three have malformed JSON.
- B2: 9/9 parseable; four excerpts not located in admin_fr_43; one ambiguous excerpt.
- Matched macro Spearman: B0 0.136, B2 0.138. No demonstrated accuracy advantage. B2 used about 20% of completion tokens and generation time in this pilot.
- Prior recorded checks: 83 tests, zero skips; official evaluator parity within 5.6e-17; byte-identical offline re-score; clean-clone Docker replay.
- Recorded three-job compute bound: $0.75, not an invoice. The pasted handoff's “four jobs” wording conflicts with its three-row table; verify compute.json and preserve the distinction.
- PR body is stale: it still claims no measured results. No GitHub reviews were submitted at inspection.

## Execution limits and coordination

Default initial pass: 30-minute supervised work window, at most two concurrent workers, no new paid API/compute spend. Finish earlier if done; checkpoint unfinished work at the limit rather than expanding scope or silently restarting the clock.

Prefer existing eligible subscription-backed Claude/Codex routes. Record requested/effective model, provider, harness, host and observed usage separately; unknown stays unknown. Do not assume subscription means free API access.

Before delegation verify credential isolation, enforced timeout, stop/settlement capability and active worker count, including possibly-live workers. No worker subdelegation. If a qualified route is unavailable, perform useful foreground coordinator work and label review limitations. A prompt deadline is not enforcement.

Maintain `track_2a/docs/ORCA_TASK_LEDGER.md`: task ID, owner/route, trusted base commit, writable paths, dependencies, status, evidence, review commit and blockers. Coordinator owns integration and shared files. Separate worktrees for writers; never run overlapping edits concurrently. At timeout observe worker settlement before releasing ownership or retrying elsewhere.

## Work packets

### A — Evidence and implementation audit

Start in parallel with B, against the refreshed exact commit. Read-only source access; write findings only to a separate scratch report for coordinator integration into `track_2a/docs/review/`.

Inspect raw records, prompts, parsers, projection, scoring and exported predictions. Reproduce the four missing French excerpts and classify each: model paraphrase, excerpt on wrong side, tokenization/normalization mismatch, ambiguity or implementation defect. Show the actual source/response evidence. Do not assume these four explain the negative correlation without checking.

Check B0 truncation, malformed outputs, fallback denominator, punctuation handling and documented baseline deviations. Check selection/coverage bias, all three scoring views, exact prediction lengths, language denominators, severity conversion and absence of gold labels from inference.

Deliver ranked findings with file references and bounded repairs. No silent JSON repair, fuzzy matching, retrospective prompt tuning or reinterpretation of the original experiment. Preserve original results unchanged.

### B — Judge contract and publication preparation

Independent research/write scope: new `track_2a/docs/JUDGE_READINESS.md` and `track_2a/docs/PUBLICATION_REVIEW.md`. Shared report/checklist remain coordinator-owned.

Read pinned challenge/template/data licence sources and check current official requirements using available read access. Record source URLs, retrieval dates and what is confirmed versus unresolved. Do not treat an inaccessible page as confirmation.

Resolve or prepare exact questions for:
- N-JUDGE-1: organiser-provided Apertus endpoint or expected runtime;
- N-RULES-1: code execution versus submitted held-out predictions;
- N-RULES-2: treatment of 34 dropped IDs for LLM methods;
- N-RULES-4: required prediction schema.

Draft one concise organiser message in JUDGE_READINESS.md; do not send it. Explain that HF Jobs batch execution and cached replay are distinct from a live endpoint. Do not claim replay satisfies judge requirements without confirmation.

Inventory licences/attribution for labels, source text, model, fetched upstream prompts/evaluator and committed text-bearing artifacts. Document publication options and unresolved permission questions; do not silently remove evidence, rewrite history or change visibility. Repo-wide CC BY wording must not imply ownership of third-party material.

### C — Integrate bounded repairs and reconcile documentation

Depends on A/B findings; coordinator assigns precise repair paths before any implementation worker starts. Permitted repair scope: existing `track_2a/src/uzh_rsd/`, related tests and existing Docker/Makefile configuration where an evidenced defect prevents documented behavior. No speculative refactor.

Coordinator updates README, STATUS.md, SUBMISSION_CHECKLIST.md and technical_report.md; records review findings; prepares/applies the corrected PR body. State parseable versus strictly valid output consistently. Treat French error analysis as diagnostic unless causal evidence exists.

If parser/scorer changes alter numbers, keep the original raw/evaluated evidence intact and record a separately versioned reanalysis with code revision, method change and original-versus-new comparison. Never overwrite the measured pilot to make a repair look like the original result.

Team name and complete membership require owner input; do not invent them. Keep optional broader experiments separate from submission blockers unless an official source requires them.

### D — Verification and independent review

After C, verify the combined candidate from a clean worktree:
- `make -C track_2a s1-setup s1-fetch s1-check`;
- root `make reproduce`, confirming expected metrics and prediction identity for the original method;
- missing-endpoint BLOCKED behavior and, if relevant code changed, the mock endpoint integration;
- no test data access, secrets, weights or unapproved artifacts; publication attribution inventory complete.

Offline reproduction may fetch pinned public dependencies/data: “no model inference” does not mean air-gapped. If runtime prerequisites are unavailable, record the exact blocked check; do not relabel inherited evidence as a new test.

Seek a qualified independent reviewer for the implementation and final fixes, pinned to the exact candidate commit, with enforced read-only source access, isolated credentials and bounded runtime. Reviewer writes only scratch findings. If this cannot be enforced, report self-review and leave independent review open. Fixes require review of the changed commit.

## Owner decisions and optional next experiment

Present a compact decision list only after completing independent preparation:
1. Organiser questions ready to send / answers still needed.
2. Team name and members.
3. Publication decision after licence review.
4. Whether to authorize a larger predeclared dev run.

An expanded experiment is optional strengthening, not automatically a required deliverable. Prepare only a design if time permits: document IDs selected without labels, language balance, untouched validation documents, frozen prompt/model/settings, expected calls/tokens/runtime and conservative pricing/budget assumptions. No launch or upload. A larger B0 output cap or repair method must be a separately named variant, not silently substituted for the baseline.

## Timing and completion

Target: review and package on 13–14 October; verification and owner decisions on 15 October. Recorded deadline: 16 October 2026, 12:00 CEST; verify against the current portal.

Handoff must include:
- exact branch/head and PR link;
- completed packets and unresolved findings;
- commands, observed results and links to evidence;
- original versus revised evaluation provenance, if applicable;
- reviewed commit/verdict or explicit review blocker;
- route/usage facts without invented savings;
- remaining owner/organiser decisions;
- stopped/settled worker states and next concrete action.

Keep PR draft and unmerged. Report “candidate prepared with blockers” if live judge execution or official contract remains unresolved; never “submission ready” merely because replay passes.

## Addendum — bounded B2 projection-cap experiment (Nebuchadnezzar)

The dedicated `blackmath88/b2-projection-evidence` branch, stacked from
`origin/feat/b0-b2-mvp` at `a0d3476`, evaluates whether B2's 40-token excerpt cap
drops usable evidence. The fixed 30-pair dev manifest was committed before
inference (`17a8922`). P1 (160-token cap, otherwise identical strict projection)
recovers 14 excerpts and improves macro 0.175044 → 0.192060 on the frozen pilot
replay, but recovers 28 excerpts and reduces macro 0.189283 → 0.180127 on the
17/30 parseable local Q8 responses. Therefore the cap does discard exact
evidence, but removing it does not consistently improve score. See
`track_2a/experiments/b2-projection-evidence/README.md`; P2 is infeasible because
the response schema contains no offsets. No test split, HF final job, paid
compute, prompt tuning, fallback, retry, or manufactured offset was used.
