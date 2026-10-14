B5 is **not yet the best justified next implementation**. Before spending calls on verifying local DiffAlign matches, test whether correcting those matches has enough oracle headroom; independently, replace DiffAlign’s unrestricted per-token maximum with a **capacity-constrained alignment model containing an explicit NULL state**. The current evidence suggests that DiffAlign’s scoring rule—not merely its embeddings—may be the largest removable error source.

# Adversarial Research Review

## Core judgment

The most important conceptual change is this:

> Do not model semantic difference as “low similarity to something.” Model it as **semantic mass that cannot be consistently explained by the other document**.

DiffAlign independently lets every token choose its most similar token anywhere in the opposite document. That creates the observed repeated-name, generic-word, and date failures because many source tokens may reuse one convenient target occurrence. An unbalanced or sequence-constrained global matcher instead forces candidate correspondences to compete, permits NULL alignment, and exposes posterior uncertainty. Research on unbalanced optimal transport identifies null alignment as central to detecting semantic inequality, while OTTAWA uses forward/reverse null alignments to localize omissions and hallucinations. [speakerdeck](https://speakerdeck.com/yukiar/13-unbalanced-optimal-transport-for-unbalanced-word-alignment)

# Part I — What was missed

## Five consequential weaknesses

### Gold localization conflates tasks

The gold-oracle results show what happens **after knowing which tokens differ**. Exact binary locations scoring 0.999 demonstrates that severity contributes little once perfect positive support is supplied; it does not prove that boundary localization is practically harder than deciding whether a proposition differs.

The sentence oracle at 0.534 is equally important. Even a coarse representation could substantially exceed the current 0.187 if its semantic decisions were sufficiently accurate. The correct conclusion is therefore:

- Exact localization has enormous theoretical value.
- Coarse representations have a lower ceiling.
- The experiments have not established whether practical errors come mainly from candidate detection, semantic judgment, correspondence errors, or projection.

An oracle-intervention study must separate these factors before choosing B5.

### DiffAlign lacks competition

The published score

\[
d_i=1-\max_j \cos(h_i,h_j)
\]

treats every token independently. It has no concept of:

- Target-token capacity.
- Repeated occurrences.
- Monotonic document structure.
- Contiguous omissions.
- One-to-many phrases.
- A NULL correspondence.
- Competition between plausible explanations.

Consequently, ten source tokens may all be “explained” by the same target token. A date may match an unrelated occurrence elsewhere, and a generic word may erase evidence of a local omission.

This is not simply an embedding problem. It is a **global assignment problem disguised as nearest-neighbor retrieval**. OTAlign’s 2023 results show why partial and unbalanced transport are particularly useful when null alignments are frequent; OTTAWA’s 2024 method likewise models null correspondences explicitly and uses directional disagreement for word-level hallucination and omission detection. [arxiv](https://arxiv.org/html/2406.01919v1)

### B3 measured serialization failure

B3 produced 42 accepted outputs from 219 calls, with 153 rejected because rationales were too long. That primarily falsifies the output contract, not Semantic Decision Middleware or Apertus’s semantic ability.

The label and rationale should have been separate channels:

```text
Completion 1: exactly one constrained label token.
Completion 2: optional explanation, never used for scoring.
```

A response should not become invalid because an irrelevant explanation exceeded an arbitrary length. B3’s zero complete semantic coverage is operationally important, but it is not evidence that decomposition failed semantically.

### Apertus probabilities remain unvalidated

Sixteen successful one-token calls establish:

- Grammar-constrained inference works.
- Candidate-label probabilities are accessible.
- Latency is acceptable.
- Free-form generation is unnecessary.

They do not establish:

- Probability calibration.
- Ranking utility.
- Cross-language consistency.
- Incremental information beyond alignment margin.
- Stability under label renaming.
- Stability under passage order.
- Correlation with benchmark annotations.

Sensitivity to label mapping and passage order is evidence that raw label probabilities combine semantic evidence with verbalizer priors, prompt-position effects, and possibly asymmetric attention. Apertus should therefore be tested through **contrastive likelihood ratios**, not accepted winning labels.

### Token count creates false sample size

The benchmark contains many token observations, but learned methods still have roughly 30 independent development documents in the fixed sample. Tokens within one sentence or document are highly correlated.

A ranker trained on thousands of token pairs can therefore look data-rich while effectively fitting a few documents. Random token splits, token-level confidence intervals, and unrestricted hyperparameter search would substantially understate uncertainty.

The benchmark metric also differs from real-world monitoring:

| Objective | What it rewards |
|---|---|
| Global Spearman | Correct ordering across all eligible tokens |
| Event recall | Finding each discrepancy at least once |
| Recall at review budget | Putting useful evidence among the first \(k\) reviewed tokens |
| Severity-weighted event recall | Finding high-impact discrepancies |
| Alert precision | Avoiding analyst fatigue |
| Calibration | Making confidence operationally meaningful |

Word-level quality-estimation research commonly uses MCC, F1, and ranking-oriented explainability metrics rather than assuming one correlation metric captures every operational goal. A benchmark improvement can coexist with worse observatory behavior. [arxiv](https://arxiv.org/html/2403.14118v1)

# Part II — Six lenses

## Lens A: First principles

### Proposal: alignment-free information gain

Spearman requires only a useful ordering of tokens. It does not require an explicit source-to-target alignment, span ontology, or explanation.

For each token \(x_i\) in document \(X\), use Apertus in teacher-forced scoring mode to compare:

\[
\ell_i^{+}
=
\log p(x_i \mid x_{<i}^{\text{local}},Y)
\]

against controls:

\[
\ell_i^{0}
=
\log p(x_i \mid x_{<i}^{\text{local}})
\]

\[
\ell_i^{-}
=
\log p(x_i \mid x_{<i}^{\text{local}},Y_{\text{control}})
\]

where \(Y\) is the opposite-language document and \(Y_{\text{control}}\) is an unrelated same-domain document or a block-permuted control. Define cross-document support as:

\[
I_i=(\ell_i^{+}-\ell_i^{0})-(\ell_i^{-}-\ell_i^{0})
\]

and difference score as a robustly normalized inverse of \(I_i\).

### Causal mechanism

If the other-language document contains information supporting a token, conditioning on it should improve that token’s likelihood more than conditioning on an unrelated control. Unsupported dates, entities, modal verbs, and omitted propositions should receive less cross-document information gain.

This tests an alignment-free hypothesis: the model need not identify where the evidence occurs, only whether the opposite document helps explain a token.

### What needs semantics

Semantic interpretation is needed for:

- Paraphrases.
- Cross-lingual lexical variation.
- Modality and negation.
- Implicit arguments.
- Scope and specificity.

No deep semantics is required for:

- Token rarity.
- Position.
- Repetition.
- Number and date normalization.
- Exact entity recurrence.
- Layout and list structure.
- Candidate competition.

### Failure modes

- A strong same-language prefix may already predict the token, masking cross-document effects.
- Apertus may not use a long foreign-language prefix productively.
- Common words may receive little informative variation.
- Teacher-forced prompt-token probabilities may require a lower-level llama.cpp interface.
- Long prompts may make the experiment slower than one-token classification.

### Small test

Run only on:

- Gold-positive tokens.
- Matched controls from the same sentences.
- Number, entity, negation, and modality subsets.

If AUROC or within-document pairwise accuracy does not beat token frequency and DiffAlign residuals, stop. Do not build a full pipeline.

## Lens B: Inversion

### Proposal: equivalence peeling

Do not search for differences first. Iteratively remove tokens that have strong certificates of equivalence.

#### Certificate hierarchy

1. Normalized exact values: dates, currencies, percentages, identifiers.
2. Entity aliases and acronym expansions.
3. High-margin mutual nearest neighbors.
4. Reciprocal word alignments stable across two embedding models.
5. Phrase correspondences supported by neighboring matches.
6. Tokens inside proposition pairs that Apertus judges mutually entailing.
7. Low-information function words attached to an already certified phrase.

Each accepted certificate removes or discounts semantic mass on both sides. Later rounds operate only on unexplained residue.

### Scoring

For token \(i\), define its equivalence evidence:

\[
E_i=\sum_k w_k c_{ik}
\]

where \(c_{ik}\) is support from certificate type \(k\). Its initial anomaly score is:

\[
s_i=1-\max E_i
\]

Then add:

- Residual mass from global alignment.
- Directional disagreement.
- Neighborhood inconsistency.
- Symbolic contradiction evidence.

### Causal mechanism

Positive difference detection is difficult because relevant differences are sparse and diverse. Equivalence has repeatable high-precision witnesses: reciprocal matches, identical values in corresponding roles, and mutually entailing local claims. Removing confidently explained material changes the class distribution of the remaining problem.

### Critical safeguard

Peeling must be conservative. A false equivalence certificate destroys a real difference and prevents later recovery. Every certificate therefore needs:

- A high-precision threshold.
- Provenance.
- A reversible score discount rather than hard deletion in the first implementation.
- An ablation measuring the damage from each certificate type.

### Counterfactual test

For a proposed equivalence, substitute a nearby plausible alternative—another date, entity, or modal expression. If the certificate survives the counterfactual, it is probably relying on generic similarity rather than the claimed semantic identity.

## Lens C: Philosophy of language

### Proposal: administrative countermodels

The useful philosophical construct is not “word meaning”; it is whether one description allows a materially different world or citizen action from the other.

Compile local clauses into a deontic event frame:

```text
actor
authority
action
object
beneficiary
permission-or-obligation
polarity
condition
deadline
quantity
location
exception
consequence
```

Then test two directional questions:

1. Can Passage A be true while Passage B is false?
2. Can Passage B be true while Passage A is false?

A difference exists when Apertus or deterministic logic can construct a countermodel in either direction.

### Philosophical translation

- **Frege:** Normalize reference separately from predication. Two names may share a referent while claims about that referent differ.
- **Wittgenstein:** Administrative meaning is partly use; classify what a citizen or authority may, must, or can do.
- **Grice:** Keep asserted information separate from merely plausible implication. A system should not silently fill an omission using world knowledge.
- **Speech-act theory:** “May apply,” “must submit,” and “is eligible” perform different administrative functions even when topical content overlaps.
- **Possible-world semantics:** Mutual entailment approximates equality of admissible worlds.
- **Information theory:** A changed frame slot is surprising relative to the otherwise corresponding event.

### Causal mechanism

Many severe differences occupy only one slot:

- `may` versus `must`.
- 30 June versus 31 July.
- residents versus citizens.
- eligible versus automatically enrolled.
- federal authority versus cantonal authority.

Frame mismatch localizes evidence directly to the source tokens filling that slot.

### What is implementable now

Do not build a general semantic parser. Implement deterministic extractors for:

- Numbers and dates.
- Negation.
- German, French, Italian, and English modal inventories.
- Condition markers.
- Obligation and permission expressions.
- Named entities.

Apertus receives only unresolved slot comparisons and returns one token:

```text
0 = same constraint
1 = materially different constraint
2 = cannot determine
```

### Philosophical metaphor to reject

“Model the complete possible-world semantics of government documents” is not a two-day algorithm. The testable contribution is the restricted deontic-frame hypothesis.

## Lens D: Cross-domain analogy

### Proposal: semantic pair-HMM

Borrow the transferable mechanism from biological sequence alignment, not merely its terminology.

Government language versions often preserve broad order while allowing:

- Local substitutions.
- Insertions and deletions.
- One-to-many translations.
- Contiguous omitted blocks.
- Occasional reordered sections.

Construct a pair hidden Markov model with states:

```text
M = semantic match
S = semantic substitution
GX = gap in X
GY = gap in Y
R = block restart or reorder
```

Emission costs combine:

- Cross-lingual embedding similarity.
- Lexical or dictionary evidence.
- Entity type.
- Normalized number/date identity.
- Dependency role.
- Local positional compatibility.

Use affine gap penalties:

\[
C_{\mathrm{gap}}(k)=g_{\mathrm{open}}+k g_{\mathrm{extend}}
\]

This makes a contiguous omitted paragraph cheaper than dozens of unrelated one-token mismatches.

### Output

Run forward–backward inference rather than only Viterbi decoding. For each token, compute:

\[
s_i=P(G_X\ \text{or}\ S \mid X,Y)
\]

or the corresponding target-side probability. Posterior entropy supplies alignment uncertainty.

### Causal mechanism

- A repeated name can no longer explain unlimited occurrences for free.
- Dates compete with other dates.
- Local order helps select the correct occurrence.
- Omitted blocks become explicit gap states.
- Soft posterior scores naturally support ranking.

### Alternative: unbalanced transport

If reordering is too common for sequence alignment, use partial or unbalanced optimal transport over token or phrase embeddings with:

- Explicit NULL mass.
- Capacity constraints.
- A position regularizer.
- Entropic regularization.
- Forward/reverse disagreement.

OTAlign provides an implementation of unbalanced alignment, while OTTAWA applies an adaptive null vector to word-level hallucination and omission detection. AWESoME Align provides a strong contextual word-alignment implementation and combines directional scores, although its published experiments found probability thresholding stronger than its OT extraction in that setup. [aclanthology](https://aclanthology.org/2021.eacl-main.181.pdf)

### Engineering recommendation

Implement the smallest formulation locally rather than integrating an entire research stack:

- `scipy.optimize.linear_sum_assignment` for a hard capacity-constrained control.
- Dynamic programming for affine-gap alignment.
- Python Optimal Transport for partial or unbalanced transport if dependency review permits.
- Existing Qwen token embeddings to isolate the matching algorithm.

Verify every repository’s current license before copying code; paper availability does not imply reusable implementation licensing.

## Lens E: Adversarial proof

### Proposal: invariance-stable token scoring

A credible semantic score should remain stable under transformations that preserve the relevant meaning.

Generate transformed inputs:

- Swap document order.
- Rename output labels.
- Duplicate an unrelated generic sentence.
- Replace formatting-equivalent dates.
- Move a paragraph without changing its text.
- Add a repeated entity mention elsewhere.
- Remove surrounding context.
- Add surrounding context.
- Replace entities with consistent typed placeholders.

For each token, calculate the mean score and instability:

\[
\bar{s}_i=\frac{1}{T}\sum_t s_i^{(t)}
\]

\[
v_i=\operatorname{Var}_t(s_i^{(t)})
\]

Use a conservative robust score:

\[
s_i^{*}=\bar{s}_i-\lambda v_i
\]

for positive evidence, or route high-variance tokens for adjudication.

### Causal mechanism

The transformations isolate nuisance dependence:

- If duplicating a name elsewhere changes its original score, matching is occurrence-insensitive.
- If swapping languages changes a symmetric equivalence decision, the classifier is directionally biased.
- If adding context reverses a decision, short tasks may be underspecified.
- If renaming labels changes probabilities, verbalizer priors dominate.

### Assumptions this can falsify

| Assumption | Adversarial intervention |
|---|---|
| Localization dominates | Give oracle candidate regions but retain real semantic decisions |
| Alignment is a strong foundation | Add distant duplicate names and dates |
| Apertus probabilities are semantic | Rename labels and swap order |
| Shorter is better | Sweep local, paragraph, and document context |
| Rankers generalize | Use document splits and label-permutation controls |
| Spearman means useful alerts | Compare event recall and review-budget recall |

This is both a scientific test and a possible ensemble: retain only evidence stable under meaning-preserving transformations.

## Lens F: Constraint removal

### Three counterfactual systems

| Environment | Best architecture |
|---|---|
| Unlimited compute, Apertus 8B only | Cross-document likelihood contrast, controlled mutations, repeated order/context checks, and posterior aggregation |
| Frontier reasoning, 20 calls | Deterministic candidate lattice; batch only the 20 highest-impact unresolved proposition groups; require cited token IDs |
| No LLM | Symbolic normalization, competitive NULL-aware global matching, reciprocal alignment, and continuous residual ranking |

### Shared components

The parts surviving all three environments are:

- Original-token provenance.
- A candidate correspondence lattice rather than one hard alignment.
- An explicit NULL or unexplained state.
- Continuous token evidence.
- Directional analysis.
- Deterministic structural features.
- Uncertainty measurement.
- Complete-coverage fallback.
- Separate benchmark ranking and operational alert metrics.

### Proposal: semantic checksum

For each local unit, compute several independent “checksums”:

```text
embedding checksum
entity/value checksum
deontic checksum
sequence-position checksum
Apertus entailment checksum
cross-document likelihood checksum
```

A token becomes suspicious when several checksums disagree with the claimed correspondence. This resembles error-correcting codes: no single detector must reconstruct meaning perfectly; inconsistency among partially redundant views localizes corruption.

### Causal mechanism

A genuine number change should trigger:

- Value mismatch.
- Local alignment residual.
- Directional entailment failure.
- Possibly Apertus counterfactual sensitivity.

A harmless paraphrase may trigger lexical residual but pass the other checks. The pattern of disagreement matters more than any one absolute score.

# Part III — Competing architectures

## Deterministic system

### NullAlign-DP

**Input:** Two official token arrays and contextual token embeddings.

**Intermediate representation:** A sparse lattice of candidate token and phrase correspondences, plus NULL edges.

**Processing:**

1. Normalize dates, numbers, entities, whitespace, and punctuation.
2. Produce contextual token embeddings.
3. Retain top-\(k\) local candidates per token.
4. Apply capacity-constrained matching or pair-HMM inference.
5. Use affine gaps for contiguous additions and omissions.
6. Run both directions.
7. Convert posterior gap, substitution, and directional-disagreement probabilities into continuous token scores.
8. Add symbolic mismatch bonuses.

**Inference responsibilities:** Embeddings propose semantic compatibility; deterministic global optimization decides the consistent explanation.

**Output:** One complete finite score vector per document side.

**Failure modes:**

- Legitimate paragraph reordering.
- Semantically equivalent phrases with little embedding similarity.
- Multiple valid alignments.
- Nonlocal coreference.
- Pragmatic differences with nearly identical words.
- Poor subword-to-official-token aggregation.

**Reproducibility:**

- Cache embeddings with model revision and checksum.
- Record embedding-generation time and hardware.
- Freeze top-\(k\), positional penalty, and gap parameters.
- Produce exact command lines.
- Evaluate all 30 documents.
- Report both cached replay and full end-to-end cost.

**Apertus requirement:** This architecture alone does not satisfy a meaningful-Apertus requirement. For submission, Apertus can adjudicate a small, predefined subset of high-entropy gap/substitution states, but the deterministic score must remain a reported standalone ablation.

## Apertus verifier

### Contrastive lattice adjudication

Do not ask “Are these passages different?” Present an actual local competition.

For source phrase \(a\), the matcher supplies:

- \(b_1\): current best counterpart.
- \(b_2\): best alternative.
- NULL: no material counterpart.

#### Contract

```text
Which option best accounts for all material information in A?

0 = B1
1 = B2
2 = neither; A contains material information absent from both
3 = insufficient context

A: ...
B1: ...
B2: ...
Answer:
```

Run the reversed question for each target-side candidate. Use one constrained output token and candidate-label probabilities.

### Intermediate representation

A candidate lattice with:

- Deterministic edge costs.
- Alignment margin.
- Position.
- Symbolic compatibility.
- Alternative correspondence.
- NULL edge.
- Apertus likelihood ratios.

### Scoring

Let:

\[
r_i =
\log p(\text{NULL}\mid a_i,b_1,b_2)
-
\log p(b_1\mid a_i,b_1,b_2)
\]

Combine this with deterministic residual using one fixed coefficient or document-level cross-validation:

\[
s_i=d_i+\lambda r_i
\]

### Why it is better than B5 as stated

A binary verifier can say “different” because the passages are unrelated, misaligned, underspecified, or genuinely contradictory. Contrastive adjudication asks the model to choose among the hypotheses the alignment system is actually considering.

### Failure modes

- Candidate alternatives may omit the true match.
- Label priors may still dominate.
- Local snippets may lack coreference context.
- The correct relationship may be one-to-many.
- Apertus may prefer fluent or lexically similar options.
- Scores may not be calibrated across languages.

### Required controls

- Passage-order reversal.
- Label permutation.
- Deterministic alignment-margin replacement.
- Randomly permuted Apertus scores within language and margin decile.
- No-Apertus candidate lattice.
- Full 30-document coverage.

## Unconventional system

### Semantic mutation tomography

**Input:** Opposite-language passage \(Y\), source passage \(X\), and deterministic candidate tokens in \(X\).

**Intermediate representation:** Controlled one-edit mutants of \(X\).

For each candidate:

- Replace one number with a nearby value.
- Replace an entity with another same-type entity.
- Insert or remove negation.
- Replace permission with obligation.
- Narrow or broaden a quantifier.
- Delete one condition or list item.

Apertus compares the original and mutant against \(Y\):

```text
Which English passage is closer in meaning to the German passage?

0 = original
1 = modified
2 = indistinguishable or uncertain
```

Define mutation sensitivity:

\[
m_i=
\log p(\text{original}\mid Y)
-
\log p(\text{mutant}_i\mid Y)
\]

Interpretation:

- Large positive \(m_i\): the original token is supported by \(Y\).
- Near-zero \(m_i\): \(Y\) does not distinguish the semantic feature.
- Negative \(m_i\): the mutation may actually agree better with \(Y\), suggesting a real difference.

### Causal mechanism

The two candidates share almost all wording and context. Topic, style, length, and most syntax cancel, leaving one controlled semantic variable.

Counterfactual NLP methods commonly define explanations as minimal edits that flip a model decision, and token importance can be measured by the change caused by deletion or replacement. Here the mechanism is inverted: controlled edits probe which source facts are supported cross-lingually. [aclanthology](https://aclanthology.org/anthology-files/anthology-files/pdf/paclic/2023.paclic-1.88.pdf)

### Failure modes

- Mutation operators may generate unnatural text.
- Some values cannot be changed independently.
- A model may detect implausibility rather than cross-lingual mismatch.
- Calls scale with candidate count.
- Low sensitivity does not necessarily imply a genuine difference.

### Reproducibility

- Predefine mutation operators.
- Reject malformed mutations deterministically.
- Store every original–mutant pair.
- Use identical label permutations and passage-order controls.
- Report results separately by mutation type.
- Never train on mutations and evaluate on the same templates without document separation.

# Part IV — Falsification experiments

## B5 oracle ceiling

### Hypothesis being tested

Correcting suspicious DiffAlign correspondences has enough potential effect on token ranks to justify an Apertus verifier.

### Recipe

1. Freeze the proposed B5 candidate selector without using gold labels.
2. For every selected token group, enumerate the score adjustments B5 could make:
   - Keep current score.
   - Promote.
   - Demote.
   - Select alternative match.
   - Choose NULL.
3. Use gold labels only in this diagnostic experiment to choose the adjustment maximizing Spearman.
4. Evaluate the resulting optimistic oracle on all 30 documents.
5. Repeat at budgets of 1, 3, 5, and 10 candidate groups per document.

### Baselines

- DiffAlign 0.187117.
- B2 full-sample zero-default 0.129306.
- Oracle adjustments on randomly selected token groups.
- Oracle adjustments on highest raw DiffAlign scores.
- Oracle adjustments on alignment-margin candidates.

### Measurement

- Maximum attainable macro Spearman.
- Per-language ceiling.
- Fraction of gold-positive tokens reachable by selected groups.
- Damage caused by projection outside selected groups.
- Candidate budget versus attainable gain.

### Stop condition

Abandon B5 if even the optimistic oracle cannot produce a practically meaningful improvement at the intended call budget. A sensible preregistered threshold is an absolute macro gain of 0.02; the precise threshold should be fixed before seeing results.

This is the smallest experiment capable of invalidating B5 without making a single model call.

## Matching-rule replacement

### Hypothesis being tested

DiffAlign’s unrestricted maximum, rather than embedding quality, causes a substantial share of its errors.

### Recipe

Reuse exactly the same cached Qwen3 token embeddings and compare:

1. Independent maximum cosine: current DiffAlign.
2. Mutual-nearest-neighbor score.
3. Hungarian assignment with dummy NULL nodes.
4. Banded dynamic programming with affine gaps.
5. Partial or unbalanced optimal transport.
6. Each method with and without a positional prior.

No Apertus calls and no new embeddings are permitted in the primary comparison.

### Fixed parameter policy

Use:

- Literature defaults where available.
- A small predefined grid.
- Leave-one-document-out or language-stratified document folds.
- One final out-of-fold prediction per token.

### Measurements

- Full-sample macro Spearman.
- Per-language Spearman.
- Duplicate-target reuse.
- Number/date cross-occurrence error rate.
- Forward/reverse disagreement.
- Score-tie fraction.
- Runtime and peak memory.

### Stop conditions

- If every competitive matcher is no better than max cosine, candidate competition is not the immediate bottleneck.
- If one improves consistently in at least two languages without learned gold features, build B5 on that matcher rather than raw DiffAlign.
- If position regularization helps one language and hurts another, use language-specific fixed structural parameters only with document-level validation.

This experiment directly tests the strongest independent alternative to B5.

## Apertus incremental-value test

### Hypothesis being tested

Apertus label probabilities contribute semantic information not already encoded by alignment margin, lexical overlap, position, and symbolic features.

### Candidate set

Choose three suspicious contiguous groups per document using a frozen, gold-independent selector: 90 groups total.

For each group, provide:

- Current match.
- Best alternative.
- NULL.
- Enough local context to resolve references.
- A second run with passage order and label mapping changed.

This produces approximately 180 one-token calls.

### Experimental arms

| Arm | Score correction |
|---|---|
| A | No correction |
| B | Deterministic logistic rule from alignment and symbolic features |
| C | Apertus contrastive likelihood ratio |
| D | Apertus probabilities shuffled within language and margin decile |
| E | Winning Apertus label only |
| F | Order-averaged and prior-corrected Apertus probabilities |

Use the same candidate groups and the same fixed fusion coefficient across all arms. If a coefficient must be learned, generate strictly out-of-fold predictions by document.

### Measurements

- Full-sample macro and per-language Spearman.
- Candidate-level pairwise accuracy where gold supplies a defensible ordering.
- Label-permutation stability.
- Passage-order stability.
- Incremental gain over Arm B.
- Coverage and fallback frequency.
- Fraction of improvement attributable to one document.
- Paired document bootstrap intervals, described as uncertainty estimates rather than definitive significance tests.

### Stop condition

Reject the verifier hypothesis if Arm C or F fails to beat:

- The deterministic Arm B.
- The shuffled-probability Arm D.
- The no-correction Arm A.

Apertus should also improve at least two language pairs or show a clearly interpretable language-specific effect. “All outputs were valid” is not a positive semantic result.

# Part V — Challenge to B5

## When B5 could work

B5 can improve full-sample Spearman if all of the following hold:

1. DiffAlign’s candidate set contains the relevant counterpart or NULL option.
2. Suspicious candidates cover enough rank-relevant errors.
3. Apertus discriminates true correspondence from lexical coincidence.
4. Its likelihood ratio is more informative than alignment margin.
5. Corrections change token ordering rather than merely rescaling scores.
6. Projection localizes the decision without promoting large irrelevant passages.
7. Model failures fall back to unchanged DiffAlign scores.

The use case most favorable to Apertus is not an obviously unaligned token. It is a **near-tie where two candidates are lexically plausible but differ in semantic role**.

## Why B5 may fail

### Candidate conditioning

The verifier cannot repair an absent candidate. If DiffAlign sends an unrelated pair, Apertus may correctly reject it without identifying the real correspondence.

### Local-context ambiguity

Shorter inputs reduce output and attention burden but can remove:

- Pronoun antecedents.
- Defined terms.
- Heading scope.
- List membership.
- Temporal context.
- Which occurrence of an entity is intended.

Short input is an engineering property, not a semantic guarantee.

### Probability contamination

Label probability includes:

- Semantic evidence.
- Token prior.
- Label ordering.
- Position.
- Passage order.
- Prompt wording.
- Option-length and fluency effects.

The relevant feature is a calibrated contrast or likelihood ratio stable under these transformations.

### Metric mismatch

Changing a few candidate scores may improve local decisions without altering enough global ranks to change Spearman. Conversely, aggressively promoting uncertain candidates can damage many positive–zero pair orderings.

### Foundation risk

B5 assumes independent suspicious alignments can be repaired one by one. But the failure may be global: repeated matches and omissions cannot be resolved consistently without making candidate edges compete.

## Isolating Apertus

A valid claim requires:

\[
\Delta_{\text{Apertus}}
=
\rho(\text{deterministic features + Apertus})
-
\rho(\text{same deterministic features})
\]

The comparison must hold constant:

- Candidate selection.
- Projection.
- Symbolic features.
- Fusion.
- Token coverage.
- Failed-call behavior.
- Sample.
- Quantization and endpoint configuration.

Further controls are essential:

- Replace Apertus output with alignment margin.
- Shuffle Apertus outputs within comparable candidates.
- Replace probabilities with a constant.
- Use winning labels instead of probabilities.
- Permute label mappings.
- Swap passage order.

Only the difference between the matched Apertus and no-Apertus arms is an Apertus contribution.

## Smallest valid test

The smallest benchmark-connected test is:

- All 30 fixed documents.
- Three candidate groups per document.
- One contrastive three-option call per group.
- One swapped-order/label-permutation call per group.
- Approximately 180 one-token calls.
- One frozen fusion formula.
- Six matched arms from the incremental-value experiment.
- Complete deterministic fallback.

Given the observed median call latency, model generation cost is minor; candidate construction and prompt evaluation will dominate. This experiment is small enough to run once without broad hyperparameter search and large enough to reveal whether Apertus probabilities move full-sample ranks.

# Part VI — Recommendation

## Experiment ranking

Scores are qualitative: 5 is best, except effort, compute, and overfitting risk where 5 means greater cost or risk.

| Rank | Experiment | Information | Effort | Compute | Overfit risk | Benchmark potential | Apertus evidence |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | B5 oracle-intervention ceiling | 5 | 1 | 1 | 2 | Diagnostic | 1 |
| 2 | NULL-aware competitive matcher | 5 | 3 | 2 | 2 | 5 | 1 |
| 3 | Apertus contrastive lattice test | 5 | 2 | 2 | 3 | 4 | 5 |
| 4 | Alignment-free information-gain pilot | 4 | 3 | 4 | 2 | 3 | 5 |
| 5 | Semantic mutation tomography | 4 | 3 | 3 | 3 | 3 | 5 |

## Immediate experiment

Run the **B5 oracle-intervention ceiling** first.

It can terminate B5 in one or two hours. If the selected suspicious groups do not contain enough correctable rank mass, no prompt, calibration scheme, or classifier improvement will make that candidate policy useful.

This is a decision experiment, not a submission method.

## Backup experiment

Replace independent max-cosine matching with a **NULL-aware competitive matcher using the same cached embeddings**.

Begin with two simple controls:

1. Hungarian assignment with dummy NULL nodes.
2. Banded affine-gap dynamic programming.

Only then add unbalanced transport. A simple constrained matcher that improves on DiffAlign would be more valuable than a sophisticated verifier built on defective correspondences.

## Meaningful Apertus test

If the B5 ceiling is high, run the 180-call contrastive lattice experiment. Apertus should choose between the current match, a concrete alternative, and NULL; it should not answer an abstract `SAME/DIFFERENT` question.

Do not add a learned ranker until the raw Apertus likelihood ratio demonstrates incremental information. Otherwise the ranker can conceal a zero-value Apertus feature behind deterministic gains.

## Post-hackathon idea

Develop the **administrative countermodel/deontic-frame system**.

For a Zürich observatory, “Do both pages permit the same citizen actions under the same conditions?” is more operationally meaningful than token correlation. Frames can support:

- Difference-event explanations.
- Risk-weighted alerts.
- Historical version tracking.
- Human verification.
- Explicit rights, duties, deadlines, eligibility, and exception monitoring.

It is defensible computational semantics, but too broad for the submission deadline.

# Independent first move

An independent attempt to outperform B0–B4 should first replace DiffAlign’s independent nearest-neighbor rule with a **position-regularized, NULL-aware global alignment model producing posterior mismatch probabilities**.

The reasons are concrete:

- It preserves the strongest observed component: multilingual embeddings.
- It directly attacks the documented repeated-name, generic-word, and date failures.
- It produces complete predictions without generation.
- It handles omissions as a first-class state.
- It generates continuous token scores suited to Spearman.
- It distinguishes embedding quality from matching-algorithm quality.
- It creates better-defined, high-entropy decisions for Apertus.
- It requires no additional large model and little compute.

Apertus should then adjudicate only ambiguous lattice states through contrastive one-token choices. If Apertus cannot beat deterministic margins and shuffled-probability controls there, the honest conclusion is to abandon Semantic Decision Middleware as the principal source of accuracy and retain Apertus only where a narrow, measurable contribution can be demonstrated.