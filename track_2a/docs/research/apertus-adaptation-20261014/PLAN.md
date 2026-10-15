# Queued plan: frozen Apertus scoring and optional learned head

Status: PREPARED / NOT RUN. Owner requested repository preservation and planning, not execution.
Companion: README.md; originals: reports/.
Documentation base: PR29 at 24dbac1f4f06ac287052bd350f3797ee418595c6. This ancestry is not the runtime implementation base.

## Question
Does a small scorer trained over frozen Apertus representations improve original-token RSD over a fixed training-free scorer using identical features?

## Pickup and evidence refresh
Read repo instructions, current Observatory/Weavr state where available, and blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md. Inspect actual host processes, leases/worktrees and newest baseline/prompt/translation results. Record READY / WAITING / SUPERSEDED / BLOCKED with exact commits.
Protect the running baseline and submission work. Do not infer idle from missing remote updates.
Revise this proposed design from new evidence before freezing; preserve old-to-new rationale. Never change a running protocol silently.
No Mission dispatch, Need waiver, merge, deployment or paid compute is implied by this plan.

## Stage 0 — preparation, no model execution
- Locate existing unquantized checkpoints and establish model/conversion lineage, hashes, tokenizer/template and runtime versions.
- Verify permitted data schema/splits from safe documentation/dev metadata only. Never enumerate or open protected test/full artifacts or third-party predictions.
- Build an exposure ledger distinguishing fixed inference from adaptive inspection.
- Group source families from verified English source identity/content; do not assume numeric ID suffix alone proves correspondence.
- Separate fit, selection and reserved evaluation families. If too few remain, use a predeclared nested group design or report an exploratory pilot. No arbitrary minimum of 96 families.
- Pin implementation paths, licences and dependencies; inspect hidden-state extraction and output mapping before reuse.
Deliver capability proposal, data manifest and numeric budget. New weights/runtime installation require a concrete resource plan under existing owner authority; no downloads authorised by this document alone.

## Stage 1 — synthetic capability gate (after local execution is authorised)
Maximum one loaded checkpoint/runtime, three synthetic bilingual fixtures, two sequence lengths (128 and 512), two repeated forwards each: 12 forwards total. One worker, no competing GPU load; 30-minute wall ceiling including loading, no automatic retry.
Measure actual device/free memory and host RAM. Use a supported device/precision/attention path; do not assume CUDA settings work on XPU. Abort on OOM/nonfinite states/unsupported operations; do not disturb other services.
Verify selected hidden-state index convention, dimensions, finite values and repeatability within a declared numerical tolerance. Do not require bitwise GPU determinism.
Test original-token mapping on punctuation, accents, repeated words, long/chunked text and empty counterpart. Exact two-sided output lengths, finite scores and complete token coverage are required.
If blocked, archive evidence and defer; do not automatically switch provider or download another model.

## Stage 2 — freeze C and B protocol
Candidate C-mid (layer15, externally suggested) and C-final use the same tokenizer, chunking, pooling and cross-document cosine scoring; at most two layers, no layer sweep. Treat the externally development-selected layer as disclosed prior information.
Keep source tokens intact; compare against the whole counterpart after stitching, not same-index chunks only. Record lost context from chunking.
For each direction, C scores one finite value per original token. Define clamping/pooling before scoring. Include no-match diagnostics without claiming alignment is truth.
B is one shared linear sigmoid head over fixed matched token-pair features (source, counterpart, absolute difference, elementwise product, similarity and margin). Freeze dimensionality, normalization and regularization using fit data only. Document best-match errors as a limitation.
Use continuous gold with soft-target BCE or MSE: choose ONE before launch. Normalize loss per official token/family so subword count and document length do not silently determine all weighting.
At most four configurations (two layers x two declared learning rates), one seed, maximum ten epochs each; early stopping uses selection families only. No synthetic-data expansion, LoRA, language-specific heads, extra smoothing or stacking in this pilot.
Choose one B and one C using selection data, then evaluate each once on the reserved partition. Also report fixed C alternatives transparently. No selection from final results.

## Stage 3 — bounded pilot execution
Before launch, commit exact manifests/configurations and numeric limits for forwards, cache size, wall time and host memory derived from Stage1 throughput. This plan is not an unlimited extraction authorisation.
One extraction pass per unique source text/config where safe; immutable caches keyed by text, checkpoint, layer, precision, tokenizer, chunking and code hashes. English cache reuse requires verified identical inputs.
Train head on cached features, preferably CPU when feasible. Preserve all configurations, failures and chosen-checkpoint lineage.
Stop at the frozen ceiling; no silent retries or replacement examples. New evidence informs a later separately frozen iteration.

## Evaluation and claims
Use the official dev scoring semantics: global Spearman pooling eligible tokens on both sides per language, then unweighted mean of the three. Assert IDs, order, lengths and finite values BEFORE scoring; no padding/truncation repairs or silent case dropping.
Prevent evaluator fallback to full/test paths. Add focused tests for this boundary and token mapping during implementation.
Compute paired family-cluster bootstrap deltas (fixed seed/resample count declared before evaluation). Report per-language scores, coverage/failures, extraction and training time, memory/storage, and inference cost.
Compare prompting baseline only on the same families and disclose checkpoint/quantization/runtime differences. B versus C with identical features is the isolated adaptation contrast.
No fixed +0.02 threshold is mandated: predeclare a practical promotion criterion and uncertainty interpretation appropriate to sample size. If uncertainty includes no gain, mark inconclusive.
Protected test remains untouched. No development pilot constitutes hidden-test evidence.

## Deliverables
- Dated evidence refresh and scope decision.
- Versioned protocol, exposure ledger and family manifests.
- Synthetic capability report with measured resources.
- Minimal isolated extraction/scoring/head implementation and relevant tests.
- Immutable feature/prediction/checkpoint manifests, all failures and reproducible commands.
- Report: supported / not supported / inconclusive, separating feasibility from accuracy.
- Draft PR and explicit next action; no automatic merge or submission.

## Deferred
Generative LoRA/QLoRA and two-tower adapter training remain later routes. Revisit only after data, runtime and measured B/C benefit justify them. A custom head is not an ordinary llama.cpp/GGUF text-generation deployment.
