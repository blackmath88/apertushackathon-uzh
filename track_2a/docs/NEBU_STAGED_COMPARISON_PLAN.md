# Nebu: explore, validate, then compare at full scale

Prepared 16 October 2026. Planning base: `da846de8270d4f3c0efa565eeb1ab54458fb8793`.
Execution entry point: current main plus this document; inspect the actual local state first.
This is an execution handoff, not a claim that a runner or scheduled monitor exists.

## Outcome and authorization

When the owner hands this plan to local Codex, prepare and run a bounded development comparison of at most three Apertus candidates against saved B0 baseline predictions. Use the existing installed local Apertus on Nebuchadnezzar. No baseline re-generation is needed.

Initial envelope: preparation and offline checks, then exploration plus one validation pass, with at most 120 real requests and 60 minutes of model execution total. Preparation has a separate 30-minute work window. Finish sooner when possible; checkpoint if either limit is exhausted. Do not automatically extend budgets.

Full-development inference and final-test inference are separate owner decision gates. Prepare concrete estimates and commands before presenting those gates. No paid/cloud inference, downloads of new models, training, merge, deployment, submission, organiser contact, Weavr dispatch, scope widening or Need waiver is authorized here.

Check submission freezes and current competition instructions before any write. If the competition snapshot is frozen, perform this as separately labelled post-submission research on an isolated branch; do not alter the submitted artifact, tag or claims. The recorded deadline is 16 October, 12:00 CEST: this staged research is not a promise to finish before it and is not permission to modify a submission.

## Read and orient

1. Read applicable AGENTS.md, the current PROJECT_MAP.md, any fresh Observatory evidence, and blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md.
2. Inspect current Weavr ownership through an available supported read route when this work is governed. Unavailable state does not authorize conflicting work. No new Mission is required for otherwise isolated development.
3. Inspect local branches/worktrees, dirty files, active workers and GPU/model processes. Preserve other work. Use an isolated worktree based on current main; do not resume historical feature branches.
4. Read PR #40 and verify its actual evidence and private local artifacts. Its inspected head was `e9c397fb570adf867a0fcfac2bacd205db41f7a4`; it remains a draft, not accepted evidence merely by existence. Reuse required artifacts or narrowly port runner helpers with provenance; do not merge its historical branch wholesale.
5. Read the existing prompt-variation plan, B2 code, B4–B8 reports, official evaluator contract and publication rules. Treat proposed methods and previous negative results honestly.
6. Apply the installed orchestrate-work and route-orca-work skills if available. Inspect real Orca capabilities; do not invent commands or call an ordinary terminal an Orca run. Default to foreground local Codex execution if an eligible orchestration route is unavailable.

## Reference baseline

PR #40 records 489 resolved cases, 333 returned responses, 59 parseable, 1 strictly valid, 155 context overflows and one restart-related transport failure. Recorded macro Spearman: all-manifest 0.01021567996488429; available-only 0.0875492679378083. Verify exact denominators and failure handling from artifacts before comparison.

The report discloses post-freeze runner changes. Describe this as the local Q8 descriptive baseline, not an exact reproduction of the original paper or the earlier BF16 cloud pilot.

Pin the manifest, prediction files, evaluator, failure convention and their hashes. Reuse saved baseline vectors for each selected case in the same order. Re-score the selected baseline cases: never substitute the global 489-case score for a subset baseline.

Returned, parseable, strictly valid and usable without token fallback are distinct categories. Use the audited definitions; do not classify 333 returns as 333 successful predictions.

## Stage 0: freeze subsets and candidate configurations

Implement only the missing small runner/manifest/report adapter. Reuse existing parsers, token mapping, evaluator and immutable run machinery. Do not rewrite orchestration infrastructure.

### Source-grouped subsets

Build subsets solely from permitted development inputs and metadata, never from labels, baseline success/failure status or scores.

- Canonical grouping key: verified shared English source identity from upstream metadata; where unavailable use the hash of exactly normalized English input text with a recorded normalization rule. Do not assume matching numeric ID suffixes prove source identity.
- Keep every DE/FR/IT pair belonging to a source group in the same partition. Deduplicate source families before selection.
- Derive a length measure from the maximum combined official-token length of the pairs in each group.
- Sort all eligible groups by length, then stable group identity. Divide into three equal-count strata: short, medium and long, with deterministic remainder handling.
- Within each stratum order by SHA-256 of `nebu-subset-v1|group-key`.
- Select the first four groups per stratum for exploration (12 groups, normally up to 36 pairs); the next six for validation (18 groups, normally up to 54 pairs).
- If complete three-language groups are insufficient, record availability and use fewer groups, without replacing them based on outcomes. List omitted/incomplete groups and the limitation.
- Preserve upstream memberships and all known prior experimental exposure. This is a reserved validation subset, NOT a pristine unseen holdout: development data has already been used.
- Freeze group keys, IDs, language, original order, input hashes, stratum, exposure notes and subset digest before inference or subset scoring. Keep source texts private.

The full manifest remains all 489 audited cases. Subsets are exploratory sampling, not official exclusions from the benchmark.

### Candidates and budget

Name and freeze at most three concrete configurations:
- C0: unchanged existing B2 implementation, as the anchor candidate.
- C1: one bounded instruction/schema variation selected from existing plans.
- C2: one bounded chunked/aligned-span variant only if existing code supports it safely; otherwise omit it.

For each, commit exact prompt/schema, parsing/projection, segmentation/alignment, deterministic merging, context/output limits, decoding, model/runtime hashes, request accounting and failure policy. Chunking must preserve every official token and distinguish unprocessed tokens from predicted no-difference. No silent input truncation, output repair or gold-dependent alignment.

Compute the exact schedule BEFORE launch. The 120-request ceiling includes synthetic endpoint probes, every chunk, and validation. Validation must be reserved first: exploration cannot consume its budget. Default:
- exploration: C0 plus at most one alternative on 36 pairs = 72 requests;
- validation: one winner on 36 pairs = 36 requests (use the first four reserved groups per length stratum);
- up to 12 requests remain for probes or chunk overhead.
The larger 18-group validation pool permits a predeclared smaller execution schedule, not opportunistic expansion. Commit the exact validation IDs before exploration. If any method needs more calls, reduce exploration groups evenly by stratum or drop an arm before launch. Never compare configurations on different exploration case sets.

No adaptive prompt editing campaign in this pass. A revised prompt is a new experiment with a new budget and a still-unused validation partition.

## Stage 1: explore

Run the frozen configurations on identical exploration cases. One request in flight globally; use no competing GPU inference. Preserve the existing model weights, runtime revision, context capacity and decoding; record changed method-specific prompt/output bounds explicitly.

Verify the actual installed GGUF hash, quantization, llama.cpp revision, chat template and effective context. Loopback 11436 is the historical Apertus endpoint, not a guarantee it is running. Acquire exclusive ownership before starting the established Apertus service. Never stop or reconfigure another active owner. Morrow on 11435 is unrelated and must not be used as fallback or modified.

Use an enforced 600-second per-request limit and 3,600-second total inference-stage limit. Before launch, check these against observed baseline throughput and planned worst-case token bounds; if unsuitable, reduce scope or report BLOCKED rather than silently increasing limits. At a timeout, stop new scheduling, establish request settlement and checkpoint. A client timeout is not proof server work stopped.

Persist request intent before transmission and raw status/response immediately on return. Resume only never-started items under identical hashes; no automatic replay of uncertain delivery, transport failure or malformed output. A transport failure pauses the stage for diagnosis. Baseline records remain immutable.

Content-addressed cache keys must include inputs, official token identity, model/runtime/chat template, prompt, decoding, parser/projection and chunk/merge settings. Reuse exact matching artifacts only; report cold and cached costs separately.

Gold enters only a separate scoring phase after stage outputs are frozen.

## Scoring and selection

For each candidate and saved baseline on the identical cases, report:
1. All-subset token-level Spearman per language and macro using the frozen baseline failure convention. Explicitly label fallback-based scores.
2. Shared-usable-case Spearman for baseline/candidate, with exact counts per language and fallback-token accounting. Report no score if a meaningful denominator is absent.
3. Coverage: intended, attempted, returned, parseable, strictly valid, usable, partially projected, context overflow, truncation, malformed, transport failure and unresolved.
4. Calls, prompt/completion tokens, inference time, median/p95 latency and cache hits.
5. Paired differences with source-group bootstrap uncertainty (fixed seed and replicate count) where meaningful. A small sample or one source family is not evidence of general superiority.

Do not average per-document correlations as a replacement for the official global token-level per-language metric.

Predeclare selection: discard candidates with provenance/token-length defects or unsettled execution. Among remaining candidates require usable coverage at least as high as C0; select highest all-subset macro Spearman. If within 0.01, select the lower measured uncached inference-time configuration. Treat this as a practical selection heuristic, not statistical significance. If none qualifies, retain C0 or report no viable candidate; do not manufacture a winner.

Freeze the selected configuration and decision report before opening validation gold. Exploration outputs must not lead to unrecorded parser or fallback changes.

## Stage 2: validate once

Run only the selected configuration on the precommitted validation execution subset, using reserved calls and remaining total time. Re-score saved B0 predictions for those same IDs.

No validation-driven prompt edits, replacement cases or repeated winner selection. Failure is a finding, not permission to tune against validation. Report the candidate-versus-baseline result, uncertainty, coverage and cost. An inconclusive result remains inconclusive.

Distinguish operational improvement (more usable output) from semantic improvement on shared usable cases. Tiny or zero baseline scores make percentage improvements misleading; use absolute Spearman differences.

## Gate A: full-development comparison

After validation, deliver a reviewable package and an estimate based on measured tokens, chunk counts and local throughput. Default state: WAITING FOR OWNER GO, not automatically queued.

Propose one frozen candidate over the exact 489-case baseline manifest. Reuse byte-identical candidate outputs already generated; run only uncached matching cases. Reserve a numeric total wall-time/call budget before authorization. Report both uncached-equivalent cost and actual incremental cost.

Do not silently enlarge context or exclude long cases to beat the baseline. If the architecture chunks long inputs, describe this as a method change and measure its total calls/cost.

## Gate B: final test / submission

Separate explicit owner authorization and current organiser contract required. Before any test operation, verify whether the submission is already frozen or handed in. Do not read test content/labels, inspect earlier test responses, tune against known test failures, or launch a new final run as part of this development plan.

Final evaluation uses the frozen system once and the required official ordering/schema. The existing incomplete historical test run is not a development diagnostic for this plan. Never claim a small dev comparison replaces the test prediction deliverable or that cached dev replay proves live judge execution.

## Verification and handoff

Meaningful checks: test refusal before I/O; source-group partition disjointness; deterministic manifests; inference/gold separation; official token lengths/order; chunk coverage/merge correctness if used; evaluator parity; cache invalidation; durable interrupted intents and settlement; single-request enforcement; no artifact overwrites.

Maintain a small task ledger with base/commit, exact schedule, budgets, run IDs, statuses, artifact hashes and blockers. Store raw prompts/source-bearing artifacts privately; publish only permitted code, hashes and text-free summaries. Do not add tokens, credentials, model weights or copied test material.

At completion return:
- implementation commit and draft PR;
- exact commands actually implemented (do not invent a CLI in advance);
- baseline and candidate artifact hashes;
- subset table, selected method and honest validation verdict;
- deterministic re-score results and review status;
- stopped/settled workers and model-service ownership;
- full-dev estimate and Gate A decision request, if warranted.

Independent review is desirable only through a real bounded, read-only, credential-isolated route. Otherwise label self-review honestly. Do not claim orchestration, independent review, zero cost or autonomous monitoring without observed evidence.

## Local Codex start prompt

Read this document in full and inspect current repository, local runtime ownership, submission freezes, Weavr contract and PR #40 evidence first. Prepare the smallest reproducible dev-only runner around existing code. Freeze the source-grouped manifests, concrete candidates and exact request/time schedule before inference. Execute only Stages 0–2 within the stated budgets once preflight passes. Keep the baseline and submitted snapshot immutable. Stop at Gate A with measured evidence and a concrete full-run estimate. No automatic full-dev or test run, paid compute, merge, deployment or submission.
