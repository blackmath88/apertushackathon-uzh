# Research synthesis — semantic preservation, linguistic risks, and multi-pass document investigation

Date: 2026-10-13. Status: **literature intake / proposed decisions**, not new benchmark results. Source reports are archived below. This synthesis is a project interpretation of three separately supplied research reports; it does not independently verify every cited paper, benchmark number, repository activity status, model or artifact licence.

## Archive: original research reports

1. [Linguistic / Semantic Risk Atlas literature](2026-10-13-linguistic-semantic-risk-atlas-literature.md) — translation shifts, modality/negation/quantity/scope, TERMDAT and terminology rights, MQM/ACES/REFreSD, empirically grounded risk versus severity, B6 experiment protocol. User-provided external research; original source document was ~852 lines.
2. [Broad cross-lingual semantic detection and prior art](2026-10-13-crosslingual-semantic-detection-prior-art.md) — COMET/xCOMET/xCOMET-lite, MetricX, NLI, ACES, Vecalign, SimAlign, Prism, BARTScore, contrastive testing and alternative cross-disciplinary mechanisms. ~575 lines.
3. [Multi-pass semantic investigation/orchestration](2026-10-13-multipass-semantic-orchestration-literature.md) — conditional cascades, lazy/cached analyses, coarse-to-fine correspondence, typed intermediate evidence, controlled escalation, complete-token fallback, causal pass ablations. ~277 lines.

Files are readable copies of the supplied extracted reports. The original chat-upload byte artifacts are not represented as verified byte-identical copies: plain-text extraction can alter line metadata/whitespace; treat these as **transcriptions**. For original source integrity, link to the user-supplied report attachments and check the research citations at their original URLs before factual publication.

## Scientific state actually measured in our repository

- PR #17: B4 published **Qwen3-Embedding-4B DiffAlign** score-vectors cover frozen 30 allowed dev pairs, macro Spearman **0.187117**. **Zero Apertus calls** in this complete baseline.
- PR #19: B5 selector at five windows/doc yields **gold-informed diagnostic** macro 0.209271 versus B4 0.187117 (+0.022154), but matched random-region oracle ~0.208212, so targeted selection's advantage was unconvincing. This is *not* a deployable classifier or actual achieved prediction gain.
- PR #19: same regenerated embedding matrices: M0 max 0.188300; M1 reciprocal 0.184959, M2 Hungarian+NULL 0.179379, M3 local affine gap 0.177585. M1–M3 underperform M0. Regenerated M0 and published B4 are not numerically identical (upstream original revision not pinned).
- B5 Gate B **FAIL**, stage C **not executed**, no new Apertus inference. Do not confuse “B5 failed” with “Apertus verification performed poorly”—it has not been measured in B5.
- PR #21: profile-based government-crawl, synthetic capture/analysis and bilingual evidence viewer complete; **0 live federal content pages / 0 verified live pairs / 0 Apertus calls**, policy-blocked at BFE reuse review. This is separate from development-corpus experiments.
- UZH final judge/model compliance and publication/access rights remain independent submission gates. Held-out test split is off limits for further research; do not enumerate even test metadata.

## Principal convergence across the three reports

**Correspondence != equivalence.** A token can correctly align to a counterpart while its *semantic commitment* has changed (modality, permission, deadline, scope, negation, eligibility). Conversely an unmatched token can reflect normal paraphrase, morphology, structural reordering or version drift rather than a meaning error.

The useful hierarchy for investigation:

```
Immutable document originals + official tokens, stable offsets
  → cheap correspondence candidates (alternatives retained; null allowed)
  → independent observations:
        structural coverage / additions / omissions
        typed linguistic risk and explicit factual constraints
        optional specialist NLI / QE semantic evidence
  → fixed, gold-blind candidate triage
  → bounded Apertus contrastive judgment on unresolved, source-anchored cases
  → invariant full token vector, unchanged baseline fallback + evidence ledger
```

**Do not build this entire pipeline first.** An additional pass is justified only if matched ablations show new useful information. A conditional cascade with typed evidence is more testable than a multi-agent conversational orchestrator.

### Important distinctions

| Confusion | Required separation |
|---|---|
| Consequential construction vs frequent natural error | `impact_if_changed` and `P(error given construction)` are distinct. The latter requires denominator-aware empirical data; often unknown. |
| Embedding similarity vs semantic entailment | Alignment proposes where to compare; NLI/contrastive verifier tests directional support. |
| Contradiction vs omission/extra information | Directional `A entails B` and `B entails A` can differ without contradiction. |
| Linguistic cue vs verified semantic difference | Cue presence triggers investigation, not a score or public allegation. |
| Lexical router advantage vs Apertus advantage | B4, lexical-only, deterministic discrepancy and shuffled Apertus controls must share candidate footprint and budget. |
| Source faithfulness vs translation fluency | Use counterpart-ablation/shuffle and meaning-preserving controls. |
| Per-pair ratings vs four-language majority | Four versions can reveal inconsistent support; agreement is not legal truth, translation errors are correlated. |
| Semantic reviewer decision vs official token metric | A correct passage verdict may still be localized to wrong official tokens; keep projection independent. |
| Benchmark versus real government observatory | Benchmark uses dev gold and official Spearman; public observatory requires source rights, date/version, human review and alert precision. |

## Prior art to inspect before implementation

These are **research leads as described by supplied reports**, not new verified integration approvals. Confirm primary-paper findings, reproducibility, exact software/model/dataset licences and checkpoint revisions before adopting any dependency.

| Mechanism | Research/implementation leads | Testable use here |
|---|---|---|
| Token-level cross-lingual divergence | [Briakou & Carpuat 2020](https://aclanthology.org/2020.emnlp-main.121/), [xling-SemDiv](https://github.com/Elbria/xling-SemDiv) | Direct comparator and error taxonomy; note EN–FR/domain transfer |
| Linguistic contrastive sensitivity | [ACES](https://github.com/EdinburghNLP/ACES), [DEMETR](https://github.com/marzenakrp/demetr), [PAWS-X paper](https://aclanthology.org/D19-1382/) | False-confidence, modality, negation and paraphrase controls, not natural-error prevalence |
| Human translation error annotations | [WMT MQM](https://github.com/google/wmt-mqm-human-evaluation) | Error taxonomy and possible conditional-rate estimates only with denominator/sampling controls |
| Reference-free quality and error spans | [COMET/xCOMET](https://github.com/Unbabel/COMET), [xCOMET-lite](https://github.com/NL2G/xCOMET-lite), [MetricX](https://github.com/google-research/metricx) | Compete with DiffAlign/Apertus on anchored cases; verify source/translation assumptions |
| Lightweight directional reasoning | [multilingual mDeBERTa NLI](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) | Bidirectional entailment vs DiffAlign on explicit changed-commitment cases |
| Many-to-many registration | [Vecalign](https://github.com/thompsonb/vecalign), [Bertalign](https://github.com/bfsujason/bertalign) | Improve passage candidate discovery; no implied improvement in semantic score |
| Token alignment / multilingual parsing | [SimAlign](https://github.com/cisnlp/simalign), [Stanza](https://github.com/stanfordnlp/stanza) | Exact token links, clause/negation/morphology candidate observations |
| Source-conditioned likelihood | [Prism](https://github.com/thompsonb/prism), [Vamvas–Sennrich 2022](https://aclanthology.org/2022.acl-short.53/) | Candidate teacher-forced Apertus likelihood pilot; **generated-label logprobs are not prompt-token logprobs** |
| Runtime pass management | [MLIR pass-management documentation](https://mlir.llvm.org/docs/PassManagement/) | Typed observations, provenance, invalidation, memoization; *engineering analogy*, not NLP result |
| Terminology and legal constraint reference | [TERMDAT](https://www.termdat.ch/), Federal Chancellery guides | Small independently authored cues and source links; **bulk API/export/scraping/republication rights unverified** |

## Decisions: what is supported, what is merely proposed

1. **Supported by B4/B5 observations:** More restrictive token matching does not automatically improve final semantic ranking; our previous suspicious-region selector barely distinguished itself from random; raw baseline should remain the measured complete-coverage comparator.
2. **Supported by external prior-art descriptions, not yet by our sample:** Semantic evaluation, divergent-source-conditioned judgments and contrastive stress-testing are serious alternatives to global cosine scores. Published benchmark scores **cannot be transferred** to SwissGov-RSD.
3. **Testable hypothesis:** The B4 false-negative region includes strong alignments that conceal changes in obligations, numeric bounds, temporal reference or omitted conditions. A lexicon/constraint router could be better than score-only routing.
4. **Testable hypothesis:** A small non-Apertus NLI/QE comparator detects those relationships; Apertus's value must be measured relative to it and deterministic rules.
5. **Unknown:** Relative prevalence of these error types, native cross-language entailment accuracy, gain from four-way comparisons, teacher-forced Apertus logprob feasibility/latency, official score improvement.
6. **Product hypothesis:** Typed evidence from these operators may power a useful review viewer, but the live-page source-rights blockade must be independently resolved.

## Next test round — only one bounded sequence

### Stage 0 — inventory and freeze (no model)
Freeze existing 30 dev pair manifests, exact B4 published-score hashes, B5 selector and evidence hashes, scorer, source-family IDs, language coverage and legal data boundaries. Never broad-list or inspect protected test paths/metadata. Catalogue existing source/target offsets and candidate passage anchors. No mass model downloads; no new deployment.

### Stage 1 — error atlas, equal-budget routing (CPU)
Stratify B4 missed ranking outcomes by strongly matched contradiction, wrong occurrence, omission/addition, morphology/paraphrase, localization/projection and unresolved. When manually reviewing, annotate without gold visible until after evidence review. Freeze small independent EN/DE/FR/IT lexical rules for modality, polarity, numbers/dates, quantities/bounds, conditions, and protect a separate structural-omission budget. Compare **identical scored-token footprints** at five B5-style regions/document against B5 suspicious, cue-first and random. Report actual covered gold positives, under-ranked positives, random percentile, source-family bootstrap and permitted oracle diagnostic clearly labeled nondeployable.

**Stop** if candidate enrichment relative to matched random/B5 is not meaningful under a predeclared threshold. Do not endlessly tune on the repeatedly inspected 30 pairs.

### Stage 2 — specialist semantics, tiny contrastive set
If Stage 1 supports a useful risk stratum, evaluate a small pinned multilingual NLI model or a licensed compact error-QE model against a deterministic constraint check and original DiffAlign. Use genuine dev-based passages **separate from** synthetic good/bad perturbations, with matched fluency and source-swapped controls. Assess semantic verdicts independent of token score projection. No claim of improved benchmark accuracy from synthetic contrastive accuracy.

**Stop** if model does not actually use opposing-language evidence, or specialist/deterministic method matches or exceeds proposed added complexity.

### Stage 3 — local Apertus as contrastive verifier
Only if Stage 1/2 generate difficult, source-anchored distinctions with actual possible model value: use pinned local Apertus v1.5 8B and fixed alternatives (0 equivalent, 1 material difference, 2 unresolved, or a clearly defined pairwise choice), measure label and presentation order, counterpart removal/shuffle, fluency confounds, latency/compute. No long generated explanations or offsets. All output unselected/failed tokens retain B4 scores.

Compare **same candidate set, same scoring footprint**: unchanged B4; deterministic cues; specialist-only; shuffled Apertus; real Apertus. Report official macro/per-language Spearman, full coverage, tie burden, uncertainty by shared-EN source family, and net cost. Apertus contribution = real minus matched non-Apertus controls, not difference from B2 or random alone.

**Stop** if Apertus's real signal fails order/counterpart controls or produces no independent score gain.

### Stage 4 — orchestrator only after independent operator value
Do not preemptively build a trained router, evidence graph engine, agent debates, linguistic ontology or multi-model supervision layer. If two independent signals produce measured benefit, implement **one fixed-gate conditional cascade** with typed `EvidenceRecord`, preserved source offsets, explicit invalidation, deterministic replay, budget caps and baseline full-coverage fallback. Compare to always-run and matched-random policies.

## Submission-critical rule

Hack Apertus submission due **2026-10-16 12:00 CEST**. A new B6 experiment must not hide or displace outstanding actual end-to-end judge and model-use acceptance checks. B4 alone is **Qwen-based and not an Apertus-only submission**. Zero test-split inspection. Experimental insight and publication-ready judge artifact are separate deliverables.

## Decision not to make

Do not infer we should deploy B6 from three research reports. The reports yield credible hypotheses and reusable comparison targets; they supply **no new measured SwissGov or Apertus uplift**. This research branch stores evidence and a proposal; no mission dispatch, model compute, crawl, merge, release or code experiment is authorized by this archive.
