The next experiment should **not** be B5 inference. First run a gold-isolated **router-conditioned rank-error tomography**: determine whether the tokens B5 would route are capable of repairing a meaningful portion of DiffAlign’s Spearman loss. If that ceiling is low, B5 is structurally misdirected regardless of Apertus quality; if it is high, test Apertus by asking it to **rank competing anomaly hypotheses**, not classify isolated pairs.

# Denkraum Traverse

## Dealing procedure

The deal used the 20 move IDs exactly as defined in [`moves.js`](https://github.com/blackmath88/denkraum/blob/main/denkraum/data/moves.js):

1. Sort IDs lexicographically.
2. Start at one-based position 16, from the October 16 deadline.
3. Advance seven positions, wrapping after 20; seven is the number of letters in “Apertus.”
4. Stop after six distinct moves.

This produced positions 16, 3, 10, 17, 4, and 11:

1. `re-enter` — Re-enter.
2. `constellate` — Constellate.
3. `historicize` — Historicize.
4. `refuse-the-metaphor` — Refuse the metaphor.
5. `demote` — Demote.
6. `interpose` — Interpose.

The selection contains four bricolage and two arsenal moves. It was fixed before applying any move to SwissGov-RSD.

The repository marks every selected move’s lineage `verified: false`. Those philosophical and historical attributions therefore remain explicitly unverified here; the technical hypotheses do not depend on their historical accuracy. This follows Denkraum’s rule that an attribution remains weak until its source has actually been checked, and that a structurally valid return remains a proposal rather than canonical state ([README](https://github.com/blackmath88/denkraum/blob/main/denkraum/README.md), [`constellation.js`](https://github.com/blackmath88/denkraum/blob/main/denkraum/data/constellation.js)).

# I. Traverse log

## Re-enter

### The move

- **ID:** `re-enter`
- **Operational form:** “Apply the distinction to itself. Put the operation back into the space it operates on.”
- **Repository lineage:** Spencer-Brown, Luhmann, and penetration testing; unverified.
- **Summons:** The paradox reappears one level higher.

### Apply it

B4 treats alignment as a directional operation: each token searches for support in the other document. Re-entry applies correspondence to itself:

> If token \(x_i\) maps to \(y_j\), does \(y_j\) map back to \(x_i\)?

This transforms alignment from an individual similarity lookup into a **cycle-consistency system**.

DiffAlign’s maximum-similarity rule can assign many source tokens to the same repeated name, date, or generic term. A high forward similarity can therefore coexist with a poor return path. The published document-level alignment work already indicates that document structure changes word-alignment behavior; B4 replayed only its released anomaly vectors, which do not retain counterpart indices ([B4 research note](https://github.com/blackmath88/apertushackathon-uzh/blob/blackmath88/b4-alignment-first-sdm/track_2a/docs/B4_ALIGNMENT_FIRST_SDM.md), [2026 alignment implementation](https://github.com/ZurichNLP/document-level-word-alignment)).

### What changes

A correspondence is no longer accepted because it has a large cosine value. It becomes a provisional edge that must survive a return journey.

Explicit sentence alignment is not necessarily required. A sparse cross-document token graph is sufficient.

### Technical hypothesis

**Hypothesis R1:** Gold-positive tokens that receive deceptively high maximum similarity will nevertheless have greater cross-lingual cycle defect than gold-zero tokens with legitimate correspondences.

Given top-\(k\) similarities, form directional distributions:

\[
P_{XY}(j\mid i)
=
\operatorname{softmax}_{j}
\left(S_{ij}/\tau\right)
\]

\[
P_{YX}(i\mid j)
=
\operatorname{softmax}_{i}
\left(S_{ij}/\tau\right)
\]

Define return probability and cycle defect:

\[
q_i=\sum_j P_{XY}(j\mid i)P_{YX}(i\mid j)
\]

\[
c_i=1-q_i
\]

A NULL node absorbs tokens for which no satisfactory explanation exists. The final deterministic score is initially just \(c_i\), not a trained combination.

**Input**

```json
{
  "source_tokens": ["..."],
  "target_tokens": ["..."],
  "top_k_similarity_edges": [
    {"source": 12, "target": 19, "similarity": 0.84}
  ]
}
```

**Output**

```json
{
  "token_scores": [0.03, 0.71],
  "return_probabilities": [0.97, 0.29],
  "null_mass": [0.01, 0.48]
}
```

**Components**

- Contextual multilingual token embeddings.
- Sparse matrix operations.
- Optional partial transport or NULL-node normalization.
- Existing official-token aggregation.

**Apertus role**

Only high-defect cases are routed. Apertus chooses between:

- Current counterpart.
- Best alternative.
- No materially equivalent counterpart.

It does not generate offsets or explanations.

**Cost**

- Deterministic stage: approximately \(O((n+m)k)\) after embeddings.
- Apertus stage: two order-controlled one-token calls per routed edge.
- The cached B4 anomaly vectors are insufficient because they omit counterpart indices; embeddings or upstream links must be regenerated.

### Summoned cost

Legitimate translations are not one-to-one. Articles can disappear, compounds can split, and a phrase can correspond to several words. A strict return-cycle requirement may classify valid many-to-one translation as defective.

Re-entry also moves the problem upward: the return map requires its own normalization, NULL policy, and aggregation.

### Falsification

Reject R1 if, using one frozen embedding matrix:

- Cycle defect fails to improve macro Spearman by at least 0.01 over independent maximum similarity.
- It does not improve at least two language pairs.
- Repeated-name and repeated-date cases are not enriched among high-cycle-defect tokens.
- Its within-document positive-versus-zero token AUROC does not beat raw DiffAlign.

This comparison must regenerate the same embeddings once and change only the matching rule.

***

## Constellate

### The move

- **ID:** `constellate`
- **Operational form:** “Stop deducing. Place the concepts side by side and let the configuration carry what no single one states.”
- **Repository lineage:** Benjamin, Adorno, and Warburg; unverified.
- **Summons:** Suggestiveness without content—a constellation can become impossible to refute.

### Apply it

Place three independently generated observations beside each token:

1. **Conservation bit:** Does global matching leave unexplained mass?
2. **Cycle bit:** Does its correspondence fail to return?
3. **Counterfactual bit:** Does Apertus prefer a controlled alternative over the original?

Do not immediately feed them into a learned fusion model. Treat their configuration as a finite **error syndrome**.

### What changes

The system stops asking which detector is authoritative. It asks whether specific disagreements among detectors diagnose particular failure modes.

This borrows the operational mechanism of error-correcting-code syndrome decoding: redundant checks do not reconstruct the original message independently, but their pattern localizes a failure.

### Technical hypothesis

**Hypothesis R2:** A predefined three-bit syndrome orders tokens more reliably than any constituent score because genuine semantic differences violate several independent conservation checks, while harmless paraphrases usually violate only lexical alignment.

| Syndrome | Interpretation | Initial score band |
|---|---|---:|
| `000` | Explained and stable | 0 |
| `001` | Apertus-only anomaly; suspected model noise | 1 |
| `010` | Cycle ambiguity or repeated occurrence | 2 |
| `100` | Global residual without semantic confirmation | 3 |
| `011` | Semantically suspicious ambiguous match | 4 |
| `101` | Residual plus counterfactual evidence | 5 |
| `110` | Structurally unexplained and cycle-inconsistent | 6 |
| `111` | All checks disagree with equivalence | 7 |

Within each band, deterministic residual mass breaks ties. The ordering is frozen before the full run.

**Input**

```json
{
  "token": "must",
  "conservation_residual": 0.73,
  "cycle_defect": 0.64,
  "counterfactual_preference": 0.81
}
```

**Output**

```json
{
  "syndrome": "111",
  "score_band": 7,
  "within_band_score": 0.73
}
```

**Apertus role**

Apertus supplies exactly one syndrome bit: whether an original or minimally altered local statement is better supported by the other-language evidence.

**Cost**

- No model call for the first two bits.
- One or two one-token calls for routed tokens.
- No learned ranker.

### Summoned cost

The syndrome table may merely aestheticize disagreement. A hand-authored ordering can hide arbitrary preferences behind an error-correction metaphor.

The signals are also not truly independent: they may all inherit the same embedding failure.

### Falsification

Reject R2 if:

- Gold-positive prevalence is not approximately monotonic across syndrome bands.
- The band ordering changes materially under passage-order or label-mapping controls.
- The syndrome score fails to beat its strongest single constituent.
- Shuffling the Apertus bit within language and deterministic-score decile performs equally well.

***

## Historicize

### The move

- **ID:** `historicize`
- **Operational form:** “Treat the current configuration as a dated artifact rather than a state of the art. Ask what it is the determinate negation of.”
- **Repository lineage:** Hegelian determinate negation; unverified.
- **Summons:** A retrospective sequence can falsely appear to have been progressing toward its latest form.

### Apply it

B0 through B5 share a premise despite architectural change:

> The system must positively identify semantic differences.

- B0 predicts differing tokens.
- B2 generates difference spans.
- B3 classifies semantic tasks.
- B4 predicts anomaly.
- B5 would verify suspicious differences.

Historicizing the sequence reveals that decomposition changed repeatedly while **positive difference recognition remained the protected core**.

Cancel that premise. Predict only **certificates of equivalence**, then rank the unexplained remainder.

### What changes

Difference is no longer a recognized object. It is what remains after high-precision explanations are deducted.

This is stronger than simply inverting a score because each deduction must carry a certificate.

### Technical hypothesis

**Hypothesis R3:** A conservative equivalence sieve can safely remove most gold-zero tokens, creating a smaller residual population in which simple anomaly ranking outperforms full-document DiffAlign.

Candidate certificates:

1. Reciprocal high-margin cross-lingual match.
2. Match stable under two context windows.
3. Normalized number, date, URL, or identifier in an equivalent local role.
4. Named-entity alias supported by surrounding predicate context.
5. Stable cycle closure.
6. Apertus mutual-entailment certificate for a bounded phrase.

Certificates are applied sequentially. The first implementation discounts rather than deletes tokens:

\[
s_i^{(t+1)}
=
s_i^{(t)}
\left(1-\alpha_t C_t(i)\right)
\]

where \(C_t(i)\) is certificate confidence.

**Input**

```json
{
  "source_token": {"index": 14, "text": "31.12.2026"},
  "target_candidates": ["31 décembre 2026"],
  "certificate_tests": ["normalized-date", "reciprocal-link", "context-stability"]
}
```

**Output**

```json
{
  "equivalence_certified": true,
  "certificate_types": ["normalized-date", "reciprocal-link"],
  "remaining_anomaly": 0.02
}
```

**Apertus role**

Apertus may only grant a bounded semantic equivalence certificate. It cannot raise a token’s anomaly score. This asymmetry prevents model enthusiasm from manufacturing differences.

**Cost**

- Cheap certificates are deterministic.
- Apertus calls only occur after deterministic tests disagree.
- Complete fallback is the residual deterministic score.

### Summoned cost

A false equivalence certificate is more dangerous than a false anomaly: it suppresses a real difference and can prevent every later stage from recovering it.

The architecture may also become a long chain of special cases—precisely the degeneration Historicize was intended to expose.

### Falsification

Reject any certificate family if:

- Fewer than 99% of certified development tokens have gold value zero.
- Applying the certificate lowers macro Spearman.
- Its apparent precision disappears on leave-one-document-out evaluation.
- A deterministic counterfactual—such as replacing a date with another date—still passes the certificate.

Reject the entire sieve if no certificate removes a meaningful number of tokens at the frozen precision requirement.

***

## Refuse the metaphor

### The move

- **ID:** `refuse-the-metaphor`
- **Operational form:** “Identify the metaphor that made the field thinkable and treat it as the obstacle it has become.”
- **Repository lineage:** Bachelard’s epistemological obstacle; unverified.
- **Summons:** Dropping a productive metaphor may remove the tractability it supplied.

### Apply it

The hidden metaphor is that the two documents must be **aligned**, as though one were a distorted spatial image of the other.

Replace correspondence with intervention:

> If this source token or fact were removed or altered, would the source become more or less equivalent to the other-language document?

A token is scored by the effect of a controlled edit, not by a counterpart.

### What changes

No target token needs to be identified. The method asks whether the other document supports the retention of a particular source fact.

This is an alignment-free form of semantic localization.

### Technical hypothesis

**Hypothesis R4:** For semantically changed numbers, entities, modal operators, negation, and quantifiers, Apertus will prefer a neutralized or alternative source statement more often than it does for gold-zero controls.

For candidate span \(i\), construct:

- \(X\): original source passage.
- \(X^{-i}\): passage with the marked information removed.
- \(X^{i\rightarrow v}\): passage with one typed alternative.

Ask:

```text
Which English version is better supported by the German document?

0 = original
1 = edited
2 = indistinguishable or insufficient evidence
```

Define intervention evidence:

\[
a_i=
\log p(\text{edited}\mid Y)
-
\log p(\text{original}\mid Y)
\]

Positive \(a_i\) suggests that the original content is poorly supported by \(Y\).

**Input**

```json
{
  "target_document": "...",
  "original": "Applications may be submitted until 30 June.",
  "edited": "Applications must be submitted until 30 June.",
  "edit_type": "modality"
}
```

**Output**

```json
{
  "p_original": 0.19,
  "p_edited": 0.68,
  "p_uncertain": 0.13,
  "intervention_evidence": 1.275
}
```

**Components**

- Typed mutation operators.
- Grammar and fluency validation.
- One-token Apertus endpoint.
- Passage-order and label-permutation controls.
- Original-token provenance for each mutation.

**Apertus role**

Apertus discriminates between two supplied worlds. It neither discovers the edit nor generates a difference.

**Cost**

A pilot with five edit types, four examples per language and both control orders requires about 120–240 one-token calls.

### Summoned cost

Deleting or changing a token can produce ungrammatical text. Apertus may prefer the more fluent candidate rather than the semantically correct one.

The refusal of alignment also loses target evidence localization. Long target documents may exceed useful attention, while retrieval quietly reintroduces alignment under another name.

### Falsification

Reject R4 if:

- Order-averaged controlled accuracy is at most 55%.
- Label permutation changes the decision in more than 10% of cases.
- Synthetic semantic mutations are not distinguished from punctuation or fluency controls.
- Real gold-positive and gold-zero candidates cannot be separated better than token rarity or DiffAlign score.
- Edited fluency predicts the model decision better than semantic edit type.

***

## Demote

### The move

- **ID:** `demote`
- **Operational form:** “Take the thing that was the source of truth and make it a rendering of something deeper.”
- **Repository lineage:** Virtual memory and Delta-style projections; unverified.
- **Summons:** The failure moves beneath the demoted representation to the layer producing it.

### Apply it

Demote absolute token scores. Spearman evaluates ranks, yet B0–B5 ask the model for absolute classes, probabilities, severities, or anomaly scores.

Ask Apertus the narrower question the metric actually needs:

> Which of two marked token hypotheses is less supported by the other-language document?

### What changes

Apertus need not calibrate `DIFFERENT`, `EQUIVALENT`, or severity probabilities across documents or languages. It only needs to provide a local ordering.

This creates a **semantic tournament**.

### Technical hypothesis

**Hypothesis R5:** Apertus’s pairwise ordering of two anomaly candidates is more stable under label permutation and passage order than its absolute same/different classification.

**Contract**

```text
The target-language evidence is supplied below.

Candidate A concerns the marked source expression: [A].
Candidate B concerns the marked source expression: [B].

Which candidate has weaker semantic support from the target document?

0 = A
1 = B
2 = tied or insufficient evidence
Answer with one token.
```

Run the swapped candidate order and average the two distributions.

For the top four deterministic candidates in each document, a sorting network or round-robin tournament produces pairwise outcomes. A Bradley–Terry model or Copeland score converts them into a rank:

\[
P(i\succ j)
=
\frac{\exp(\theta_i)}
{\exp(\theta_i)+\exp(\theta_j)}
\]

Outside the routed set, preserve the deterministic ranking.

**Input**

```json
{
  "document_id": "de_004",
  "candidate_a": {"token_indices": [41], "context": "..."},
  "candidate_b": {"token_indices": [119], "context": "..."},
  "target_evidence": "..."
}
```

**Output**

```json
{
  "p_a_weaker": 0.67,
  "p_b_weaker": 0.21,
  "p_tie": 0.12
}
```

**Components**

- Frozen gold-blind candidate selector.
- One-token Apertus calls.
- Pairwise tournament scheduler.
- Bradley–Terry or deterministic Copeland ranking.
- Existing evaluator.

**Cost**

Four candidates need six unordered comparisons. With two order controls:

\[
30 \times 6 \times 2 = 360
\]

one-token calls.

At the observed median latency this is operationally manageable, though prompt-prefill cost must be measured separately.

### Summoned cost

The source of truth moves beneath the model into the candidate selector. If a gold-positive token never enters the tournament, perfect pairwise reasoning cannot recover it.

Pairwise preferences may also be intransitive:

\[
A\succ B,\quad B\succ C,\quad C\succ A
\]

Such cycles would expose unstable semantic comparison rather than usable ranking information.

### Falsification

Reject R5 if:

- Pairwise accuracy does not beat DiffAlign’s existing order by at least two percentage points on a preregistered diagnostic set.
- More than 10% of three-candidate subsets form strong preference cycles.
- Order-averaged output still changes materially under label permutation.
- Adding the tournament fails to improve complete-sample Spearman over the identical candidate selector and deterministic correction.
- Shuffled Apertus pairwise probabilities perform equally well.

***

## Interpose

### The move

- **ID:** `interpose`
- **Operational form:** “Insert a mediator every request must traverse. Make traversal structural, not policy-mandated.”
- **Repository lineage:** Anderson’s 1972 reference-monitor framing; unverified.
- **Summons:** Bypass and confused-deputy failure—the mediator can be persuaded to misuse its own authority.

### Apply it

No source token may declare itself “explained” merely because it finds a similar target token. Every claimed correspondence must traverse a **semantic conservation matcher**.

The matcher has three structural rules:

1. Target evidence has bounded capacity.
2. Tokens may align to explicit NULL.
3. Local matches must participate in a globally consistent explanation.

### What changes

Difference becomes **unexplained semantic mass**, not low maximum similarity.

This directly targets B4’s repeated names, dates, and generic vocabulary: one convenient target occurrence cannot freely explain many unrelated source occurrences.

### Technical hypothesis

**Hypothesis R6:** With an identical embedding matrix, partial matching with bounded capacity and NULL mass will improve token ranks over independent maximum similarity.

A minimal transport formulation is:

\[
\min_{T\ge 0}
\sum_{i,j}T_{ij}C_{ij}
+
\lambda_x\sum_i u_i
+
\lambda_y\sum_j v_j
\]

subject to:

\[
\sum_jT_{ij}+u_i=a_i
\]

\[
\sum_iT_{ij}+v_j=b_j
\]

where:

- \(C_{ij}\) is semantic and positional cost.
- \(u_i\) is unexplained source mass.
- \(v_j\) is unexplained target mass.
- \(a_i,b_j\) are token capacities.

The initial token score is \(u_i\), optionally combined with transport entropy.

**Components**

- Contextual embedding matrix.
- Sparse candidate edges.
- SciPy assignment for a hard control.
- Partial or unbalanced optimal transport for soft matching.
- Optional affine-gap dynamic programming.
- The [Python Optimal Transport](https://github.com/PythonOT/POT) project is an implementation lead, but its exact revision and licence should be pinned before integration.
- Biological sequence alignment supplies the transferable mechanisms of monotone matching, insertion/deletion states, and affine gap costs; it does not establish that documents are biological sequences.

**Apertus role**

Apertus supplies an edge cost only where deterministic costs leave two near-equal explanations:

```text
0 = candidate edge A is more semantically adequate
1 = candidate edge B is more semantically adequate
2 = neither; use NULL
```

The optimizer, not Apertus, decides the global assignment.

### Summoned cost

The mediator becomes a confused deputy. A positional prior can reject a legitimate reordered passage; a capacity rule can reject valid repeated mentions; a NULL penalty can be tuned to manufacture the desired anomaly density.

It may improve benchmark rank by encoding document order while harming genuinely reordered multilingual pages.

### Falsification

Using one frozen embedding matrix, reject R6 if:

- Hard assignment, affine-gap alignment, and partial transport all fail to improve over independent maximum similarity.
- Any apparent gain disappears when positional cost is removed.
- Gains depend on language-specific tuning that cannot survive document-level cross-validation.
- The new method fixes repeated-name cases but loses more on one-to-many translations.
- Full embedding-generation and matching costs are disproportionate to the gain.

# II. Constellation

## Three incompatible moves

The strongest tension appears among:

- **Refuse the metaphor:** Do not treat alignment as the primary object.
- **Interpose:** Require every correspondence to pass through a global alignment mediator.
- **Demote:** Absolute anomaly scores are not the truth; relative ordering is.

These cannot be resolved by saying “combine alignment, counterfactuals, and an LLM.” Each makes a different claim about what the problem *is*.

| Move | Apparent demand |
|---|---|
| Refuse the metaphor | A token can be tested without identifying its counterpart |
| Interpose | Unexplained mass exists only relative to a globally constrained correspondence system |
| Demote | The final primitive should be pairwise ordering, not calibrated difference probability |

## Unresolved tension

If alignment is only a retrieval convenience, global matching may be unnecessary. If unexplained mass is meaningful only after conservation, alignment is fundamental. If only rank matters, neither position needs to yield an absolute semantic score.

The new scientific question is:

> Is Apertus better at ordering two globally generated residual hypotheses than at deciding whether either hypothesis is absolutely different?

That prediction did not exist in B0–B5.

## Emerging algorithm

### Counterfactual Residual Tournament

This is not a weighted signal fusion model.

1. **Interpose:** Construct a NULL-aware global matcher and identify four token groups per document with the largest unexplained mass.
2. **Refuse:** For each group, construct an explicit counterfactual that neutralizes only the suspected information—delete a condition, replace a date, swap a modal, or substitute the proposed counterpart.
3. **Demote:** Do not ask Apertus whether each group is different. Compare two groups and ask which counterfactual produces the larger improvement in cross-lingual equivalence.
4. Use a fixed six-duel round robin over four groups.
5. Average order-swapped probabilities.
6. Rank the four groups by Copeland score or Bradley–Terry strength.
7. Preserve deterministic global-matcher ranks outside those groups.
8. Project each group score only onto the original mutated tokens.

### Exact duel

```text
Target-language passage:
{target}

Case A:
Original: {a_original}
Counterfactual: {a_counterfactual}

Case B:
Original: {b_original}
Counterfactual: {b_counterfactual}

For which case does the counterfactual repair a larger material
difference with the target passage?

0 = Case A
1 = Case B
2 = neither or indistinguishable
```

### Why it is scientifically distinct

- B2 asks Apertus to invent differences.
- B3 asks Apertus to classify isolated semantic tasks.
- B5 asks Apertus to verify a suspicious correspondence.
- The tournament asks Apertus to make a **relative causal judgment between two supplied repairs**.

It predicts that absolute probability instability can coexist with useful pairwise ordering—an empirically falsifiable claim.

# III. Adversarial verdict

## Programme assessment

B0–B5 is neither wholly progressive nor wholly degenerating. It contains a degenerating phase followed by a genuine core change at B4.

| Stage | New prediction | Observed result | Verdict |
|---|---|---|---|
| B0 | An 8B model can directly serialize document-wide token scores | Truncation, malformed output, weak correlation | Initial conjecture falsified |
| B2 | Generating sparse spans will improve reliability and reduce completion cost | Better pilot parseability and fewer tokens; no demonstrated semantic gain | Operational progress, semantic accommodation |
| B3 | Bounded decisions will deliver reliable complete semantic coverage | Only 42/219 accepted; no complete document; alignment errors | Contract and decomposition falsified in implemented form |
| B4 oracle | Localization granularity strongly limits achievable Spearman | Exact locations near 1; sentence and passage broadcasts much lower | Successful new prediction |
| B4 alignment | A complete continuous non-generative baseline will beat B2 | 0.187117 versus 0.129306 on the same 30 documents | Successful new prediction |
| B4 probe | One-token Apertus scoring is operational but may be unstable | 16/16 valid; order and label sensitivity | Successful capability diagnosis |
| B5 | Apertus probabilities contain incremental information for selected residuals | Not tested | Progressive only if matched against deterministic and shuffled controls |

The B4 experiments were preregistered around explicit gates, refused test data in code, used the immutable 30-document manifest, and separated the 16-call capability probe from benchmark claims ([PR 17](https://github.com/blackmath88/apertushackathon-uzh/pull/17), [B4 research note](https://github.com/blackmath88/apertushackathon-uzh/blob/blackmath88/b4-alignment-first-sdm/track_2a/docs/B4_ALIGNMENT_FIRST_SDM.md)). That is stronger evidence of a progressive change than merely adding middleware after B3.

## Mandatory degeneration test

The actual Denkraum move asks whether recent modifications predicted anything new or only accommodated prior failure; its lineage is marked unverified, and its summons warns against premature abandonment ([`moves.js`](https://github.com/blackmath88/denkraum/blob/main/denkraum/data/moves.js)).

### B0 to B2

B2 predicted shorter and more parseable outputs. That prediction succeeded operationally. It did not predict or deliver a robust semantic improvement.

**Assessment:** Partly progressive engineering, degenerating scientific core.

### B2 to B3

B3 changed granularity but preserved the belief that Apertus should positively classify semantic differences. Its principal failure—overlong rationales—was partly self-inflicted by the output contract. Nevertheless, zero complete documents and serious proportional-alignment errors were new, informative failures.

**Assessment:** Failed experiment, not scientifically empty; however, it protected the positive-recognition core.

### B3 to B4

B4 made several risky predictions before observing results:

- Binary exact localization would nearly preserve perfect ranking.
- Sentence and passage broadcasts would lose substantial correlation.
- Continuous DiffAlign would outperform full-sample B2.
- One-token Apertus outputs would be technically reliable but not necessarily semantically stable.

Those predictions produced discriminating outcomes.

**Assessment:** Progressive core change from model-first generation to representation and metric diagnosis.

### B4 to B5

B5 becomes degenerating if it is justified only as:

> DiffAlign has errors, so add Apertus to correct them.

It becomes progressive only if it predicts something unavailable from B4:

> On a frozen candidate set, Apertus probabilities improve token ordering over the same deterministic features and over shuffled Apertus probabilities.

That result must be falsifiable before implementation.

## Adversarial objections

### Does the oracle prove localization dominates?

Not by itself. It proves that exact localization has an exceptionally high ceiling and that coarse broadcast sacrifices ranking. It does not show that realistic systems can identify exact locations, nor whether practical failure arises from semantic judgment, correspondence, or routing.

A sentence oracle of 0.534 also means coarse semantic units retain substantial theoretical headroom over current systems. Therefore, “localization is the dominant practical bottleneck” remains a hypothesis.

### Is DiffAlign a strong foundation?

It is a strong task-native baseline, but its current B4 instantiation is one published embedding and extraction configuration. Independent maximum similarity permits unlimited target reuse and has no NULL, capacity, or structural consistency. The [original 2023 DiffAlign work](https://aclanthology.org/2023.emnlp-main.835/) establishes alignability as a useful unsupervised signal; it does not establish that maximum similarity is the optimal matching rule.

### Are Apertus probabilities semantic?

Not yet. B4 established one-token output reliability and probability access, while order and label sensitivity showed nuisance dependence. Semantic value requires matched deterministic, shuffled, label-permuted, and order-reversed controls.

### Are shorter inputs better?

They reduce serialization and attention burden but can remove headings, definitions, antecedents, list scope, and document-level exceptions. Context length must be treated as an ablation variable, not a monotonic virtue.

### Will a continuous ranker generalize?

Only if document-level held-out predictions improve. Thousands of correlated tokens do not create thousands of independent training examples. A ranker can memorize language, document position, and annotation density while appearing data-rich.

### Does Spearman equal useful detection?

No. Spearman rewards global token ordering. The Zürich observatory needs event recall, alert precision, severity, human-verifiable evidence, and review-budget utility. A method that makes small rank improvements by demoting punctuation-adjacent tokens may add no civic value.

## Surviving predictions

| Hypothesis | Prediction not made by B0–B5 |
|---|---|
| Cycle defect | Repeated-name/date false matches have high round-trip inconsistency despite high cosine |
| Conservation matching | Changing only the matching rule improves ranks with the same embeddings |
| Equivalence sieve | A large token subset can be certified gold-zero at at least 99% precision |
| Support intervention | Controlled semantic edits shift Apertus preference specifically at differing tokens |
| Pairwise tournament | Relative anomaly ordering is more stable than absolute labels |
| Syndrome decoding | Specific disagreement patterns outperform arbitrary continuous fusion |

# Prior-art mechanisms

## Multilingual alignment

- **DiffAlign, 2023:** Scores a token by its best cross-document embedding alignment; this is the direct foundation of B4 ([paper](https://aclanthology.org/2023.emnlp-main.835/)).
- **SimAlign, 2020:** Extracts word alignments from multilingual contextual embeddings, including mutual-nearest-neighbor and iterative matching variants ([paper](https://aclanthology.org/2020.findings-emnlp.147/), [implementation](https://github.com/cisnlp/simalign)).
- **Vecalign, 2019:** Uses multilingual sentence embeddings and dynamic programming, including one-to-many sentence relationships; its implementation is Apache-2.0 ([paper](https://aclanthology.org/D19-1136/), [repository](https://github.com/thompsonb/vecalign)).
- **Document-level structural alignment, 2026:** Introduces document constraints and publishes SwissGov-RSD vectors; the pinned implementation used by B4 is MIT-licensed according to the project’s research note ([paper](https://arxiv.org/abs/2608.21023), [repository](https://github.com/ZurichNLP/document-level-word-alignment)).

The proposed transfer is not “use another aligner.” It is to compare independent maxima against cycle consistency, bounded capacity, NULL mass, and affine gaps while holding embeddings fixed.

## Biological alignment

Needleman–Wunsch, Smith–Waterman, pair-HMMs, and affine-gap alignment contribute three mechanisms:

- Matches compete inside a global path.
- Insertions and deletions are explicit states.
- A contiguous omitted block is not charged as many unrelated mismatches.

The analogy fails where document sections reorder freely or repeated statements legitimately occur. Therefore, sequence constraints must be an ablation, not an unquestioned prior.

## Differential testing

Compiler differential testing executes equivalent or generated programs under multiple compilers and treats disagreement as evidence of a defect. Csmith is a prominent implementation lineage ([repository](https://github.com/csmith-project/csmith)).

The transferable mechanism is **metamorphic invariance**, not program generation:

- Swapping language order should not reverse symmetric equivalence.
- Renaming labels should not change semantic probabilities.
- Duplicating a distant name should not change the original occurrence’s meaning.
- A format-preserving date rewrite should not create a discrepancy.
- Adding relevant context may resolve uncertainty; adding irrelevant context should not reverse a confident decision.

## Error-correcting codes

The transferable mechanism is syndrome decoding:

- Several partially redundant checks encode expected consistency.
- A failure pattern can localize an error even when no check is authoritative.
- The syndrome table must predict observable error classes or it is merely decorative.

No novelty is claimed for syndrome decoding itself; the proposed application is to multilingual semantic evidence.

## Causal intervention

Deletion, substitution, and counterfactual explanation methods probe whether changing one input component alters an outcome. Here the outcome is not a classifier label but cross-lingual support.

The critical control is fluency: every semantic mutation needs a same-fluency, meaning-preserving control so model preference cannot be attributed merely to grammar.

# IV. Candidate experiments

## Scientific comparison

| Rank | Hypothesis | What is different? | Falsifying result | Apertus contribution |
|---:|---|---|---|---|
| 1 | Rank-error tomography | Materializes where Spearman is being lost before choosing an architecture | Frozen B5 router has negligible oracle repair reach | None; decision experiment |
| 2 | Capacity/cycle matcher | Changes matching law while holding embeddings fixed | No improvement over max similarity | Optional edge adjudication |
| 3 | Pairwise semantic tournament | Apertus orders two anomaly hypotheses instead of classifying one | No gain over deterministic ordering; unstable cycles | Direct pairwise ranking information |
| 4 | B5 verifier control | Tests current proposal with matched controls | Same performance as deterministic or shuffled arm | One-token correspondence probability |
| 5 | Support intervention | Scores effects of controlled source edits without target-token alignment | At most 55% controlled accuracy or fluency confound | Counterfactual choice |

## Practical comparison

| Experiment | Localization | Benchmark path | Generalization | Compute | Engineering | Main risk |
|---|---|---|---|---|---|---|
| Rank-error tomography | Identifies rank-error locations diagnostically | Determines whether routing can move Spearman | High as an experimental tool | CPU, no inference | 1–3 h | Oracle analysis mistaken for production evidence |
| Capacity/cycle matcher | Unexplained or cycle-defective tokens | Direct continuous scores | Strong if same rules work across languages | New embeddings or links | 6–12 h | One-to-many and reorder errors |
| Pairwise tournament | Candidate-token groups only | Reorders selected token scores | Moderate; relative judgments may transfer | About 360 calls | 4–8 h | Candidate selector dominates |
| B5 control | Suspicious correspondence windows | Local score correction | Moderate | About 180 calls | 3–6 h | Binary verifier says “different” for misalignment |
| Support intervention | Exact mutated token | Direct token-level evidence | Potentially high for typed changes | 120–240 calls | 6–12 h | Ungrammatical counterfactuals |

## Information per hour

1. **Router-conditioned rank-error tomography.**
2. **Matching-rule replacement with one regenerated similarity matrix.**
3. **Pairwise Apertus tournament pilot.**
4. **Matched B5 verifier test.**
5. **Typed support-intervention pilot.**

The first experiment can reject an entire intervention strategy. The fifth may reveal a better long-term model role but is less likely to produce submission-ready scores immediately.

# V. Immediate implementation

## Rank-error tomography

### Exact hypothesis

> The current B5 routing concept selects token windows containing enough correctable rank error that an ideal local score-adjustment policy could improve macro Spearman by at least 0.02 at a budget of three windows per document.

This does **not** hypothesize that Apertus can realize the correction. It asks whether the proposed place of intervention has sufficient reach.

### Why this comes first

Apertus can only improve tokens that B5 routes. If an oracle operating inside the intended local-adjustment family cannot move the metric, model calls are irrelevant.

It also addresses a hidden possibility:

> Most Spearman loss may come from gold-positive tokens that DiffAlign considers confidently equivalent—not from conspicuous high-anomaly or ambiguous tokens.

If true, B5’s suspicious-correspondence premise is backward.

### Input schema

```json
{
  "manifest": {
    "sample": "frozen-b2-b3-30",
    "split": "dev",
    "language_counts": {
      "de": 10,
      "fr": 10,
      "it": 10
    }
  },
  "documents": [
    {
      "document_id": "...",
      "language": "de",
      "tokens": ["..."],
      "eligible_mask": [true, false],
      "gold_scores": [0, -1],
      "diffalign_scores": [0.12, 0.00]
    }
  ]
}
```

Gold data enters only the diagnostic evaluator and oracle intervention. It must not be exposed to the router.

### Output schema

```json
{
  "experiment": "router-conditioned-rank-tomography-v1",
  "baseline": {
    "macro_spearman": 0.187117
  },
  "routers": [
    {
      "name": "local-anomaly-peaks",
      "budget_per_document": 3,
      "selected_windows": [],
      "gold_positive_recall": 0.0,
      "rank_error_mass_covered": 0.0,
      "oracle_adjusted_macro": 0.0,
      "random_percentile": 0.0
    }
  ],
  "decision": "reject|continue|inconclusive"
}
```

### Frozen routers

Evaluate these without gold:

1. **Top anomaly:** Highest DiffAlign scores.
2. **Local peaks:** Highest score relative to neighboring tokens.
3. **High gradient:** Largest local score discontinuities.
4. **Repeated structured value:** Dates, numbers, URLs, or capitalized expressions repeated elsewhere.
5. **Low-context support:** High anomaly unsupported by adjacent token scores.
6. **Uniform random:** Seeded control.

Use budgets of 1, 3, 5, and 10 non-overlapping windows per document. Fix each window to three official tokens unless the selected token is at a boundary.

Because B4 vectors omit counterpart links, do not call these “alignment ambiguities.” They are score-derived routers.

### Rank tomography

For each language:

1. Concatenate eligible predictions exactly as the official evaluator does.
2. Compute average predicted and gold ranks.
3. For each token, record signed rank residual:

\[
e_i=R_{\mathrm{pred},i}-R_{\mathrm{gold},i}
\]

4. Record squared rank error:

\[
q_i=e_i^2
\]

5. Separate:
   - Under-ranked gold-positive tokens.
   - Over-ranked gold-zero tokens.
   - Correctly ordered tokens.
6. Aggregate rank-error mass by:
   - Router membership.
   - Gold severity.
   - Number/date/entity-like token.
   - Repetition count.
   - Document and language.
   - DiffAlign score decile.

Squared rank residual is diagnostic; official Spearman remains the primary evaluation.

### Oracle intervention

The oracle must operate only on routed windows and inside an attainable B5-like correction family.

For each routed window, allow a uniform score offset selected from:

\[
\{-1,-0.5,-0.25,0,0.25,0.5,1\}\sigma_l
\]

where \(\sigma_l\) is the standard deviation of DiffAlign scores for that language.

Use gold labels to select the best offset per window through deterministic coordinate search. Run a fixed maximum of three passes and report:

- Original official Spearman.
- Best attained official Spearman.
- Number and magnitude of adjustments.
- Result from the same procedure on seeded random windows.

This is an optimistic diagnostic, not a production result and not a mathematically exact global upper bound.

### Baselines

- Unmodified DiffAlign.
- Existing B2 P1 full-sample zero-default result.
- Random windows over 1,000 frozen seeds.
- Top raw anomaly tokens.
- An oracle allowed to adjust all tokens, as a sanity ceiling.
- Gold-positive locations, explicitly labeled as the existing non-deployable oracle.

### Evaluation

Primary:

- Official macro Spearman.
- Per-language Spearman.
- Oracle-adjusted macro gain.

Diagnostic:

- Fraction of total squared rank error inside routed windows.
- Gold-positive token recall.
- Recall of under-ranked gold-positive tokens.
- Recall of over-ranked gold-zero tokens.
- Random-router percentile.
- Gain by intervention budget.
- Document concentration: fraction of gain attributable to the single most influential document.

### Decision rules

**Reject B5’s current router if:**

- Three windows per document yield oracle gain below 0.01; or
- The router does not beat the 95th percentile of random routing; or
- Improvement is confined to one language; or
- More than half of the gain comes from one document.

**Continue to an Apertus test if:**

- Oracle gain is at least 0.02.
- The router beats random in at least two languages.
- Selected windows capture both under-ranked positives and over-ranked zeros.
- Gain is not dominated by one document.

**Inconclusive:**

- Gain lies between 0.01 and 0.02.
- Router performance is language-specific.
- Different reasonable score-offset grids reverse the conclusion.

Thresholds must be committed before executing the experiment.

### Dataset protocol

- Use the exact immutable 30-document development manifest from B2–B4.
- Ten documents per language.
- Do not inspect, enumerate, load, or construct paths for the test split.
- Refuse any non-`dev` split before file I/O.
- Do not change routers after viewing their oracle results.
- Do not use oracle-adjusted scores in a submission or downstream feature.
- Keep BF16/HF, Q8 B2, B3, and B4 results in separate configuration records.

### Budget

- Model calls: 0.
- New model downloads: 0.
- CPU runtime: likely minutes.
- Implementation: approximately 1–3 hours using the existing evaluator and frozen B4 artifacts.
- Statistical analysis: approximately one additional hour.

### Evidence artifacts

```text
runs/b5-router-tomography/
  manifest.json
  environment.json
  source-hashes.json
  router-config.json
  selected-windows.jsonl
  token-rank-residuals.csv
  oracle-interventions.jsonl
  metrics.json
  random-controls.json
  report.md
```

Tests should verify:

- Exact manifest identity.
- Refusal of test split.
- Gold data is inaccessible from router functions.
- Deterministic seeds.
- Official evaluator parity.
- Reproduction from stored artifacts without inference.

# VI. Denkraum return package

The actual schema requires `schema`, `move`, `problem`, and `deposits`; each deposit requires `kind`, `label`, and `detail`. The schema explicitly states that structural validity is not acceptance ([contribution schema](https://github.com/blackmath88/denkraum/blob/main/denkraum/schemas/contribution-package.schema.json)).

The package below uses the existing canonical problem `falsification-without-stakes` because the SwissGov-RSD problem is not yet a canonical Denkraum node. One proposed deposit introduces that problem. Every deposit remains `verified: false`, consistent with the MCP concept’s rule that an external caller cannot certify its own attribution ([MCP concept](https://github.com/blackmath88/denkraum/blob/main/denkraum-mcp-concept.json)).

```json
{
  "schema": "ai.bridgework.denkraum.contributionPackage/v0.1",
  "move": "demote",
  "problem": "falsification-without-stakes",
  "preparedBy": "AI prepared research traverse; not human verified",
  "deposits": [
    {
      "kind": "problem",
      "label": "SwissGov-RSD intervention reachability",
      "detail": "Before asking whether Apertus can correct suspicious multilingual correspondences, determine whether a frozen gold-blind router reaches enough rank error to alter the official metric. The proposed test uses the immutable 30-document development manifest, the stored DiffAlign vectors and gold-aware local score interventions only as a non-production oracle. Sources: https://aclanthology.org/2026.acl-long.1437/ and https://github.com/blackmath88/apertushackathon-uzh/pull/17",
      "summons": "Oracle reachability can become a substitute for building a real predictor. A high ceiling says only that correction is possible at those locations, not that Apertus can perform it.",
      "attribution": "SwissGov-RSD benchmark and B4 experimental record",
      "verified": false,
      "remainder": "The oracle adjustment family is only an approximation of what a future B5 implementation could do."
    },
    {
      "kind": "concept",
      "label": "Rank-error tomography",
      "detail": "Demote the aggregate Spearman value from source of truth to a rendering of token-level rank residuals. Materialize where gold-positive tokens are under-ranked, where gold-zero tokens are over-ranked, and which frozen candidate routers can reach those errors. The diagnostic does not become a production feature.",
      "summons": "The error map exposes development gold so vividly that architectural decisions may overfit thirty documents.",
      "attribution": "Denkraum move demote; lineage attribution in the repository remains unverified",
      "verified": false,
      "remainder": "Per-token rank residuals are explanatory diagnostics, not independent observations or causal error contributions."
    },
    {
      "kind": "tension",
      "label": "Alignment as witness versus alignment as authority",
      "detail": "DiffAlign treats maximum cross-document similarity as evidence that a token is explained. A capacity-constrained matcher would instead require correspondences to compete and permit NULL. The unresolved question is whether alignment should determine semantic explanation or merely nominate hypotheses for counterfactual testing. Relevant prior work: https://aclanthology.org/2023.emnlp-main.835/ and https://github.com/ZurichNLP/document-level-word-alignment",
      "summons": "The global matcher becomes a confused deputy: positional and capacity priors can reject valid translation variation while appearing structurally principled.",
      "attribution": "DiffAlign and document-level word-alignment work",
      "verified": false,
      "remainder": "Neither maximum similarity nor constrained matching establishes pragmatic or deontic equivalence."
    },
    {
      "kind": "graft",
      "label": "Pairwise semantic tournament",
      "detail": "Borrow pairwise ranking from preference models and apply it to token anomalies. Rather than asking Apertus for an absolute difference label, present two candidate token discrepancies and ask which is less supported by the opposite-language evidence. A fixed tournament converts order-controlled one-token probabilities into local ranks, matching the benchmark's ranking objective more directly.",
      "summons": "The candidate generator becomes the hidden source of truth, and pairwise preferences may be cyclic or dominated by prompt order.",
      "attribution": "Pairwise ranking graft; no novelty claim for the underlying ranking method",
      "verified": false,
      "remainder": "A local tournament cannot recover a differing token that the deterministic router never selected."
    },
    {
      "kind": "problem",
      "label": "Does Apertus add conditional ranking information?",
      "detail": "A meaningful Apertus contribution requires improvement over an identical deterministic candidate set, projection and fusion rule, as well as over label-permuted and probability-shuffled controls. Valid one-token output is operational reliability, not evidence of semantic competence.",
      "summons": "Strict ablation may reject a weak but practically useful model contribution on a small sample; relaxing it would make the contribution unidentifiable.",
      "attribution": "B4 one-token capability probe",
      "verified": false,
      "remainder": "Thirty development documents may be insufficient to distinguish small true gains from document composition effects."
    }
  ]
}
```

This package is only a proposed return. Generating or validating it does not place any deposit in `constellation.js`, mark an attribution verified, or promote it into canonical Denkraum state.

# VII. Final recommendation

## What to test next

Run **router-conditioned rank-error tomography** before making another Apertus call.

The experiment may overturn the assumption that:

> The right use of Apertus is to verify conspicuous, suspicious DiffAlign correspondences.

It may show instead that most recoverable Spearman loss comes from **apparently well-aligned gold-positive tokens**—changed dates, names, modality, or omitted facts whose generic or repeated counterparts suppress their anomaly. In that case, B5’s router is aimed at visible uncertainty while the important errors are false confidence.

## If the router passes

Do not begin with binary B5 verification. Run the smallest pairwise semantic-tournament test:

- Four routed groups per document.
- Six comparisons per document.
- Candidate-order reversal.
- Fixed candidate selector.
- Deterministic, shuffled, and no-Apertus controls.
- Complete fallback.
- No learned fusion.

This tests a genuinely new claim: Apertus may be better at **relative semantic ordering** than at absolute semantic classification.

## If the router fails

Abandon B5 in its current form. Regenerate explicit alignment evidence and test:

1. Independent maximum similarity.
2. Reciprocal-cycle defect.
3. Hard assignment with NULL.
4. Affine-gap alignment.
5. Partial transport.

Hold embeddings fixed. If a constrained matcher improves token ranks, Apertus can later adjudicate its high-entropy edges. If it does not, the alignment-first programme itself needs reconsideration.

## Benchmark versus Zürich

For the UZH benchmark, optimize complete token ranking with strict Apertus ablation.

For the Zürich observatory, the more consequential direction is administrative counterfactual testing:

- Does one page permit an action that another forbids?
- Is a duty, deadline, eligibility condition, fee, or exception different?
- Can the difference be shown with original-source evidence?

A pairwise tournament may help the benchmark while being unsuitable for human alerts. Conversely, deontic countermodels may be operationally valuable while scoring poorly under token-level Spearman. Those outcomes should remain separate.

The smallest decision-changing experiment is therefore not a new middleware layer. It is a measurement of whether the proposed intervention site contains enough rank error to justify one.