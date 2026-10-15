The strongest direction is to replace “How similar are these passages?” with “Which claims are preserved, weakened, strengthened, contradicted, added or omitted?” Embeddings remain useful for locating comparable material, but they should not define semantic correctness.

The closest reusable systems are COMET/XCOMET, MetricX, ACES/Span-ACES, multilingual NLI cross-encoders, Vecalign, and Prism. They address different parts of your problem: quality estimation, error localization, contrastive evaluation, directional inference, structural correspondence, and probabilistic scoring. None is a demonstrated turnkey solution for symmetric, multilingual document-difference detection. [github](https://github.com/Unbabel/COMET)

My recommendation is a shift toward **contrastive** testing: evaluate preservation of specific semantic commitments against plausible alternatives, rather than treating low similarity or missing word alignment as evidence of error. Importantly, test this change without first building a larger pipeline.

Your final sentence is truncated after “Find a fundamentally”; the report below addresses the complete research requirements preceding it.

## 1. What the evidence says—and what it does not

Three findings most directly challenge your current assumptions.

1. Better word alignment does not establish better semantic-error detection. Awesome-align demonstrates substantial improvements in alignment error rate, but that measures correspondence, not whether a correspondence preserves meaning. “Must” and “may,” or “approved” and “not approved,” can be correctly aligned while expressing different commitments. The first part is published evidence; the second is the task distinction your evaluation must capture. [github](https://github.com/neulab/awesome-align)

2. Strong aggregate translation-quality metrics can still miss consequential differences. ACES evaluates 68 error phenomena across 146 language pairs. Its analysis of 50 metrics finds source neglect, surface-overlap preferences, phenomenon-specific weaknesses, and unreliable performance from the LLM-based methods tested. Span-based metrics also need substantial improvement. [arxiv](https://arxiv.org/abs/2401.16313)

3. Small specialist models are serious competitors, not merely routers for an LLM. The 2024 xCOMET-lite paper reports a 278M-parameter metric retaining 92.1% of the authors’ measured xCOMET-XXL quality. MetricX-24’s documented WMT24 average correlations are 0.705 for Hybrid-Large and 0.716 for Hybrid-XXL. These results support testing compact learned evaluators before assuming an 8B generator is the best semantic judge. They do not establish equivalent performance on your document-difference task. [github](https://github.com/google-research/metricx)

### Evidence boundaries

Throughout this report:

- “Published result” means a finding reported by the original paper or implementation.
- “Transfer hypothesis” means a proposed adaptation to your task, not a demonstrated improvement.
- Engineering effort and computational budgets are planning estimates, not measured benchmarks.
- Code licences, checkpoint licences, and dataset licences are separate. A permissive repository licence does not automatically cover its weights or training data.
- I inspected public repositories and model documentation. Where a last-commit date was not exposed, I do not infer active maintenance from stars, downloads, or repository availability.

## 2. Prior-art landscape: 23 relevant resources

“Unverified” below means the retrieved documentation did not establish a usable licence for the particular artifact—not that the artifact necessarily lacks one.

### A. Closest evaluation systems and error corpora

| # | Resource and direct link | Actual findings or capabilities | Licence and reuse caveat |
|---|---|---|---|
| 1 | [COMET / XCOMET](https://github.com/Unbabel/COMET) | Scores translations; XCOMET additionally returns error spans, severity and confidence. Available XCOMET encoders include 3.5B XL and 10.7B XXL. Closest implementation for localized translation-error detection.  [github](https://github.com/Unbabel/COMET) | Code: Apache-2.0. Model licences vary; some require Hugging Face acknowledgement. |
| 2 | [xCOMET-lite, EMNLP 2024](https://github.com/NL2G/xCOMET-lite), [paper](https://arxiv.org/abs/2406.14553), [checkpoint](https://huggingface.co/myyycroft/XCOMET-lite) | Reports 278M parameters, 92.1% retained quality relative to XXL, and up to threefold compression through quantization without quality degradation in its experiments. The reported 6.4% improvement over small comparison metrics is specific to the paper’s evaluation, not a general accuracy gain.  [arxiv](https://arxiv.org/abs/2406.14553) | Licence unverified. Research implementation with pinned, older dependencies and no published releases on the inspected page. |
| 3 | [MetricX-24](https://github.com/google-research/metricx), [paper](https://arxiv.org/html/2410.03983v1) | Hybrid reference-based/reference-free regression. Ablations report improvements over MetricX-23 using WMT23 MQM and synthetic challenge data. Public WMT24 evaluation script reports average correlation 0.705 for Large versus 0.716 for XXL.  [arxiv](https://arxiv.org/html/2410.03983v1) | Code: Apache-2.0. Repository explicitly says it is not an officially supported Google product; check checkpoint terms separately. |
| 4 | [GEMBA / GEMBA-MQM](https://github.com/MicrosoftTranslator/GEMBA), [paper](https://arxiv.org/abs/2310.13988) | GPT-4-based, three-shot MQM error-span annotation without a human reference. Original authors report strong system-ranking performance but explicitly caution about proprietary-model dependence.  [arxiv](https://arxiv.org/abs/2310.13988) | Licence unverified here. Original inference depends on proprietary GPT models. |
| 5 | [GEMBA V2, WMT 2025](https://www2.statmt.org/wmt25/pdf/2025.wmt-1.67.pdf) | Aggregates ten judgments from GPT-4.1-mini. Reference-free RRWA variant reports first place by average correlation, 0.728, on the WMT24 MQM evaluation used in the paper. Evidence for repeated judgment aggregation—not evidence that ten 8B judgments will reproduce it.  [www2.statmt](https://www2.statmt.org/wmt25/pdf/2025.wmt-1.67.pdf) | Paper available; verified open-weight equivalent not established. |
| 6 | [ACES / Span-ACES](https://github.com/EdinburghNLP/ACES), [Hugging Face dataset](https://huggingface.co/datasets/nikitam/ACES), [2024 analysis](https://arxiv.org/abs/2401.16313) | Contrastive good/bad translations covering 68 phenomena and 146 language pairs; span annotations and evaluation scripts. Finds that metric families fail differently and that high-quality aggregate evaluation does not imply reliable error sensitivity.  [github](https://github.com/EdinburghNLP/ACES) | Code/data licences unverified in retrieved README. Best immediate diagnostic benchmark. |
| 7 | [WMT MQM human evaluation](https://github.com/google/wmt-mqm-human-evaluation) | Expert annotations for WMT submissions from 2020–2023. Useful for natural, rather than solely synthetic, error distributions and severity labels.  [github](https://github.com/google/wmt-mqm-human-evaluation) | Verify dataset terms and source-text rights before redistribution. |
| 8 | [OpenKiwi](https://github.com/unbabel/openkiwi) | Word-level and sentence-level quality estimation framework. Its original work reports state-of-the-art word-level QE on WMT18 English–German using stacked systems.  [github](https://github.com/unbabel/openkiwi) | Licence/current compatibility unverified. More useful as a reference architecture than an assumed drop-in modern dependency. |
| 9 | [SEScore / SEScore2](https://github.com/xu1998hz/SEScore2), [original implementation](https://github.com/xu1998hz/SEScore) | Learns evaluation from synthesized errors. Reports an average Kendall improvement of 0.158 over prior unsupervised metrics across four evaluation benchmarks. Reference-based; the multilingual fine-tuned version differs from the five-language synthetic-only version.  [github](https://github.com/xu1998hz/SEScore2) | Licence unverified. Do not interpret the README’s rescaled scores as calibrated error counts without validation. |
| 10 | [BLASER 2.0 / SONAR](https://github.com/facebookresearch/sonar), [2025 publication](https://ai.meta.com/research/publications/blaser-2-0-a-metric-for-evaluation-and-quality-estimation-of-massively-multilingual-speech-and-text-translation/) | Reference-based and QE models over SONAR representations; covers 202 text languages and 57 speech languages. Authors demonstrate applications to hallucination detection and dataset filtering. Still representation-based, but learned evaluation rather than raw cosine alone.  [ai.meta](https://ai.meta.com/research/publications/blaser-2-0-a-metric-for-evaluation-and-quality-estimation-of-massively-multilingual-speech-and-text-translation/) | Check SONAR code and each checkpoint’s terms separately; licence not verified here. |

### B. Entailment, alignment and likelihood scoring

| # | Resource and direct link | Actual findings or capabilities | Licence and reuse caveat |
|---|---|---|---|
| 11 | [mDeBERTa multilingual NLI](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) | Approximately 0.3B parameters; trained with multilingual and some mixed-language premise/hypothesis pairs. Model card reports XNLI accuracy 82.4% German and 82.3% French, but only 53.7% on English ANLI overall. This large benchmark gap is a useful warning about hard inference.  [huggingface](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7) | Confirm exact revision’s licence metadata. Validate non-English↔non-English pairs separately from English-linked pairs. |
| 12 | [XNLI](https://github.com/facebookresearch/XNLI) | Foundational 15-language NLI corpus: 5,000 test and 2,500 development pairs. Useful for transfer evaluation, not a document-difference or token-error corpus. Repository was archived on October 31, 2023.  [github](https://github.com/facebookresearch/XNLI) | Dataset-specific licence file; archived repository. |
| 13 | [Vecalign](https://github.com/thompsonb/vecalign) | Approximate dynamic programming, linear in sentence count; supports consecutive many-to-many correspondence and insertions/deletions. README reproduction reports strict F1 0.902 and lax F1 0.986 on its Bleualign test setup.  [github](https://github.com/thompsonb/vecalign) | Code: Apache-2.0. Bundled Bleualign data: GPLv2. Needs Cython/C compiler and overlapping-span embeddings. |
| 14 | [SimAlign](https://github.com/cisnlp/simalign), [paper](https://aclanthology.org/2020.findings-emnlp.147/) | Extracts word alignments from multilingual contextual embeddings without parallel training. Useful as an alignment baseline and for comparing extraction strategies—not a semantic contradiction detector.  [aclanthology](https://aclanthology.org/2020.findings-emnlp.147/) | MIT code; underlying model terms separate.  [github](https://github.com/cisnlp/simalign/blob/master/LICENSE) |
| 15 | [Awesome-align](https://github.com/neulab/awesome-align) | Fine-tuned contextual word alignment. README reports German–English AER 15.2 versus fast_align 27.0, and Chinese–English 13.4 versus 38.1 for the shown configuration. It also documents a recall/precision trade-off when enabling coverage training.  [github](https://github.com/neulab/awesome-align) | BSD-3-Clause. Tokenized input and word/subword-offset handling required. |
| 16 | [SuperPAL](https://github.com/oriern/SuperPAL), [paper](https://aclanthology.org/2021.conll-1.25/) | Aligns proposition spans rather than whole sentences. Supervised NLI-initialized model improves alignment quality over unsupervised comparison. Transferable unit-of-comparison idea, but original task is English summarization.  [arxiv](https://arxiv.org/html/2009.00590v2) | Licence unverified. Legacy Transformers 2.5.1 and AllenNLP 0.9 components; some DUC-derived text requires LDC access.  [github](https://github.com/oriern/SuperPAL) |
| 17 | [Prism](https://github.com/thompsonb/prism), [paper](https://evalnlg-workshop.github.io/papers/EvalNLGEval_2020_paper_4.pdf) | Teacher-forced multilingual conditional likelihood using a 39-language translation/paraphrase model. Reports outperforming or statistically tying prior metrics across language pairs in WMT19 segment-level evaluation. Can condition on source for QE.  [github](https://github.com/thompsonb/prism) | Licence unverified. Older toolkit; supports German, French and Italian among its 39 languages. |
| 18 | [BARTScore](https://github.com/neulab/BARTScore), [paper](https://arxiv.org/abs/2106.11520) | Treats evaluation as conditional generation likelihood; reports outperforming comparison metrics in 16 of 22 settings. Scoring direction changes the information being assessed. Original BART is not a multilingual drop-in solution.  [arxiv](https://arxiv.org/abs/2106.11520) | Licence unverified. Reuse scoring formulation; verify multilingual replacement independently. |
| 19 | [ContrastScore, 2025](https://aclanthology.org/2025.ijcnlp-long.163.pdf) | Contrasts token probabilities from stronger and weaker models rather than relying on one model’s likelihood alone. Relevant to removing generic fluency effects. Retrieved evidence establishes the formulation, not a verified gain on cross-lingual difference detection.  [aclanthology](https://aclanthology.org/2025.ijcnlp-long.163.pdf) | Implementation/licence not verified; conceptual candidate rather than immediate integration choice. |
| 20 | [Unsupervised QE, Fomicheva et al., 2020](https://aclanthology.org/2020.tacl-1.35/) | Uses uncertainty information from the translation system; reports correlations rivaling supervised QE without training a separate annotated-data predictor. Crucial limitation: access to the producing MT model is assumed.  [aclanthology](https://aclanthology.org/2020.tacl-1.35/) | Paper-level resource; reproduction code exists in fairseq examples. Third-party document versions may not expose the required glass-box information. |

### C. Linguistic analysis, testing and transferable tooling

| # | Resource and direct link | Actual findings or capabilities | Licence and reuse caveat |
|---|---|---|---|
| 21 | [Negation-MT corpus/code](https://github.com/mosharafhossain/negation-mt), [paper](https://par.nsf.gov/servlets/purl/10396754) | Finds substantially poorer translation quality for negation-containing sentences in several tested language pairs; some reported quality reductions exceed 60%. This concerns the paper’s quality measures, not a universal mistranslation probability.  [par.nsf](https://par.nsf.gov/servlets/purl/10396754) | Licence unverified. Valuable source of risk categories and targeted evaluation cases. |
| 22 | [Stanza](https://github.com/stanfordnlp/stanza), [Universal Dependencies](https://universaldependencies.org/), [interlingual WordNet interface](https://github.com/goodmami/wn) | Stanza provides lemmas, morphology, dependencies and entities. UD supplies cross-language grammatical conventions; `wn` accesses multilingual lexicons. These are feature sources, not evidence that symbolic checking solves semantic equivalence.  [github](https://github.com/stanfordnlp/stanza) | Stanza code: Apache-2.0. Treebank and lexicon licences vary; inspect each selected resource. |
| 23 | [CheckList](https://github.com/marcotcr/checklist) and [POT](https://github.com/PythonOT/POT) | CheckList operationalizes behavioral testing, including negation perturbations. POT implements balanced, partial and unbalanced optimal transport. Neither demonstrates your intended multilingual detector, but both substantially reduce implementation work for falsifiable alternatives.  [ijcai](https://www.ijcai.org/proceedings/2021/0659.pdf) | POT: MIT. CheckList licence unverified here. |

### Recent work worth distinguishing from established solutions

A 2026 audit of 51 multilingual benchmarks covering 242 datasets and 219 languages finds that 56% of dataset–language instances were translated, with uneven task coverage and contamination risks. This matters because success on translated multilingual benchmarks can overstate generalization to independently authored multilingual documents. It is evaluation evidence, not a new semantic-difference algorithm. [microsoft](https://www.microsoft.com/en-us/research/publication/the-state-and-fate-of-multilingual-contextual-evaluation-in-the-nlp-world/)

I found clearer directly reusable evidence in 2024–2025 evaluation research than a verified 2026 open-source breakthrough for your exact task. I would not fill that gap with adjacent papers presented as solved prior art.

## 3. Five promising techniques

### Technique 1: Bidirectional entailment with claim-level coverage

#### How it works

For comparable passages \(A\) and \(B\), estimate separately:

\[
P(A \Rightarrow B), \qquad P(B \Rightarrow A), \qquad P(\text{contradiction})
\]

Interpret the directions rather than reducing them immediately to one number:

- Both entail: candidate equivalence.
- Only one entails: possible addition, omission, narrowing or strengthening.
- Contradiction: incompatible commitments.
- Neither entails: unrelated material, unresolved ambiguity, or insufficient context.

For passages containing several claims, score claim coverage rather than assuming the whole paragraph is one proposition.

The mDeBERTa model offers a cheap implementation of multilingual NLI, while SuperPAL provides evidence that proposition-level units can improve correspondence in its summarization setting. Neither establishes multilingual claim extraction and comparison as solved. [huggingface](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7)

#### Why it could beat embedding similarity

Similarity is largely symmetric; information preservation is directional. A detailed passage can entail a shorter version without the shorter version preserving everything.

#### Important limitation

Neutral is not synonymous with “meaningful difference.” Missing context, anaphora and underspecified claims also produce non-entailment. Furthermore, mixed-language NLI capability must be tested on your actual language pairs; the model’s published XNLI results are not that test. [huggingface](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7)

#### Local 8B compatibility

Excellent: use the small NLI encoder as the complete baseline, then test whether an 8B verifier adds information on difficult cases. Do not assume the LLM is necessary.

***

### Technique 2: Specialized quality estimation and error localization

#### How it works

Run a source-conditioned evaluator on paired passages:

- COMETKiwi or MetricX for reference-free quality estimation.
- XCOMET for error spans and severity.
- xCOMET-lite as a compact candidate, after confirming the desired inference mode and output support.

For symmetric document comparison, evaluate both orientations. Treat the resulting signals as directional warnings—not as calibrated probabilities that one language version is wrong.

COMET explicitly supports reference-free scoring; XCOMET exposes error-span metadata. MetricX supports hybrid inputs with or without references. [github](https://github.com/Unbabel/COMET)

#### Why it could beat embedding similarity

These models learn relationships between source-conditioned content and human quality judgments rather than only learning that two texts discuss similar topics.

#### Important limitation

Translation evaluation assumes a source and a translation. Your documents may instead be independently revised co-authoritative versions. A quality metric can conflate intended adaptation, fluency, and semantic loss.

Also, an omission has no target-text span to highlight. Preserve source-side evidence and unmatched claims rather than relying solely on target-side span detection.

#### Local 8B compatibility

The strongest evidence-backed low-compute alternative. Test whether a compact evaluator already solves much of the problem before paying for 8B inference. xCOMET-lite’s published compression results justify this comparison, not an assumption of task equivalence. [arxiv](https://arxiv.org/abs/2406.14553)

***

### Technique 3: Many-to-many correspondence with explicit unmatched mass

#### How it works

Separate correspondence from error judgment:

1. Generate paragraph and sentence-group candidates.
2. Permit one-to-many and many-to-many matches.
3. Permit deletion/addition states.
4. Retain competing candidates when the correspondence is uncertain.
5. Only then assess semantic preservation.

Vecalign already implements consecutive many-to-many matching and empty-side alignments. For reordered content, test partial or unbalanced optimal transport using POT. [github](https://github.com/thompsonb/vecalign)

A possible transfer formulation is:

\[
\min_{T \ge 0}
\langle T,C\rangle
+\varepsilon R(T)
+\lambda D(T\mathbf 1,a)
+\lambda D(T^\top\mathbf 1,b)
\]

Here \(C\) is a matching cost, \(T\) is soft correspondence, and marginal penalties allow imperfect coverage instead of forcing all content to match.

#### Why it could beat conventional similarity

It can expose content that has no adequate counterpart and avoid repeatedly “explaining” several source units with the same generic target unit.

#### Important limitation

This is not an argument for strict token transport. Balanced mass conservation can invent correspondence; unbalanced transport can discard the very content you need to flag. The unmatched-mass penalty must be evaluated explicitly.

The established evidence is Vecalign’s alignment performance and POT’s supported optimization methods. Improvement in semantic-error detection is a hypothesis. [github](https://github.com/thompsonb/vecalign)

#### Local 8B compatibility

Excellent: reuse cached embeddings and CPU optimization. The LLM can be absent or restricted to unresolved competing correspondences.

***

### Technique 4: Contrastive teacher-forced scoring

#### How it works

Score a candidate explanation or interpretation without generating a long answer.

One option is a likelihood ratio:

\[
S(A,B)=
\frac{1}{|B|}
\left[
\log P(B\mid A,\text{task})
-\log P(B\mid \text{task})
\right]
\]

The subtraction is intended to reduce the contribution of generic target fluency. This exact adaptation is a hypothesis; Prism and BARTScore establish conditional-likelihood evaluation, and ContrastScore explores model-probability contrasts. [evalnlg-workshop.github](https://evalnlg-workshop.github.io/papers/EvalNLGEval_2020_paper_4.pdf)

A more targeted version compares fixed alternatives:

- preserved obligation / weakened obligation;
- same deadline / changed deadline;
- retained exception / omitted exception.

Use the same evidence passage and identical answer structure. Score the alternatives with teacher forcing or next-token label probabilities.

#### Why it could beat embedding similarity

It asks whether the source supports a particular semantic interpretation, not whether the two passages share a topic.

#### Important limitation

Likelihood rewards familiar wording and can favor fluent incorrect text. Candidate construction can reveal the answer. A label-probability interface does not create semantic competence.

Essential controls are source removal, source shuffling, label-order reversal and equivalent label paraphrases.

#### Local 8B compatibility

Good if the deployment exposes logits or prompt-token log probabilities. Short fixed-label scoring avoids long generation, although prompt processing still costs compute. Full candidate scoring may need multiple forward passes.

There is evidence for likelihood-based evaluation; there is not yet evidence here that your particular 8B model will outperform its own direct judgments.

***

### Technique 5: Risk localization before LLM inference

#### How it works

Use low-cost signals to predict where comparison is worth spending compute:

- negation and polarity markers;
- modal verbs and obligation/permission expressions;
- quantifiers and exception constructions;
- numbers, units, dates and interval endpoints;
- entity and semantic-role changes;
- unmatched propositions;
- disagreement between NLI, QE and alignment signals.

Stanza and UD provide practical morphology and dependency features. Negation-MT supplies evidence that at least one such linguistic category is associated with substantial translation-quality problems in tested settings. [par.nsf](https://par.nsf.gov/servlets/purl/10396754)

#### Why it could beat embedding similarity

A single low-salience operator can change a passage’s consequences while leaving its topical representation almost unchanged.

#### Important limitation

Risk is not an error label. Negation can be expressed lexically, morphologically or through constructions; modalities are not equivalent word-for-word. False friends and polysemy require context, so lexicon membership should trigger scrutiny rather than determine correctness.

WordNet can supply lexical relations and candidate ambiguity features, but it is not a comprehensive cross-language false-friend or modality database. [github](https://github.com/goodmami/wn)

#### Local 8B compatibility

Excellent. Evaluate the router’s critical-error recall at a fixed inference budget before testing the downstream judge.

## 4. Unexpected connections from neighboring fields

### A. Compiler differential testing → semantic metamorphic testing

Compiler testing can compare implementations under transformations whose expected behavior is known. CheckList brings the same behavioral-testing philosophy to NLP. [ijcai](https://www.ijcai.org/proceedings/2021/0659.pdf)

Transfer hypothesis:

- Meaning-preserving transformations should not change the detector’s verdict.
- Meaning-changing mutations should change it.
- Compare implementations under exactly the same paired transformations.

Examples:

| Transformation | Expected detector behavior |
|---|---|
| Active/passive paraphrase | Stable |
| Harmless sentence split | Stable |
| “Must” → “may” | Change |
| “Before” → “after” | Change |
| Remove a restrictive exception | Change |
| Reorder independent clauses | Usually stable |

This tests whether your detector responds to semantic commitments rather than edit magnitude. It is also a practical way to generate difficult negative controls, not just obvious errors.

### B. Information theory → source-conditioned information gain

Prism and BARTScore use conditional generation likelihood. That suggests comparing what the source adds to the probability of the target, rather than evaluating target probability alone. [evalnlg-workshop.github](https://evalnlg-workshop.github.io/papers/EvalNLGEval_2020_paper_4.pdf)

Transfer hypothesis:

- A generic fluent sentence may have high unconditional probability.
- A faithful specific statement should receive additional support from the correct source.
- A shuffled source should remove that support.

The source-shuffle control is decisive. If the score barely changes, the supposed semantic evaluator is functioning mainly as a fluency or familiarity detector.

### C. Error-correcting codes → multilingual consistency syndromes

When three or more language versions exist, construct a graph of pairwise semantic-consistency judgments.

Transfer hypothesis:

- One anomalous version may disagree with several others.
- An inconsistent triangle can identify a review target.
- Directional coverage patterns may reveal which version lacks a claim.

This is an analogy, not a demonstrated multilingual error-correcting theorem. Versions are not independent sensors: they may share a translation source or copy the same mistake. Majority agreement cannot establish truth.

### D. Active learning and anomaly detection → disagreement-budgeted review

Use disagreement between genuinely different signals to select annotations or expensive verification: NLI versus QE, structural coverage versus lexical checks, or source-conditioned versus source-ablated scores.

Transfer hypothesis:

- Cases with model disagreement may yield more informative annotations than cases selected only by low cosine similarity.
- A small labeled set may be better spent identifying failure mechanisms than training a universal scalar scorer.

However, uncertain cases are not necessarily consequential cases. Report critical-error recall as well as uncertainty.

## 5. Practical reuse: what to integrate first

The estimates below assume one engineer, an existing document loader, and reproducible access to a GPU. They include a basic adapter and smoke tests, not production hardening.

| Component | Dependencies and interface work | Estimated effort | Recommendation |
|---|---|---:|---|
| ACES / Span-ACES | Dataset loader; score adapters; character-span normalization | 0.5–1.5 days | First: establish phenomenon-level diagnostics. |
| Multilingual mDeBERTa NLI | PyTorch, Transformers, tokenizer; two-direction batching | 0.5–1 day | First: strongest simple non-generative semantic baseline. |
| COMETKiwi / MetricX | PyTorch and model framework; checkpoint downloads; score orientation and thresholds | 0.5–2 days | First: compare against cosine without rebuilding a metric. |
| XCOMET | `unbabel-comet`; GPU memory; span-offset adapter; licence acknowledgement where applicable | 1–2 days | Useful localization baseline; do not equate all spans with semantic errors. |
| xCOMET-lite | Repository wrapper; version isolation; compatible COMET dependencies | 1–3 days | Promising compact comparator, but test clean installation and outputs first. |
| Vecalign | Cython/C compiler; sentence-group embeddings; insertion/deletion handling | 1–2 days | Prefer over strict token alignment for split/merge-heavy documents. |
| Stanza risk features | PyTorch; per-language models; parsing and operator rules | 1–3 days | Useful for inexpensive routing and error strata. |
| POT partial/unbalanced transport | NumPy/SciPy; cached costs; penalty tuning | 1–2 days for prototype | Experimental replacement for forced correspondence. |
| Prism | Older translation toolkit and checkpoint environment | 1–3 days | Reproduction comparator; not my first production dependency. |
| SuperPAL | Legacy AllenNLP/Transformers; English proposition extractor | Several days or more | Borrow the proposition-level design, not necessarily the full stack. |

The documented installation and compatibility details supporting these estimates are in the COMET, xCOMET-lite, Vecalign, NLI and SuperPAL repositories. [github](https://github.com/Unbabel/COMET)

### Reproducibility warnings

- Pin COMET versions and checkpoint revisions. A public issue reports inconsistent XCOMET scores between versions 2.2.4 and 2.2.5; it is a reason to run score-regression tests, not proof that all current versions are affected. [github](https://github.com/Unbabel/COMET/issues/244)
- xCOMET-lite’s README includes older CUDA, PyTorch, quantization and protobuf requirements. Do not install that complete environment into your main application without isolation. [github](https://github.com/NL2G/xCOMET-lite)
- Vecalign’s empty-side alignment cost is reported as zero in its output. Treat insertion/deletion status explicitly; do not rank it using that cost as though it were an ordinary matched pair. [github](https://github.com/thompsonb/vecalign)
- SuperPAL’s dependencies and some underlying dataset restrictions materially raise reuse effort. [github](https://github.com/oriern/SuperPAL)
- XNLI is archived, but remains usable as a dataset. Archival and scientific utility are different questions. [github](https://github.com/facebookresearch/XNLI)

### What I would not integrate yet

I would not begin with a semantic ontology, a multilingual semantic-frame parser, a document agent, or 8B fine-tuning.

First determine whether NLI, specialized QE, or explicit unmatched coverage gives an independent improvement. Otherwise, architectural complexity risks hiding a failure to measure the right semantic relation.

## 6. Three small, falsifiable experiments

All three should use the same frozen development/test split and preserve document families across splits. Bootstrap by original document or source item—not individual mutated sentences—because derived cases are correlated.

Use three separate outcomes:

1. Contrastive ranking accuracy.
2. Critical-error recall at a fixed false-alert rate or review budget.
3. Localization quality, including source-side omission detection.

Keep your existing benchmark metric too, but do not assume it measures all three.

### Experiment 1: Can a small verifier beat cosine without an LLM?

#### Hypothesis

Directional NLI or source-conditioned QE distinguishes small consequential edits from benign paraphrases better than embedding similarity.

#### Dataset

Approximately 400 paired tests:

- 200 human-checked meaning-changing cases: negation, modality, quantity, dates, roles and omissions.
- 200 meaning-preserving controls: paraphrase, sentence splitting, grammatical alternation and harmless reordering.

Combine relevant ACES cases with native document samples. ACES supplies contrastive phenomena; native samples reduce dependence on translated benchmark artifacts. [github](https://github.com/EdinburghNLP/ACES)

#### Systems

- Existing embedding baseline.
- Bidirectional multilingual NLI.
- Reference-free MetricX or COMETKiwi.
- A simple combination fitted only on development data.

#### Controls

- Correct source versus shuffled source.
- Original versus swapped comparison direction.
- Same-language versus mixed-language pairs.
- Comparable edit size for benign and consequential changes.
- Source-document family held out.

#### Preregistered falsification criterion

Require, for example, at least a five-percentage-point test improvement in contrastive accuracy without a material increase in false alerts on benign controls. Set the threshold before examining results.

If source shuffling preserves performance, reject the interpretation that the improvement reflects source-sensitive verification.

#### Expected failures

Neutral NLI outputs mistaken for omissions; QE penalties for style; poor non-English↔non-English transfer; quantities hidden in complex constructions.

#### Approximate cost

Roughly a few thousand encoder scoring instances, including controls. Budget under a few GPU-hours for a small pilot, with wall time measured on your hardware. No 8B inference is required.

***

### Experiment 2: Is correspondence actually the bottleneck?

#### Hypothesis

Many-to-many matching and explicit unmatched states improve omission/addition detection more than stricter token alignment.

#### Dataset

About 50 document pairs with manually marked correspondence and:

- sentence splits/merges;
- reordered paragraphs;
- omitted claims;
- duplicated boilerplate;
- scope-sensitive edits.

#### Systems

Hold the semantic scorer fixed and vary only correspondence:

1. Current matching.
2. Current strict word-alignment variant.
3. Vecalign-style many-to-many matching.
4. Partial/unbalanced transport.
5. Human correspondence as an oracle control.

Vecalign provides a working many-to-many comparator; POT supplies the alternative transport solvers. [github](https://github.com/thompsonb/vecalign)

#### Measurements

- Gold correspondence coverage.
- Omission/addition recall.
- Downstream semantic detection.
- False matches to boilerplate.
- Oracle improvement ceiling.

#### Preregistered falsification criterion

If human correspondence barely improves semantic detection, alignment is not the main bottleneck. Stop investing in more elaborate alignment.

If soft methods improve correspondence but worsen semantic detection, reject alignment quality as a sufficient proxy for your objective.

#### Expected failures

Vecalign’s order assumption breaks on reordered content; transport hides unmatched material by spreading mass; group concatenation dilutes a small error; penalties overflag legitimate language-specific restructuring.

#### Approximate cost

Reuse cached embeddings. CPU matching should be inexpensive at this pilot scale; embedding generation is likely the main compute expense. Budget a few GPU-hours at most for ordinary-sized documents, and record costs against actual sentence/group counts.

***

### Experiment 3: Does the local 8B add value as a scorer rather than a generator?

#### Hypothesis

Fixed-alternative probability scoring is more reliable or cheaper than generating difference labels with the same model.

#### Dataset

Approximately 300 adjudicated cases, including:

- difficult errors missed by the embedding baseline;
- benign controls;
- disagreement cases from Experiment 1;
- a random sample to avoid evaluating only routed hard cases.

#### Same-model comparison

1. Short direct label generation.
2. Fixed-label next-token scoring.
3. Pairwise judgment of matched alternatives.
4. Teacher-forced candidate scoring with a source-ablation contrast.

Keep evidence windows, model revision, precision and task definition fixed. Count all prompt-processing work.

#### Controls

- Reverse candidate order.
- Permute label tokens.
- Remove or shuffle the source.
- Replace labels with equivalent paraphrases.
- Compare full-precision and deployed quantized scores on a subset.
- Include small NLI/QE and no-LLM baselines.

#### Preregistered falsification criterion

A scoring mode must improve semantic detection or calibration at equal compute, not merely improve JSON validity.

Separately, test the router at a 25% inference budget. Require a predetermined critical-error retention target—for example 95%. If it cannot meet that target, reject the routing policy even if downstream accuracy appears good.

#### Expected failures

Token-label bias; position bias; confidently wrong judgments; fluency dominating likelihood; correlated errors across repeated judgments; scope evidence missing from the window.

#### Approximate cost

With 300 cases, four modes, two orderings and roughly 500–1,000 input tokens per evaluation, expect on the order of 1–3 million input-token evaluations before additional ablations. Plan for several local GPU-hours, then measure rather than assume throughput. Short labels reduce decoding cost, not prompt cost.

Prism/BARTScore motivate likelihood evaluation, and GEMBA V2 motivates testing judgment aggregation. Neither establishes that these modes will beat generation on your 8B model. [www2.statmt](https://www2.statmt.org/wmt25/pdf/2025.wmt-1.67.pdf)

## 7. Critical assessment

### What has failed or proved unreliable

#### Aggregate correlation as a proxy for critical-error sensitivity

ACES shows that metrics with strong general standing still have substantial phenomenon-specific weaknesses. Evaluate negation, source-dependent ambiguity, quantities, omissions and discourse separately. [arxiv](https://arxiv.org/abs/2401.16313)

#### Assuming an LLM judge necessarily improves semantic evaluation

GEMBA reports strong system-level evaluation, while ACES finds unreliable behavior from tested LLM metrics on targeted error phenomena. These findings are compatible: system ranking and detecting a subtle error in one passage are different tasks. [arxiv](https://arxiv.org/abs/2401.16313)

#### Treating alignment improvements as semantic improvements

Awesome-align’s AER gains are real, but do not demonstrate downstream error-detection gains. Its documented recall/precision trade-off also shows that “more aligned tokens” is not unconditionally better. [github](https://github.com/neulab/awesome-align)

#### Trusting spans as complete explanations

Span-ACES finds substantial room for improvement in error localization. A predicted target span also cannot by itself represent a completely omitted source claim. [arxiv](https://arxiv.org/abs/2401.16313)

### Where the evidence remains inconclusive

- Whether bidirectional multilingual NLI reliably separates equivalent wording from altered legal, medical or technical commitments.
- Whether an 8B multilingual LLM’s token probabilities outperform its direct judgments.
- Whether unbalanced transport improves semantic detection rather than merely alignment.
- Whether small perturbation corpora generalize to naturally occurring editorial divergence.
- Whether repeated judgments improve an open-weight model enough to justify their cost.
- Whether risk routers retain rare, severe errors rather than preferentially finding easy operator changes.

These are proposed experiments, not established conclusions.

### Linguistic knowledge helps—but does not close the problem

Negation, modality, quantifiers and temporal relations deserve explicit test strata. Dependency parsing and lexicons can localize likely trouble, but scope and discourse require more than matching cue words.

For example:

- “Not every applicant qualifies” differs from “No applicant qualifies.”
- “May not disclose” can involve a different interpretation from simply matching “may” and “not.”
- “Within 30 days” and “for 30 days” concern different temporal relations.
- An exception can govern several clauses rather than the nearest sentence.

These examples illustrate why operator-aware comparison is promising; they are not evidence that a rule-based parser will resolve the interpretations reliably. Stanza supplies analysis infrastructure, and negation research supplies a demonstrated risk category—not a universal semantic verifier. [par.nsf](https://par.nsf.gov/servlets/purl/10396754)

### What you may be overlooking

1. No-error controls may be more informative than additional error examples. A detector that flags every paraphrase can appear sensitive while being operationally unusable.
2. Source ablation is a cheap test of whether a sophisticated evaluator is actually using its evidence. ACES makes source neglect a central concern. [arxiv](https://arxiv.org/abs/2401.16313)
3. Human correspondence gives a decision-changing oracle ceiling before you improve alignment.
4. Omission detection requires source-side coverage, not only target-side anomaly spans.
5. Document versions may differ in publication date or revision intent. A genuine semantic difference is not automatically a mistranslation.
6. A third language is additional consistency evidence, not a trustworthy reference by default.
7. A compact specialized evaluator may be the final detector—not merely middleware for a larger model. xCOMET-lite and MetricX’s size comparisons make that possibility worth testing directly. [github](https://github.com/google-research/metricx)

## 8. Recommended research decision

Start with a head-to-head test of bidirectional NLI and source-conditioned QE against your embedding baseline, using ACES-style minimal contrasts plus native no-error controls. This is the smallest credible test of a fundamentally different decision rule. [github](https://github.com/google-research/metricx)

Then run the correspondence-oracle experiment. Only invest in new alignment if better correspondence demonstrably creates useful detection headroom.

Finally, test your local 8B as a source-sensitive contrastive scorer under label-order and source-ablation controls. If it does not contribute independent accuracy at a fixed budget, retain it for human-readable explanations rather than treating it as the semantic authority.

The research supports changing the question the system answers. It does not yet support assuming that a more elaborate combination of embeddings, alignment and LLM judgments will answer that question correctly.