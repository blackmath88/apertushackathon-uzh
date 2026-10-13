Yes—document-level semantic comparison can plausibly benefit from orchestrated, repeated examination, but the strongest research support is for **selectivity**, not simply for adding more passes. Existing work supports coarse-to-fine alignment, bounded reranking, conditional inference, explicit error localization, and acquisition of informative features. It does not establish that a general multi-agent controller improves multilingual document-difference detection with complete token coverage. Those are related mechanisms, not interchangeable proofs of the proposed system. [github](https://github.com/thompsonb/vecalign)

My recommendation is to start with architecture B—a conditional cascade—while retaining evidence in the style needed for architecture C. Use a fixed pipeline as the reference implementation and matched control. Promote an evidence-driven controller only if selecting the next examination demonstrably beats a simpler, budget-matched gate.

## 1. What the research establishes—and what remains unproven

The core question has three distinct parts:

1. Where should the system examine next?
2. What different information should that examination produce?
3. How should that information change the final prediction?

These should be measured separately. Multi-stage ranking already separates candidate generation, pointwise scoring, and pairwise comparison; active feature acquisition explicitly studies choosing which additional measurement to obtain based on current observations and acquisition cost. Neither requires conversational agents. [arxiv](https://arxiv.org/html/1910.14424v1)

An important distinction is between computational refinement and additional semantic evidence:

- Vecalign’s coarse-to-fine dynamic programming makes alignment tractable; refinement is not necessarily another model’s semantic judgment. [github](https://github.com/thompsonb/vecalign)
- Bertalign’s second pass searches around anchors identified by the first pass; the passes have different responsibilities, but depend on substantially the same embedding evidence. [github](https://github.com/bfsujason/bertalign)
- An LLM verifier can introduce a different judgment, but only if it contributes information beyond alignment confidence and linguistic features.
- A fusion layer can improve prediction without revealing anything new: it may merely calibrate or combine existing signals.

The last two points are hypotheses to test, not benefits to assume.

I did not identify, in this investigation, a validated open-source system satisfying all six of your requirements together: typed passes, retained evidence, conditional execution, information-targeted LLM calls, complete token coverage, and independently measured pass contributions. The useful precedents are modular.

## 2. Research and implementations worth reusing

### Coarse-to-fine document and sentence alignment

| Research / implementation | Established mechanism | Relevance and limitation |
|---|---|---|
| `thompsonb/vecalign` | Multilingual sentence embeddings; embeddings of consecutive-sentence concatenations; approximate dynamic programming with linear time and space in document sentence count. | A practical document-to-sentence alignment backbone. Its repository also supplies order-sensitive document embeddings and proposes rescoring document candidates. Alignment similarity is not itself a semantic-difference label.  [github](https://github.com/thompsonb/vecalign) |
| `bfsujason/bertalign` | First identify approximate one-to-one anchors; then constrain a second dynamic-programming search to recover one-to-many, many-to-one and many-to-many alignments. | A particularly direct example of passes with different responsibilities. Its paper reports better F1 than earlier methods on two Chinese–English literary alignment datasets; that does not establish accuracy on government-document semantic differences.  [github](https://github.com/bfsujason/bertalign) |
| `cisnlp/simalign` | Word alignment from contextual embeddings, with different alignment extraction methods, without parallel training. | Useful for sentence-to-token refinement and directional views. The repository reports English–German F1 of .81 for mBERT-Argmax versus .77 for eflomal, and approximately 15–20 seconds for 500 sentence pairs on a GTX 1080 Ti. These are alignment measurements, not discrepancy detection measurements.  [github](https://github.com/cisnlp/simalign) |
| `neulab/awesome-align` | Extract multilingual BERT word alignments; optionally fine-tune on parallel data. | An alternative token-alignment component. Reported German–English alignment error rate falls from 17.4 without fine-tuning to 15.1 in one multilingual fine-tuning configuration. Model adaptation and inference orchestration must not be conflated.  [github](https://github.com/neulab/awesome-align) |

The reusable idea is a constrained alignment lattice with explicit alternatives—not a sequence of increasingly confident summaries.

### Multi-stage retrieval and reranking

`castorini/duobert` implements an established division of labor: retrieve candidates, score them independently with monoBERT, then compare selected candidates pairwise with duoBERT. The paper reports that reranking 20 candidates reaches near-maximum effectiveness with roughly 40% additional inference latency over monoBERT alone; larger candidate sets more than double the inference count in the discussed configurations. Component ablations show contributions from both BERT stages. [arxiv](https://arxiv.org/html/1910.14424v1)

For document comparison, the transferable mechanism is:

> Generate several plausible correspondences cheaply; reserve expensive comparison for deciding among them.

Do not transfer retrieval’s aggressive pruning unchanged. A search system may discard irrelevant candidates; your system must still return a score for every required token.

### Conditional inference, budgeted computation and selective prediction

`stanford-futuredata/FrugalGPT` learns cascades of models under budget constraints. Its paper reports matching the best individual model with up to 98% cost reduction, or improving accuracy over GPT-4 by 4% at the same cost, on its evaluated tasks. These are task-specific API-cost results, not an expected saving for a local 8B semantic verifier. [arxiv](https://arxiv.org/abs/2305.05176)

SelectiveNet jointly learns prediction and rejection, evaluating performance over the accepted subset. Its paper finds advantages over MC-dropout at coverage rates below .9 in the discussed setting. Its implementation is linked as `geifmany/SelectiveNet`. [arxiv](https://arxiv.org/pdf/1901.09192.pdf)

For your task, reinterpret rejection as escalation:

- Selective prediction coverage: how much the stronger component handles.
- Output coverage: whether every input token receives a final prediction.

The former may be low; the latter must remain complete.

### Error localization and iterative translation evaluation

`Unbabel/COMET` provides xCOMET, which predicts sentence quality and localized error spans with severity. The paper reports state-of-the-art performance across sentence-level, system-level and error-span evaluation, together with stress tests for localized critical errors and hallucinations. The implementation exposes error annotations and supports JSON export. [aclanthology](https://aclanthology.org/2024.tacl-1.54/)

`xu1998hz/InstructScore_SEScore3` produces structured diagnostic reports containing error type, location, severity and explanation. Its research includes automated evaluation of explanation failures and further training on feedback. This is an important qualification: iterative improvement occurs partly during training, not evidence that repeated runtime critique is automatically beneficial. [ar5iv.labs.arxiv](https://ar5iv.labs.arxiv.org/html/2305.14282)

`dayeonki/mt_feedback` connects error annotation to LLM post-editing, using InstructScore or xCOMET annotations. It is an implementation precedent for localized feedback directing a later action—not proof that generating a corrected translation improves detection on the unchanged originals. [github](https://github.com/dayeonki/mt_feedback)

For discrepancy detection, keep originals immutable. A generated correction may be a hypothesis, never replacement evidence.

### Compiler-inspired analysis management

MLIR provides an unusually relevant engineering precedent:

- Analyses compute information without modifying the represented operation.
- Analyses are obtained lazily and cached.
- Passes explicitly declare which analyses remain preserved.
- Potentially stale analyses are invalidated after transformations. [mlir.llvm](https://mlir.llvm.org/docs/PassManagement/)

This supports a small pass manager with declared dependencies, cached observations and explicit invalidation. It does not justify implementing a compiler infrastructure for prose, and it supplies no NLP accuracy evidence.

The practical adaptation is modest: typed records, stable source offsets and provenance. If segmentation or alignment changes, invalidate dependent views; retain their historical records rather than silently replacing them.

### Evidence graphs, linguistic rules and neural-symbolic reasoning

`thunlp/GEAR` aggregates multiple evidence sentences through a graph for fact verification. Its paper reports a FEVER test score of 67.10%. This establishes an evidence-aggregation mechanism, not adaptive selection of the next analysis pass. [ar5iv.labs.arxiv](https://ar5iv.labs.arxiv.org/html/1908.01843)

`krishnamrith12/ProoFVer` generates natural-logic proofs through sequences of claim spans, evidence spans and semantic relations. It offers a more concrete precedent than unconstrained “reasoning”: intermediate relations participate in the decision mechanism itself. Its repository contains training and inference code. [arxiv](https://arxiv.org/html/2410.03341v1)

Snorkel offers another useful abstraction: independent labeling functions return a label or abstain, and their noisy outputs are combined into probabilistic labels. Research explicitly considers source accuracy and correlation; linguistic checks and model judgments should not be counted as independent votes simply because they came from different functions. [pmc.ncbi.nlm.nih](https://pmc.ncbi.nlm.nih.gov/articles/PMC5951191/)

These approaches suggest retaining both:

- Observations: aligned numbers, detected negation, candidate correspondences.
- Hypotheses: changed obligation, missing exception, alternate alignment, insufficient context.

An evidence graph can initially be a table of these relations. A graph neural network is unnecessary.

### Uncertainty-driven acquisition and multilingual views

Active feature acquisition is the closest established formulation of “which examination is worth doing next?” It selects additional measurements per instance while trading predictive benefit against acquisition cost. `a-norcliffe/SEFA` provides an implementation using stochastic latent representations to score candidate acquisitions. This is supervised machinery; a small development dataset may not justify training it. [arxiv](https://arxiv.org/html/2502.11067v1)

`AkariAsai/self-rag` and `s-nlp/AdaRAGUE` provide adaptive retrieval implementations. Self-RAG uses learned retrieval and critique tokens; its project reports strongly task-dependent effects of reduced retrieval—approximately a 40% relative performance drop on PopQA versus 2% on PubHealth. AdaRAGUE evaluates 27 uncertainty methods and cautions that out-of-distribution robustness differs across answer performance, self-knowledge and efficiency. [selfrag.github](https://selfrag.github.io/)

For multilingual consistency, “Found in Translation” studies a translate-then-evaluate approach. This provides a second view, but introduces translation fidelity as another uncertainty source; agreement after translation is not independent confirmation of the originals. [arxiv](https://arxiv.org/pdf/2505.21999.pdf)

Use direct alignment, reversed direction and third-language views as disagreement detectors. Treat three-language agreement as corroboration, not majority-vote ground truth.

## 3. Comparing the three architectures

The published numbers below come from different tasks and metrics. They cannot be ranked as if they were results on one multilingual discrepancy benchmark.

| Dimension | A. Fixed pipeline | B. Conditional cascade | C. Evidence-driven orchestration |
|---|---|---|---|
| Execution | Every unit receives the same analyses. | Cheap observations gate a predetermined deeper stage. | Current evidence determines which action to acquire next. |
| Measured precedent | monoBERT/duoBERT demonstrates independently useful stages and a measurable latency–effectiveness tradeoff.  [arxiv](https://arxiv.org/html/1910.14424v1) | FrugalGPT demonstrates substantial task-specific cost reductions; SelectiveNet demonstrates risk–coverage optimization.  [arxiv](https://arxiv.org/abs/2305.05176) | Active feature acquisition and adaptive retrieval demonstrate selective acquisition, but do not establish your complete document/token system.  [arxiv](https://arxiv.org/html/2502.11067v1) |
| Cost model | Predictable sum of stage costs. | Cheap base cost plus escalation frequency × expensive cost. | Variable action costs plus controller overhead and potentially repeated examinations. |
| Error propagation | Early alignment errors can contaminate every later stage. | The same issue, plus false-negative gates that prevent repair. | Can reopen alternatives if retained; can also repeatedly reinforce a wrong shared hypothesis. |
| Implementation complexity | Lowest; simplest tracing and ablations. | Moderate: calibration, routing and fallback policy. | Highest: action selection, stopping, dependency management and evidence reconciliation. |
| Main failure modes to test | Unhelpful passes; wrong local context; fusion double-counting. | Confidently wrong cheap detectors; distribution-shifted gates; rare errors never escalated. | Misestimated information value; correlated disagreement; looping; unnecessary calls; controller overfitting. |

For B and C, these failure modes are proposed evaluation targets unless tied to a cited study—not claims that the exact failures have already been measured on your documents.

Multi-agent debate is a weak default for C. A comparative study finds that debate does not reliably outperform self-consistency and ensembling, while another study documents correct answers becoming incorrect through peer reasoning and agreement pressure. Different personas do not guarantee different evidence. [raw.githubusercontent](https://raw.githubusercontent.com/mlresearch/v235/main/assets/smit24a/smit24a.pdf)

The simpler interpretation of C is therefore a controller selecting between concrete analyses—not agents discussing the document.

## 4. How to orchestrate document → sentence → span → token examination

The following is a proposed adaptation of the established mechanisms above, not an existing validated end-to-end framework.

### Minimal pass contracts

| Pass | Responsibility | Typed output | Conditional behavior |
|---|---|---|---|
| 0. Inventory | Preserve originals, offsets, tokens, document structure and language metadata. | `TokenInventory`, `StructureMap` | Always run. |
| 1. Correspondence | Propose section/sentence matches, alternatives and NULL matches. | `AlignmentCandidates` | Always run; widen search where correspondence is ambiguous. |
| 2. Local observations | Measure lexical alignment, quantities, entities, polarity, modality and unmatched spans. | `EvidenceRecord[]` | Run inexpensive checks broadly. |
| 3. Triage | Distinguish likely mismatch, alignment ambiguity and unresolved semantic relation. | `RouteDecision` | Select a bounded next action or stop. |
| 4. Targeted examination | Test one specific ambiguity against original text and competing candidates. | `HypothesisAssessment` | Local 8B call only on selected units. |
| 5. Projection/fusion | Convert evidence to final token scores. | `TokenPrediction[]` | Always run, with baseline fallback. |

Every evidence record should contain source document IDs, original offsets, pass/model version, dependency IDs, observation or hypothesis type, score semantics and cost. Separate a model probability from a calibrated confidence estimate.

Retain competing alignment candidates rather than overwriting the first match. A semantic verifier should be able to answer “neither candidate” or “insufficient context.”

### Narrowing must not become irreversible pruning

Use coarse structure to define an initial search region, not an absolute semantic boundary. A low-cost alignment pass may misplace a moved paragraph, merge distinct obligations or omit a sentence. Later disagreement should permit one bounded widening action.

For more than two documents:

1. Maintain pairwise correspondence evidence.
2. Check whether pairwise matches are mutually compatible.
3. Flag inconsistent correspondences for examination.
4. Never infer that the majority language version is necessarily correct.

A “difference” may be asymmetric inclusion rather than contradiction. Typed hypotheses should distinguish equivalence, contradiction, additional content, missing content, alignment error and unresolved relation.

### Complete token coverage

Initialize the final output with the existing embedding baseline’s score for every required token. Subsequent passes add evidence and may update selected scores.

Enforce these invariants:

- Stable token identifiers and original offsets.
- One final prediction per required token.
- Explicit NULL alignment for unmatched material.
- Recorded mappings from model subwords to benchmark tokens.
- Baseline fallback on skipped analyses, invalid LLM responses and timeouts.
- Separate flags for “unexamined,” “examined and unchanged,” and “examined but unresolved.”

This prevents the system from improving apparent accuracy by silently dropping hard cases.

## 5. One small, falsifiable experiment

### Question

Does cheap disagreement-based routing place a fixed number of local 8B examinations where they improve token predictions more than random selection—and does the LLM contribute information beyond linguistic features and score fusion?

Use the current embedding scorer unchanged. If this continues your Apertus work, use the same local 8B checkpoint and inference setup already under evaluation; do not change alignment, model or dataset simultaneously.

### Freeze the experiment

Freeze:

- Permitted multilingual development documents and original tokenization.
- Embedding baseline and candidate alignment.
- Model checkpoint, precision, prompt, context cap and output format.
- Candidate examination units.
- Routing rules, budgets, fusion family and primary metric.

Partition by document family: translations, related pages and near-duplicates stay together. Fit any thresholds or fusion weights inside grouped training folds, then evaluate out of fold. If the dataset is too small, use predetermined thresholds and report descriptive uncertainty rather than presenting tuned development performance as generalization.

### One bounded LLM examination

Define one unit as a baseline candidate sentence/block pair, with fixed nearby context.

Ask the 8B model to assess:

- Equivalent content.
- Contradiction.
- Additional or missing content.
- Incorrect correspondence.
- Insufficient evidence.

Use a short constrained response. If requesting affected spans, require exact source offsets or validate extracted quotations against the originals. Invalid localization falls back to the unchanged token scores.

No free-form document critique, post-editing or debate.

### Matched controls

| Arm | Purpose |
|---|---|
| E | Unchanged embedding baseline. |
| E + F | Add only cheap linguistic features. Measures feature contribution. |
| E + L-random | LLM on randomly selected units under a fixed budget. Measures extra inference without informed routing. |
| E + F + L-random | Same random units and LLM budget, plus features. |
| E + L-routed | Route using embedding margin, directional disagreement and unmatchedness; no linguistic features. |
| E + F + L-routed | Add linguistic features to routing and prediction. |
| E + F + L-all | Fixed pipeline: examine every unit. Measures attainable benefit and cost, not a budget-matched competitor. |
| E + F + shuffled-L | Shuffle LLM outputs within compatible language/length strata before identical fusion. Tests whether LLM content, rather than an extra variable or calibration flexibility, contributes. |

Use identical LLM prompts and context rules in all LLM arms. Match random and routed budgets by calls and total input/output tokens as closely as possible; stratify random selection by language pair and unit length. Report residual cost differences.

A practical way to keep this small is to infer once over all eligible units, cache responses, and replay routing policies over that fixed pool. Count hypothetical deployed costs separately from the experiment’s total computation. This isolates selection effects without changing the LLM answer between policies.

### Separate inference from fusion

For each relevant evidence set, compare:

1. A preregistered simple update rule.
2. Baseline-score-only calibration using the same supervised fitting protocol.
3. A small regularized fusion model incorporating features and/or LLM outputs.

The decisive comparisons are:

- Routing: routed versus random, with the same features, fusion and budget.
- Linguistic features: E + F versus E, and paired LLM arms with/without F.
- Additional model inference: real LLM outputs versus shuffled outputs and no-LLM controls.
- Fusion: learned fusion versus simple updates and baseline-only calibration.

If supervised fusion alone explains the improvement, that is useful—but it is not evidence that repeated examination uncovered new semantics.

### Metrics and decision rules

Use the official benchmark metric as primary. If that remains token-level Spearman, report it at the required aggregation level rather than replacing it with binary detection accuracy.

Also report:

- Paired document-level metric changes and bootstrap intervals.
- Per-language-pair performance.
- Full token coverage and invalid-response rate.
- Routed share of units and tokens.
- Calls, input/output tokens, GPU time and wall time.
- Helpful versus harmful score updates.
- Performance by alignment ambiguity and error category, where annotations permit.

Predeclare a small budget, such as 20% of eligible units, and one practical-effect threshold.

Interpret outcomes as follows:

- Routed beats random at matched cost: evidence for useful routing.
- Features improve scores but LLM outputs do not: retain the linguistic pass; reject the verifier for this role.
- All-unit LLM helps but routing does not: verifier has potential, gate is inadequate.
- Fusion helps equally with shuffled outputs: no demonstrated semantic contribution from the LLM.
- No LLM arm helps: reject this prompt/action, rather than adding debate rounds.
- Different actions help different strata: justification for a later, small C-versus-B experiment.

## 6. Recommended implementation boundary

Reuse Vecalign or Bertalign for structural correspondence, SimAlign or awesome-align for token correspondence, MLIR’s analysis-preservation ideas for bookkeeping, and the cascade/feature-acquisition literature for budgeting. These are established components and mechanisms; none alone is your final system. [github](https://github.com/thompsonb/vecalign)

Build only a pass registry, immutable evidence records, a simple gate and a coverage-preserving scorer.

The first scientific target should be narrowly stated: at the same inference budget, does selecting a different examination site reveal information that changes token ranking correctly? Until that is demonstrated, an elaborate evidence controller or multi-agent architecture adds complexity without establishing the contribution you care about.