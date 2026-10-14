# Alternative prompting — bounded local experiment workstream

Date: 2026-10-14. Status: experiment design and seed prompts, not measured results.
Owner reports full-dev baseline running. Do not restart, alter or compete with it.
Prepared from PR #27 docs; inspect current runtime/implementation state before execution.

## Research question

Can changes to instructions and examples improve local Apertus's official token-level semantic-difference ranking, while preserving reliability and reasonable cost?

Freeze the paper baseline unchanged. Prompt optimisation is a separate candidate method, never a retrospective baseline repair. No new agent framework, fine-tuning, automatic tool selection or live adaptive memory is needed for this first workstream.

## New evidence affecting design

PR #28 B8 report was inspected on 14 October:
- local-only 234 attempts; teacher/transfer arms not run;
- R2 accuracy 0.7222 vs R0 0.3333 on provisional synthetic cases;
- overall valid outputs 183/234, source sensitivity reported 0.0000;
- directional reversal metric needs equivariance, not literal same-label agreement.
B8 remains INCONCLUSIVE. Context is a plausible factor, not proven benchmark gain.
Before reusing controls, inspect their implementation and expected semantics. Do not assume every source removal must change an answer.

## Literature intake (primary records checked)

All takeaways below are design inspiration, not replication or evidence of Apertus improvement. No claimed percentage gain is transferred to SwissGov-RSD.

| Source | Verified takeaway | Application |
|---|---|---|
| Ramnath et al., https://aclanthology.org/2025.emnlp-main.1681/ (earlier user-provided full survey) | Candidate generation, evaluation, selection and iteration are distinct design decisions | Freeze search space, objective and budget |
| Li et al., https://arxiv.org/abs/2502.11560 | Broader optimisation framing, primary record retrieved | Background; no soft prompts in this workstream |
| Cui et al., https://arxiv.org/abs/2502.18746 | Instruction search taxonomy includes targets, criteria and operators | Define precisely what each variant changes |
| GEPA, https://arxiv.org/abs/2507.19457 | Reflection proposes and tests prompt edits; retains complementary candidates | One bounded feedback round with preserved lineage, not a GEPA replication |
| TRAS, https://arxiv.org/abs/2507.09839v2 | Feedback from successful examples regularises error-driven edits | Diagnose successes and failures; protect working clauses |
| MemAPO, https://arxiv.org/abs/2603.21520 | Stores reusable strategies and error patterns | Append-only experiment notebook; freeze it before evaluation |
| SAPO, https://arxiv.org/abs/2608.11219 | Segment-level edits address regressions from wholesale rewrites | Edit one instruction block per candidate |
| Agent self-improvement survey, https://arxiv.org/abs/2607.13104 | Extends optimisation to prompts, memory, tools and control | Broader background, deferred here |

SEPO arXiv:2608.28067 could not be verified through direct retrieval/search in this session. Treat its supplied numerical superiority claims as unverified; do not use them to justify this protocol. Other numerical claims in the Consensus attachment were not independently audited. The attachment is a discovery aid and is not copied into the repo.

Apertus Translate README explicitly includes SwissGov in combined evaluation data. Do not import its examples/corpus without overlap verification confined to allowed data. Never inspect protected test to perform that check.

## Phase A — make the experiment reproducible, offline

Read repository instructions, current Weavr ownership if applicable and current baseline/B8 state. Follow CHATGPT-OPERATING-CONTRACT.md. Use an isolated worktree. Do not modify baseline runner/configuration while its run is active.

Implement minimal candidate injection around existing B2 rendering in a new module, preserving baseline prompts.py and its frozen parser/projection. Pin:
- exact local model hash/runtime, decoding, cap and context settings;
- unchanged full document inputs and official tokens;
- unchanged B2 schema, severity scale, locator and projection;
- insertion point for additional instructions before document A;
- scorer, failure convention and dataset manifests.

B2 is chosen as a readily available output contract, not declared the best current method. If its frozen output cap makes this experiment uninformative, report the limitation; do not change the cap mid-search. A representation/schema/cap experiment must be separately named.

Use the adjacent seed specification. Materialise exact P0/P1/P2/P3 prompt files/hashes before calls. Validate format and expected synthetic projections offline. No grammar-constrained generation or JSON repair in this prompt-only comparison.

## Phase B — split and freeze before search

Use permitted dev data only. Never access test content or metadata. Inference receives no labels.

Respect existing dev/train and dev/val membership if provided, then group by shared English source and known duplicate families. Keep all sibling translations in one partition. Record experimental exposure from B0-B8. Already inspected cases are not fresh holdout.

Define optimisation and reserved validation manifests before looking at new per-case baseline scores. Baseline generation over all dev is compatible with this, but do not feed reserved validation outputs/errors into prompt selection. If validation has already influenced development, label the result exploratory, not independent generalisation.

For the first screen, select up to 12 source families from optimisation by deterministic hash order, retaining every available EN-DE/FR/IT sibling: maximum 36 pairs. No short-document or score-based filtering. Smaller pools are recorded, not padded with validation examples.

## Phase C — bounded instruction/example comparison

P0 unchanged B2 control.
P1 P0 + semantic commitments instruction.
P2 P0 + bidirectional comparison instruction.
P3 P0 + synthetic contrastive demonstrations.
These are separate edits, not cumulative. All use same input, schema, projection, runtime and decoding.

Budget: at most 144 initial task calls (4 x up to 36 pairs).
Run one request at a time only after baseline positive settlement. Never infer settlement from a missing PR or transient idle GPU.

Rank candidates by official macro Spearman pooled across tokens within each language, with fixed punctuation handling and failure convention. Do not replace it with mean document correlation or classification accuracy. Record valid coverage and token cost beside ranking.

## Phase D — one feedback round, optional within this workstream

At most two additional candidates P4/P5, each editing one block of the best seed. Use the optimisation subset only. Build a feedback packet containing:
- representative semantic errors;
- successful cases whose behaviour must be retained;
- format/projection failures separately from semantic errors;
- measured deltas and affected languages;
- explicit protected schema/scale/length instructions.

Use at most 4 local critic/editor calls, maximum 2048 output tokens each. Apertus may propose edits; the scorer decides. No frontier/cloud provider assumed or authorised. Reject proposals that embed benchmark case answers, change the task/schema or exceed 300 added words.

Evaluate P4/P5 on the identical optimisation screen: at most 72 task calls. Retain all rejected candidates and costs. No more rounds or automatic prompt search.

Memory is an append-only ledger: parent hash, edited block, hypothesised error, optimisation evidence, regressions and disposition. It is not retrieved or updated during validation inference.

## Phase E — freeze finalist and check robustness

Choose exactly one finalist using optimisation results before reserved validation. If all are worse, retain P0 and report negative findings. Use score first among candidates with no worse parseable coverage than P0; resolve exact ties by fewer total tokens, then candidate ID. Report all candidates regardless.

Create 12 new, human-checked diagnostic cases (4 per language; balanced equivalence/change and directional omission) before model calls. Freeze expected transformations, not just labels. Diagnostics are separate from official benchmark gold. If no qualified human check is available, label provisional and do not certify semantic reliability.

For P0 and the finalist run original, reversed passages, and an explicitly changed counterpart: 72 calls total. Reversal must swap A/B evidence and ADDITION/OMISSION as appropriate while preserving CHANGE. Counterpart edits must demonstrably change the gold relation/localisation; do not demand arbitrary differences on source removal.

Report exact-schema validity, directional equivariance, correct original/edited decisions and source sensitivity. Diagnostic promotion gate: >=11/12 correct for originals, >=11/12 correct for edited counterparts, >=11/12 reversal-equivariant, >=35/36 parseable per prompt. These small-sample gates are screening criteria, not population guarantees. Failure prevents semantic reliability claims even if benchmark score rises.

## Phase F — locked validation and comparison

Run P0 and the single frozen finalist on all reserved dev-validation pairs (2V calls, V fixed in manifest). Reuse saved identical P0 outputs only if every relevant input/config hash matches. Re-score the completed paper baseline over this same validation manifest as an external comparator. B2-versus-paper comparisons change the pipeline; finalist-versus-P0 isolates prompt changes.

Primary result: paired delta in official macro Spearman, with English-family cluster bootstrap (2000 resamples, seed 0); report per-language scores, coverage, fallback/invalid counts, latency and tokens. Predeclare how undefined bootstrap correlations are handled and report their frequency. Do not drop failed documents after seeing scores.

Claim supported prompt improvement only if held-out delta CI95 lower bound >0, coverage is no worse, and diagnostics pass. Otherwise report inconclusive/negative or ranking-only exploratory evidence as appropriate. Do not choose a different finalist or tune after seeing validation. Full-dev aggregate may also be descriptive, not independent validation.

## Execution ceiling and deliverables

Maximum first-workstream calls: 144 + 72 + 4 + 72 + 2V = 292 + 2V, no retries.
Reuse reduces actual calls; count all critic/diagnostic calls. Freeze exact V, resulting cap, numeric per-request timeout and total wall-clock ceiling before execution using observed local throughput. Do not launch without that execution manifest. No new paid compute, downloads, test access, publication, merge or Weavr dispatch.

Checkpoint each intent/response. Pause on transport failure or uncertain live ownership; do not repeat possibly-live requests. Preserve baseline/B0-B8 artifacts byte-for-byte. Raw benchmark text stays in existing private storage; repo receives code, hashes and appropriate summaries.

Deliver:
1. exact prompts, manifests, run config and provenance;
2. append-only candidate/feedback ledger;
3. official scores and uncertainty, all failures and costs;
4. diagnostic control report;
5. reproducible offline re-score instructions and draft PR;
6. clear implemented/tested/executed/reviewed status.

This preparation adds no model calls. Local execution follows the owner's handoff after the current baseline has settled.
