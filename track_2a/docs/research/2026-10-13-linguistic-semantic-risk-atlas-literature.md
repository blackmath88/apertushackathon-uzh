# Research conclusion

Yes: linguistic science can tell you where small translation changes are likely to have large semantic consequences, and established NLP methods can detect some of those changes even when lexical or embedding alignment remains strong. But the evidence does not justify treating a list of important constructions as a calibrated predictor of naturally occurring translation errors.

The most defensible Semantic Risk Atlas is therefore a **constraint-oriented** candidate selector: use linguistic cues to locate obligations, permissions, exclusions, quantities, deadlines and participant relationships; then compare their realization across anchored passages. Keep construction importance, observed error probability and detected cross-language incompatibility as separate signals.

Three findings are particularly important:

1. Your proposed problem already has close prior art. Briakou and Carpuat’s fine-grained semantic-divergence work includes English–French sentence pairs with token-level rationales and explicitly outperforms a sentence-similarity baseline on divergence detection. This is substantially closer to SwissGov-RSD than generic MT quality evaluation. [aclanthology](https://aclanthology.org/2020.emnlp-main.121/)
2. Contrastive translation benchmarks establish that meaning-changing perturbations can defeat evaluation metrics, and recommend modeling language-specific information beyond multilingual embeddings. They do not establish how frequently these errors occur naturally in Swiss government documents. [arxiv](https://arxiv.org/abs/2210.15615)
3. Linguistic vulnerability is not stable error prevalence. A modern study found manual negation-translation accuracy of 95.7% for EN→DE and 94.8% for DE→EN in its evaluated setting. Negation remains consequential, but “contains negation” alone may be a weak anomaly predictor. [aclanthology](https://aclanthology.org/2021.tacl-1.45/)

For B6, I recommend one bounded experiment: test whether a frozen, source-family-aware constraint router captures more B4-missed gold-positive tokens than equal-budget random routing. Only if that succeeds should you test deterministic constraint discrepancies, and only after that should Apertus receive a narrow contrastive verification task.

## 1. Evidence status and project grounding

I inspected the bodies of [PR #17](https://github.com/blackmath88/apertushackathon-uzh/pull/17) and [PR #19](https://github.com/blackmath88/apertushackathon-uzh/pull/19) through the connected repository service. The public-page retrieval did not succeed. I did not independently rerun their experiments or audit every implementation file.

The PR evidence supports a stronger caution than “alignment changes did not help”:

- B4’s reported published macro Spearman is 0.187117.
- At five groups per document, B5’s selected-region oracle replacement reached 0.209271; random-region oracle replacement reached 0.208212.
- The difference between those two oracle results is only 0.001059. Correction opportunity exists, but B5 did not demonstrate a useful selector advantage.
- The regenerated independent-max baseline is not byte-identical to published B4. B6 should preserve the published B4 prediction artifact rather than silently replacing it with regenerated scores.
- PR #17 reports semantic decisions changing under order reversal and label permutation.
- B5 made zero Apertus calls after its alignment gate failed.

These are project findings, not general scientific conclusions. In particular, the oracle correction improvement is not evidence that a deployable verifier can realize that improvement.

Throughout this report:

- Verified empirical evidence means a finding reported in an inspected original publication or official dataset/software record.
- Theory means a linguistic account of meaning or translation relationships.
- Extrapolation means a proposed transfer from that evidence to SwissGov-RSD.
- Project hypothesis means something B6 must test.

Some requested details remain unresolved: several artifact-level licences, complete per-release language manifests, TERMDAT bulk-access permission, and construction-conditioned natural error frequencies. I mark these as unresolved rather than inferring them from public availability.

## 2. What has already been done?

### 2.1 The closest research traditions

Your idea sits at the intersection of five established lines:

| Research line | What it already provides | What it does not provide |
|---|---|---|
| Translation shifts and lexical-semantic divergences | Distinguishes different linguistic realizations from changes in conveyed meaning | A calibrated probability that a construction will be mistranslated |
| Translation difficulty prediction | Predicts lexical uncertainty or human processing effort from translation distributions, surprisal and attention | Proof that difficulty causes meaning-changing errors |
| Fine-grained cross-lingual divergence detection | Detects non-equivalence and sometimes localizes explanatory tokens | Swiss administrative-domain validation |
| Word-level QE and critical-error detection | Learns token/span error predictions from human labels | Guaranteed scope preservation or construction-specific calibration |
| Contrastive evaluation and semantic verification | Tests sensitivity to controlled meaning changes | Natural error prevalence or reliable transfer to Apertus |

The distinction between difficulty and error is especially important. Lim and colleagues predict reading or production time, not erroneous translation. Their research provides candidate features, not an error-risk estimator. [aclanthology](https://aclanthology.org/2024.tacl-1.81/)

### 2.2 Prior-art map: 22 relevant works

Direct links below point to original papers, publisher-hosted records, author-hosted originals or official project records. “Unresolved” means I did not verify the relevant artifact licence or full experimental language list; it does not mean no licence exists. Publication access rights and software/data licences are separate.

| # | Verified work and publication | Mechanism, coverage and data | Findings and limitations | Code/data and licence status |
|---|---|---|---|---|
| 1 | Angelika Kratzer, 1981, [“The Notional Category of Modality”](https://semantics.uchicago.edu/kennedy/classes/s08/semantics2/kratzer81.pdf), in *Words, Worlds, and Contexts* | Formal analysis of modal meaning; German examples; modal interpretation depends on contextual background rather than modal word alone | Foundational theory, not translation-error measurement. Supports separating modal force from contextual reading | Original chapter available; no computational dataset or implementation established here.  [semantics.uchicago](https://semantics.uchicago.edu/kennedy/classes/s08/semantics2/kratzer81.pdf) |
| 2 | Mona Baker, 1993, [“Corpus Linguistics and Translation Studies: Implications and Applications”](https://corpus.bfsu.edu.cn/Baker_1993_Corpus_Linguistics_Translation_Studies.pdf), in *Text and Technology* | Corpus-based study of translated language; discusses explicitness and translation-process characteristics | Research programme, not a construction-conditioned error model. Explicitation must not automatically be labeled divergence | Original chapter available; no reusable implementation verified.  [corpus.bfsu.edu](https://corpus.bfsu.edu.cn/Baker_1993_Corpus_Linguistics_Translation_Studies.pdf) |
| 3 | Bonnie J. Dorr, 1994, [“Machine Translation Divergences: A Formal Description and Proposed Solution”](https://aclanthology.org/events/cl-1994/), *Computational Linguistics* 20(4) | Formal lexical-semantic classes and mappings for cross-language structural divergences | Crucial distinction: divergence in linguistic encoding need not be an error in meaning. Not a modern probabilistic risk study | Original journal record verified; software/data licence unresolved.  [aclanthology](https://aclanthology.org/events/cl-1994/) |
| 4 | Federico Fancellu and Bonnie Webber, 2015, [“Translating Negation: Induction, Search And Model Errors”](https://aclanthology.org/W15-1003/), SSST | Separates sources of negation-translation failure in statistical MT | Historical evidence that polarity preservation is a translation problem; model-specific and not a SwissGov prevalence estimate | Paper verified; raw artifacts and their licences unresolved.  [aclanthology](https://aclanthology.org/W15-1003/) |
| 5 | Daniel Beck, Lucia Specia and Trevor Cohn, 2016, [“Exploring Prediction Uncertainty in Machine Translation Quality Estimation”](https://aclanthology.org/K16-1021/), CoNLL | Predictive uncertainty for QE; three language-pair datasets with post-editing-time targets | Uncertainty provides decision information missed by point-estimate evaluation. Target is editing effort, not administrative semantic divergence | Paper verified; full language list and artifact licence unresolved here.  [aclanthology](https://aclanthology.org/K16-1021.pdf) |
| 6 | Rico Sennrich, 2017, [“How Grammatical is Character-level Neural Machine Translation? Assessing MT Quality with Contrastive Translation Pairs”](https://aclanthology.org/E17-2060.pdf), EACL short papers | EN→DE contrastive pairs derived from WMT references; controlled grammatical and polarity errors | Establishes targeted contrastive evaluation; negation deletion appears as a polarity failure. Synthetic alternatives do not estimate natural prevalence | Paper/test-set methodology verified; artifact licence unresolved.  [aclanthology](https://aclanthology.org/E17-2060.pdf) |
| 7 | Alexis Conneau, Ruty Rinott, Guillaume Lample, Adina Williams, Samuel Bowman, Holger Schwenk and Veselin Stoyanov, 2018, [“XNLI: Evaluating Cross-lingual Sentence Representations”](https://aclanthology.org/D18-1269.pdf), EMNLP | Entailment/neutral/contradiction evaluation in 15 languages; 2,500 development and 5,000 test premise–hypothesis pairs | Provides multilingual inference evaluation, not translation equivalence labels. EN/DE/FR included; IT absent | [Official repository](https://github.com/facebookresearch/XNLI); artifact licence not verified here.  [aclanthology](https://aclanthology.org/D18-1269.pdf) |
| 8 | Fabio Kepler, Jonay Trénous, Marcos Treviso, Miguel Vera and André F. T. Martins, 2019, [“OpenKiwi: An Open Source Framework for Quality Estimation”](https://aclanthology.org/P19-3020/), ACL demonstrations | Word- and sentence-level QE; WMT 2018 EN–DE SMT/NMT | Reproduces winning QE architectures; reports state-of-the-art word-level performance in the evaluated setting. BAD labels are broader than consequential semantic error | Open-source framework; exact code/model/data licences require artifact-level verification.  [aclanthology](https://aclanthology.org/P19-3020/) |
| 9 | Thomas McCoy, Ellie Pavlick and Tal Linzen, 2019, [“Right for the Wrong Reasons: Diagnosing Syntactic Heuristics in Natural Language Inference”](https://aclanthology.org/P19-1334/), ACL | HANS: controlled English entailment examples defeating lexical-overlap, subsequence and constituent heuristics | MNLI-trained models, including BERT, perform poorly on these diagnostic cases. Direct warning against treating overlap as entailment | Dataset introduced; artifact licence unresolved here.  [aclanthology](https://aclanthology.org/P19-1334/) |
| 10 | Yinfei Yang, Yuan Zhang, Chris Tar and Jason Baldridge, 2019, [“PAWS-X: A Cross-lingual Adversarial Dataset for Paraphrase Identification”](https://aclanthology.org/D19-1382/), EMNLP-IJCNLP | High-overlap paraphrase/non-paraphrase pairs; English plus six translated languages, including DE/FR, not IT | Shows structural sensitivity remains a challenge despite lexical overlap. Reports 83.1–90.8 accuracy across non-English languages for its best evaluated setup | Data released; licence unresolved here.  [aclanthology](https://aclanthology.org/D19-1382/) |
| 11 | Eleftheria Briakou and Marine Carpuat, 2020, [“Detecting Fine-Grained Cross-Lingual Semantic Divergences without Supervision by Learning to Rank”](https://aclanthology.org/2020.emnlp-main.121/), EMNLP | Multilingual BERT trained to rank synthetic divergences; REFreSD EN–FR data with token rationales | Improves sentence-level divergence detection over a strong similarity model; token predictions offer finer localization. Closest task match, but only EN–FR and not Swiss legal validation | [Code/data](https://github.com/Elbria/xling-SemDiv); REFreSD has 1,039 pairs; dataset card reports MIT.  [aclanthology](https://aclanthology.org/2020.emnlp-main.121/) |
| 12 | Eleftheria Briakou and Marine Carpuat, 2021, [“Beyond Noise: Mitigating the Impact of Fine-grained Semantic Divergences on Neural Machine Translation”](https://aclanthology.org/2021.acl-long.562/), ACL-IJCNLP | EN–FR divergence-aware training; synthetic and naturally occurring mismatches | Fine-grained divergences affect degeneration and confidence; divergence-aware factors improve quality and calibration. Studies training impact, not pretranslation risk routing | Paper verified; associated artifact licence unresolved.  [aclanthology](https://aclanthology.org/2021.acl-long.562/) |
| 13 | Gongbo Tang, Philipp Rönchen, Rico Sennrich and Joakim Nivre, 2021, [“Revisiting Negation in Neural Machine Translation”](https://aclanthology.org/2021.tacl-1.45/), TACL | Automatic/manual negation evaluation for EN↔DE and EN↔ZH | Manual accuracy: 95.7%, 94.8%, 93.4%, 91.7% respectively. Undertranslation is the dominant error type; rephrasing complicates detection. Not evidence that every negation marker is high-probability error | Paper verified; raw-data licence unresolved.  [aclanthology](https://aclanthology.org/2021.tacl-1.45/) |
| 14 | Markus Freitag, George Foster, David Grangier, Viresh Ratnakar, Qijun Tan and Wolfgang Macherey, 2021, [“Experts, Errors, and Context: A Large-Scale Study of Human Evaluation for Machine Translation”](https://aclanthology.org/2021.tacl-1.87/), TACL | Professional MQM annotation with document context; WMT2020 EN→DE and ZH→EN | Expert error-based judgments substantially change system rankings relative to crowd evaluation; supports context-aware annotation rather than isolated lexical judgments | [Human-evaluation repository](https://github.com/google/wmt-mqm-human-evaluation), Apache-2.0 at repository level.  [aclanthology](https://aclanthology.org/2021.tacl-1.87/) |
| 15 | Jannis Vamvas and Rico Sennrich, 2022, [“As Little as Possible, as Much as Necessary: Detecting Over- and Undertranslations with Contrastive Conditioning”](https://aclanthology.org/2022.acl-short.53/), ACL short papers | Off-the-shelf translation-model sequence likelihoods under full versus partial conditioning; localizes addition/omission without references | Reports accuracy comparable to a supervised QE approach. Particularly relevant to source-conditioned likelihood, but demonstrated on translation models—not Apertus | Paper verified; full pair list and implementation licence unresolved here.  [aclanthology](https://aclanthology.org/2022.acl-short.53/) |
| 16 | Hanna Behnke, Marina Fomicheva and Lucia Specia, 2022, [“Bias Mitigation in Machine Translation Quality Estimation”](https://aclanthology.org/2022.acl-long.104/), ACL | Auxiliary/adversarial objectives counter partial-input bias in QE | Fluent, grammatical translations can receive high scores despite meaning failure; augmented multitask classification mitigates bias. Important contrary evidence for confidence routing | Paper verified; exact artifacts/licences unresolved.  [aclanthology](https://aclanthology.org/2022.acl-long.104/) |
| 17 | Marzena Karpinska, Nishant Raj, Katherine Thai, Yixiao Song, Ankita Gupta and Mohit Iyyer, 2022, [“DEMETR: Diagnosing Evaluation Metrics for Translation”](https://aclanthology.org/2022.emnlp-main.649/), EMNLP | Approximately 31K English examples from ten source languages; 35 controlled semantic, syntactic and morphological perturbations | Learned metrics outperform string metrics overall, but diagnostic categories expose weaknesses. Controlled perturbations cannot estimate natural error rates | [Official repository](https://github.com/marzenakrp/demetr), MIT. Repository packaging describes 35 JSON files with 1K items each; pin the release rather than assuming all count descriptions are identical.  [aclanthology](https://aclanthology.org/2022.emnlp-main.649/) |
| 18 | Chantal Amrhein, Nikita Moghe and Liane Guillou, 2022, [“ACES: Translation Accuracy Challenge Sets for Evaluating Machine Translation Metrics”](https://arxiv.org/abs/2210.15615), WMT | Good/bad contrastive translations across 68 phenomena and 146 pairs | Recommends stronger source conditioning and language-specific information beyond embeddings. Challenge-set composition is not a natural error distribution | [Official ACES/Span-ACES repository](https://github.com/EdinburghNLP/ACES); raw data available; governing dataset/subset licences require verification.  [arxiv](https://arxiv.org/abs/2210.15615) |
| 19 | Zheng Wei Lim, Trevor Cohn, Charles Kemp and Ekaterina Vylomova, 2023, [“Predicting Human Translation Difficulty Using Automatic Word Alignment”](https://aclanthology.org/2023.findings-acl.736/), Findings of ACL | Alignment-distribution entropy and surprisal; behavioral translation difficulty in/out of context | Improves over an embedding-based difficulty approach. Difficulty, ambiguity and error probability are different targets | Original paper verified; language manifest/data and code licences unresolved.  [aclanthology](https://aclanthology.org/2023.findings-acl.736/) |
| 20 | Tom Kocmi and Christian Federmann, 2023, [“GEMBA-MQM: Detecting Translation Quality Error Spans with GPT-4”](https://aclanthology.org/2023.wmt-1.64/), WMT | Fixed three-shot prompting; source+translation; error spans/types/severity; WMT22 EN→DE, EN→RU, ZH→EN | Strong system-ranking evidence, with explicit caution about proprietary black-box dependence. Does not establish small-model span accuracy | Prompt/method public; GPT-4 weights unavailable; implementation licence unresolved here.  [aclanthology](https://aclanthology.org/2023.wmt-1.64/) |
| 21 | Nuno M. Guerreiro, Ricardo Rei, Daan van Stigt, Luisa Coheur, Pierre Colombo and André F. T. Martins, 2024, [“xCOMET: Transparent Machine Translation Evaluation through Fine-grained Error Detection”](https://aclanthology.org/2024.tacl-1.54/), TACL | Joint quality estimation and fine-grained error-span/severity detection; MQM/QE supervision and robustness stress tests | Reports strong sentence/system/span results and detection of localized critical errors/hallucinations. Multilingual architecture is not proof of Swiss DE/FR/IT validity | Open-source learned metric; code, checkpoint and training-data licences must be checked separately.  [aclanthology](https://aclanthology.org/2024.tacl-1.54/) |
| 22 | Zheng Wei Lim, Ekaterina Vylomova, Charles Kemp and Trevor Cohn, 2024, [“Predicting Human Translation Difficulty with Neural Machine Translation”](https://aclanthology.org/2024.tacl-1.81/), TACL | NMT surprisal and attention; CRITT behavioral records, hundreds of translators, 13 pairs | Translation surprisal is the strongest individual predictor of production duration; attention adds information. No demonstrated implication for semantic-error probability | Paper verified; underlying behavioral-data and implementation licences unresolved.  [aclanthology](https://aclanthology.org/2024.tacl-1.81/) |

Two additional works matter for implementation:

- CometKiwi’s WMT2022 system combines COMET with OpenKiwi’s predictor–estimator architecture, word-level tagging and explanation extraction, and participates in critical-error detection. This is an established learned alternative to a handcrafted router. [aclanthology](https://aclanthology.org/2022.wmt-1.60/)
- *xTower: A Multilingual LLM for Explaining and Correcting Translation Errors*—Treviso and colleagues, Findings of EMNLP 2024—demonstrates an explicitly translation-oriented LLM role built on TowerBase. It supports bounded explanation/correction research, not a claim that a general 8B model will reliably verify Swiss legal constraints. [aclanthology](https://aclanthology.org/2024.findings-emnlp.892/)

### 2.3 Research lineage and novelty

The progression is not “linguistics was replaced by embeddings”:

1. Translation-shift research explains why equivalent texts can differ in grammatical form.
2. Lexical-semantic divergence work formalizes cross-language mappings.
3. Corpus research studies translated-language regularities and variation.
4. Word-level QE learns empirical error patterns from post-editing or human annotation.
5. Contrastive benchmarks isolate semantic phenomena that aggregate metrics obscure.
6. Fine-grained divergence models learn localized non-equivalence directly.
7. LLM evaluators produce structured error judgments or explanations.

The genuinely useful combination for your project would be:

> A multilingual, provenance-preserving constraint representation, used first as a gold-blind router, with separately measured routing enrichment and bounded model verification.

None of the ingredients is individually new. The potential novelty lies in the combination of Swiss administrative semantics, exact official-token projection, matched-budget evaluation, explicit legal-authority handling, and a locally measured Apertus contribution.

Do not describe the Atlas as the first linguistically informed semantic-error detector.

## 3. What linguistic theory predicts—and what empirical evidence does not

### 3.1 Separate three targets

For a construction \(C\), distinguish:

\[
I(C)=\text{consequence if its meaning changes}
\]

\[
P(E\mid C)=\text{probability of a meaning-changing error}
\]

\[
P(E\mid C,D,A)=\text{probability given a cross-language discrepancy }D
\text{ and anchoring evidence }A.
\]

A permission/obligation mismatch may have high consequence. A permission word present in both documents may have low error probability. A verified mismatch in modal force, governing predicate and participants is a stronger signal than the word itself.

The third quantity is the most promising deployable target. It also makes clear that a bilingual discrepancy detector is not “predicting an error before translation”: it is selecting likely divergence sites after both versions exist.

### 3.2 Empirical evidence table

“Coverage” below is a qualitative expectation to test on your permitted sample—not a measured SwissGov percentage.

| Risk category | Linguistic justification | Empirical evidence and strength | Confounds and false positives | Likely coverage / frequency status |
|---|---|---|---|---|
| Modality and deontic force | Obligation, permission and prohibition differ in force; modal interpretation depends on context and scope | Strong theoretical support; contrastive/critical-error research supports targeted checks. No verified natural Swiss error-rate estimate | DE *kann*, FR *peut*, IT *può* may express ability or permission; duties can be expressed without modal auxiliaries; different legal formulations may be equivalent | Potentially common in regulatory passages; \(P(E\mid C)\) unestimated.  [semantics.uchicago](https://semantics.uchicago.edu/kennedy/classes/s08/semantics2/kratzer81.pdf) |
| Negation and polarity | Negation changes truth conditions; interaction with modals and quantifiers can change scope | Direct manual MT evidence for EN↔DE and EN↔ZH; modern evaluated accuracy is high, limiting marker-only routing | Rephrasing, morphological negation, *kein*, FR discontinuous negation, IT negative concord, non-negative uses of cue words | Moderate cue reach; reliable local study rates exist, but not SwissGov rates.  [aclanthology](https://aclanthology.org/2021.tacl-1.45/) |
| Quantifiers and bounds | Universal/existential scope; inclusive/exclusive bounds; restriction through *only* | Strong logical rationale; challenge sets establish sensitivity testing, not prevalence | “Up to” may be temporal or quantitative; *only* has varying associates; distributive versus collective interpretation | Moderate, domain-dependent; no verified natural category-conditioned rate.  [arxiv](https://arxiv.org/abs/2210.15615) |
| Numbers, units and quantities | Small substitutions can change amounts, counts, thresholds or eligibility | Strong controlled-perturbation evidence; project B5 also observed cross-occurrence number/date mismatches | Formatting, units, rounded totals, article identifiers, repeated dates; correct values paired to wrong events | Broad, cheap coverage; number presence is not error probability.  [aclanthology](https://aclanthology.org/2022.emnlp-main.649/) |
| Conditions and exceptions | An exception narrows applicability; a condition changes the domain of a rule | Strong formal plausibility; general accuracy/divergence datasets relevant, but no verified dedicated Swiss rate | Exception moved to neighboring sentence; *subject to* can indicate precedence or condition; *unless* transformations require polarity handling | Sparse cue tokens but potentially large governed spans; rate unknown.  [aclanthology](https://aclanthology.org/2020.emnlp-main.121/) |
| Temporal constraints | Dates, durations, endpoints and reference times encode different administrative requirements | Controlled diagnostic evidence for date/quantity changes; normalization tooling exists | “Within 30 days” versus “by 30 June” require event anchors; relative dates need document time; inclusive endpoints may be implicit | Potentially useful in notices/procedures; natural error rate unknown.  [aclanthology](https://aclanthology.org/2022.emnlp-main.649/) |
| Terminology and polysemy | Jurisdiction and domain constrain intended concept; lexical similarity does not guarantee concept identity | Translation-difficulty research supports ambiguity/entropy features; TERMDAT provides contextual terminology | Authorized variants, inflection, nominalization, paraphrase, changing legal terminology; one-to-many mappings | Broad reach, potentially high false-positive burden; difficulty is not error prevalence.  [aclanthology](https://aclanthology.org/2023.findings-acl.736/) |
| Presupposition and pragmatic enrichment | Information can be backgrounded, made explicit, weakened or omitted without simple lexical opposition | Translation-studies corpus rationale; no verified construction-specific natural error estimate | Legitimate explicitation; context supplies omitted information; audience-specific drafting | Poor lightweight localization; postpone beyond hackathon.  [corpus.bfsu.edu](https://corpus.bfsu.edu.cn/Baker_1993_Corpus_Linguistics_Translation_Studies.pdf) |
| Participant roles and relations | Same words can identify different agents, recipients or affected entities | High-overlap NLI/paraphrase diagnostics provide strong evidence against bag-of-words equivalence | Passive/active alternation; nominalization; role recovery errors; equivalent word-order differences | Potentially valuable but parser-sensitive; no Swiss rate estimate.  [aclanthology](https://aclanthology.org/P19-1334/) |
| Discourse, co-reference and list scope | A rule’s antecedent or governing condition can lie outside a sentence | Expert MQM work establishes importance of document context; divergence resources include non-local meaning differences | Sentence-boundary changes, pronoun omission, list formatting, reordered explanations | Large blind spot for five-token windows; rate unknown.  [aclanthology](https://aclanthology.org/2021.tacl-1.87/) |
| Whole-passage omission/addition | Missing propositions can occur without any high-risk cue surviving in the compared version | Direct over/undertranslation detection research; fine-grained divergence work | Legitimate summarized versions, publication scope differences, stale documents, bad segmentation | Essential complementary channel; cue-only Atlas can miss these entirely.  [aclanthology](https://aclanthology.org/2022.acl-short.53/) |

### 3.3 Why cue counting is insufficient

Consider:

- “Applicants must not disclose the information.”
- “Applicants are not required to disclose the information.”

Both contain obligation-related language and negation. Their administrative meanings differ because prohibition and absence of obligation are different relationships.

Similarly, “not all applicants qualify” and “all applicants do not qualify” cannot be safely compared by counting negation and quantifier tokens.

For the Atlas, the relevant object is therefore not simply:

```text
contains: modal, negation
```

but:

```text
actor: applicants
action: disclose
modal_force: obligation
negation_scope: action
```

versus:

```text
actor: applicants
action: disclose
modal_force: obligation
negation_scope: modal
```

These examples illustrate a proposed representation; they are not SwissGov gold annotations.

## 4. Swiss resources, access and redistribution

### 4.1 Practical inventory

| Resource | Coverage and access | A: terminology query | B: local lexicon | C: passage constraints | D: open redistribution |
|---|---|---|---|---|---|
| TERMDAT | Official online database; DE/FR/IT/RM/EN; definitions, usage notes, official names, abbreviations and legislation titles | Yes, through public search | Only after obtaining permission or a clearly licensed export | Useful for concept grounding, not automatic scope annotation | Not established by free online access.  [bk.admin](https://www.bk.admin.ch/en/termdat-the-federal-administrations-terminology-database) |
| TERMDAT help/import documentation | Search guidance; TBX import workflow; Terminology Section contact | Operational guidance | No verified public bulk-export/API entitlement | No | “TermStar Export” documentation concerns preparing data for import into TERMDAT; it is not evidence of a downloadable TERMDAT export.  [bk.admin](https://www.bk.admin.ch/en/termdat-help) |
| Federal Chancellery English Style Guide | Official translator/drafter guidance, including Swiss conventions and DE/FR→EN pitfalls | Useful contextual guidance | Independently authored rules can be informed by it; copying tables requires rights review | Useful for drafting conventions | Document publication is not blanket permission to redistribute substantial extracts.  [bk.admin](https://www.bk.admin.ch/en/style-guides-for-english-language-translators) |
| Federal Chancellery Legal Style Guide | Legal terminology, citations, references and translation pitfalls | Yes, manually | Good source of rule ideas | Useful for legal-text interpretation and normalized citations | Reuse terms unresolved here.  [bk.admin](https://www.bk.admin.ch/en/style-guides-for-english-language-translators) |
| Fedlex | Federal-law collections, multilingual legal resources; structured identifiers and SPARQL access | Legal titles/citations | Potential source for independently derived terminology, subject to rights checks | Strong source for article/version-level anchoring | Verify legal text, metadata and service terms separately.  [fedlex.data.admin](https://fedlex.data.admin.ch/en-CH/home/references) |
| CHEU-lex | DE/FR/IT Swiss–EU agreements and related Swiss legislation; parallel/comparable, structurally and linguistically annotated | Corpus concordance | Useful for contextual term distributions | Useful for legal constructions and cross-language patterns | SwissCoco lists CC BY 4.0, but confirm at the actual downloadable artifact before shipping.  [transius.unige](https://transius.unige.ch/en/research/cheu-lex) |
| SwissCoco | Inventory of Swiss corpora and licence descriptions | Discovery aid | Indirect | Indirect | Do not inherit the inventory’s terms as licences for linked corpora; entries require verification.  [aclanthology](https://aclanthology.org/2025.swisstext-1.14.pdf) |
| Federal administrative web pages | Potentially EN/DE/FR/IT, with varying publication scope | Contextual evidence | Not automatically reusable | Relevant to the observatory | No blanket licence established; verify provider/page terms and third-party material |

### 4.2 TERMDAT: what is verified

Verified:

- Free public online access.
- Swiss legal, administrative and public-sector terminology.
- All four national languages plus English.
- Definitions, explanatory notes and official designations.
- Official search and TBX-import guidance. [bk.admin](https://www.bk.admin.ch/en/termdat-the-federal-administrations-terminology-database)

Not verified:

- A documented public API suitable for your project.
- A general permission to scrape entries.
- A complete downloadable database.
- An open licence permitting republication of entries or a derived database.
- A bulk-export agreement available without contacting the provider.

The safe hackathon approach is to ship an independently authored, small construction lexicon and external TERMDAT entry references—not a scraped TERMDAT mirror. Ask the Terminology Section specifically about machine access, local caching, derived feature tables and redistribution; those are different permissions.

### 4.3 Legal authority is not a majority vote

The Federal Chancellery states that German, French and Italian versions of federal laws are equal and legally binding. It also states that English legislative translations have no legal force. [bk.admin](https://www.bk.admin.ch/en/languages)

That does not imply:

- German is the authoritative original.
- Two agreeing official-language versions automatically defeat a third.
- The English benchmark source defines legal correctness.
- Every administrative website passage has the same authority as enacted legislation.

The observatory should represent:

```text
comparison_source_language
document_type
legal_authority_status
version_or_effective_date
semantic_difference
direction_of_inclusion_if_supported
```

Use “version A permits a broader class of applicants than version B” rather than “version B is legally wrong.” Legal correction requires interpretation beyond pairwise semantic comparison.

## 5. Empirical datasets: what can support conditional error probabilities?

### 5.1 Annotation inventory

| Dataset/resource | Source + translation | Error localization/categories/severity | Corrected reference | Relevant languages | Raw access/licence | Can estimate \(P(E\mid C)\)? |
|---|---|---|---|---|---|---|
| WMT MQM human evaluation | Yes, in released evaluation packages | Error spans, categories, severity; document-aware annotation | References available in associated releases; not necessarily a correction for every annotated output | Strong EN→DE coverage; other directions vary by year | Raw repository; Apache-2.0 repository licence | Within the sampled systems/domain, potentially—if all construction opportunities and no-error segments are retained.  [github](https://github.com/google/wmt-mqm-human-evaluation) |
| WMT word-level QE / post-edit data | Yes | OK/BAD tokens and insertion gaps; labels often edit-derived, not semantic-category labels | Post-edits in appropriate releases | EN–DE and additional pairs; release-specific | Public task data; licences vary and must be checked | Can estimate edit-label association; semantic error probability requires recategorization.  [aclanthology](https://aclanthology.org/P19-3020/) |
| WMT2022 critical-error detection | Yes | Critical-error task labels; exact annotation format depends on subset | Not guaranteed for every item | Task-specific pairs | Public task release; licence unresolved here | Usually cannot infer deployment prevalence without understanding sampling/enrichment.  [wmt-qe-task.github](https://wmt-qe-task.github.io/wmt-qe-2022/) |
| REFreSD | EN–FR pairs | Sentence divergence judgments; token-level rationales | No corrected reference required by the task | EN–FR | 1,039 pairs; MIT reported | Can estimate within-sample divergence association if sampling is accounted for; not Swiss translation-error probability.  [huggingface](https://huggingface.co/datasets/eleftheria/refresd) |
| ACES | Source, reference, good and bad candidates | Phenomenon categories; Span-ACES adds localization | Good/reference alternatives, not natural post-edits | 146 pairs overall; category-by-pair coverage must be inspected | Raw data public; licence verification outstanding | No natural error prevalence: selection is challenge-oriented.  [arxiv](https://arxiv.org/html/2210.15615v2) |
| DEMETR | Original translations and controlled perturbations | 35 perturbation types; designed severity/linguistic categories | Original translation acts as comparator | Ten source languages → English | Raw JSON; MIT | No: estimates sensitivity to designed perturbations, not naturally occurring error rates.  [aclanthology](https://aclanthology.org/2022.emnlp-main.649/) |
| XNLI | Premise–hypothesis pairs, not source–translation error records | Entailment/neutral/contradiction; no translation-error spans/severity | No | EN/DE/FR among 15; no IT | Raw release; licence unresolved here | No: measures inference, not translation errors.  [github](https://github.com/facebookresearch/XNLI) |
| PAWS-X | Paraphrase pairs, not translation-error observations | Binary paraphrase relation; no error severity | No | EN/DE/FR plus others; no IT | Raw data released; licence unresolved | No: useful overlap stress test only.  [aclanthology](https://aclanthology.org/D19-1382/) |
| CHEU-lex | Parallel/comparable legal texts | Structural and linguistic annotations, not gold errors | No systematic corrections established | DE/FR/IT | Corpus described; CC BY listing requires artifact confirmation | No without new error annotation.  [transius.unige](https://transius.unige.ch/en/research/cheu-lex) |
| Frozen SwissGov development sample | Supplied project evidence: official tokens and gold difference labels | Project-specific localization; not necessarily construction type or material severity | Not established here | EN versus DE/FR/IT | Existing permitted project artifacts | Estimates sample-conditioned benchmark association; construction frequency and consequentialness need separate annotation |

WMT’s 2025 fine-grained error-span task explicitly asks for start/end positions and major/minor severity, using MQM and ESA annotations. This confirms that localized consequential-error detection is an established task, but its labels remain distinct from your source-side SwissGov token labels. [www2.statmt](https://www2.statmt.org/wmt25/mteval-subtask2.html)

### 5.2 Denominators are the decisive issue

To estimate:

\[
P(E\mid C)=
\frac{\text{annotated erroneous construction instances}}
{\text{all eligible construction instances}},
\]

you need:

1. All inspected text, including no-error segments.
2. Construction annotation independent of the error annotation.
3. A declared unit: construction occurrence, clause, token or document.
4. A mapping between error spans and construction instances.
5. Known sampling procedures.
6. Controls for language pair, system, domain, length and source ambiguity.
7. Clustering for repeated sources, systems and annotators.

Counting “20% of errors contain negation” estimates neither \(P(E\mid\text{negation})\) nor the benefit of a negation router.

A matched analysis should compare, for example, negation-containing clauses with non-negation clauses from the same system, language pair, document/domain and approximate length. Report unmatched and matched results because matching itself changes the target population.

There is an additional localization problem: a clause may contain an omitted exception, but the annotated error span may be elsewhere—or absent because the exception is missing. Token intersection alone can misclassify the construction’s involvement.

### 5.3 What you can claim by the deadline

You can credibly measure:

- Construction prevalence in the 30-document permitted sample.
- Candidate coverage.
- Gold-positive enrichment.
- B4-missed-positive recall.
- Incremental token-ranking performance.

You cannot credibly derive stable DE/FR/IT Swiss-government construction-conditioned error probabilities from that sample, especially after several development rounds.

Call the first release an evidence-linked risk-feature atlas, not a calibrated epidemiology of translation errors.

## 6. Implementation components

| Component | Recommended role | EN/DE/FR/IT and evidence | Licence/reuse considerations | Important limitation |
|---|---|---|---|---|
| Stanza | Tokenization, lemmas, morphology, dependency structure | Multilingual UD pipeline; appropriate four-language models should be pinned and checked | Apache-2.0 code; verify selected model/treebank terms separately.  [aclanthology](https://aclanthology.org/2020.acl-demos.14/) | Dependencies do not directly provide modal/negation scope |
| HeidelTime | Extract/normalize dates, durations and intervals | Handcrafted resources explicitly include all four languages; TIMEX3 normalization | GPL-3.0.  [github](https://github.com/HeidelTime/heideltime) | Event anchoring and legal deadline interpretation remain separate |
| Independently authored lexical rules | Modal, exclusion, bound and condition cues | Full control over four-language coverage | Your chosen open licence | Coverage and semantic interpretations are hypotheses |
| TERMDAT references | Concept grounding and reviewer evidence | All required languages | Do not bundle entries without verified permission | Terminology match does not establish proposition equivalence |
| REFreSD divergence model | Closest learned baseline or research comparator | EN–FR evidence | MIT reported for released project/data.  [github](https://github.com/Elbria/xling-SemDiv) | Domain and DE/IT transfer unproven |
| OpenKiwi/CometKiwi | Learned token QE comparator | Demonstrated multilingual QE; EN–DE central in OpenKiwi evaluation | Verify exact software and checkpoint licences | BAD/error spans need source-side projection; broad quality ≠ semantic divergence.  [aclanthology](https://aclanthology.org/P19-3020/) |
| xCOMET | Fine-grained learned verifier baseline | Published localization/critical-error evidence | Check checkpoint and code terms separately | Potentially expensive; Swiss administrative transfer unverified.  [aclanthology](https://aclanthology.org/2024.tacl-1.54/) |
| XNLI-based multilingual classifier | Entailment diagnostic, not sole truth arbiter | XNLI covers DE/FR/EN, not IT | Verify model licence and training-data terms | Same-language multilingual NLI success does not guarantee mixed-language pair inference.  [github](https://github.com/facebookresearch/XNLI) |
| Vamvas–Sennrich contrastive conditioning | Addition/omission or likelihood comparator | Translation-model evidence | Verify implementation/model terms | A general causal LLM is a different model class.  [aclanthology](https://aclanthology.org/2022.acl-short.53/) |

For this deadline, do not build a multilingual semantic-frame pipeline unless it is already operational. Dependency-guided local constraints are a more falsifiable initial step.

Likewise, do not assume a negation cue tagger provides scope. Scope extraction should output alternatives and uncertainty where the syntax does not settle interpretation.

## 7. Three substantially different system designs

The following are proposed architectures, not demonstrated systems.

### 7.1 Shared input/output and offset contract

All three should consume:

```text
document_id
source_family_id
language_pair
source_raw_text
target_raw_text
official_source_tokens:
    token_id, text, start_char, end_char
official_target_tokens, if supplied
unchanged_B4_scores
permitted_anchor_candidates
document/version metadata, when genuinely available
```

Candidate output:

```text
candidate_id
source_token_ids
source_char_spans
target_char_spans
risk_categories
anchor_method
anchor_ambiguity
evidence_features
estimated_cost
```

Prediction output:

```text
exactly one finite score per official source token
same order and count as the original artifact
unchanged B4 value outside explicitly selected tokens
```

Offset rules:

1. Preserve original raw text; never overwrite it with normalized text.
2. Establish whether offsets count Unicode code points, bytes or another unit.
3. Normalize only through a reversible alignment map.
4. Map parser tokens to original character spans, then to official-token IDs by declared overlap.
5. Handle multiword-token expansion and contractions without inventing new official tokens.
6. Represent discontinuous cues as multiple spans.
7. Use tokenizer offset mappings for model subwords; never assume parser token IDs equal model `word_ids`.
8. Assert every mapped substring and preserve a text hash.
9. Anchor source-side omission predictions to the actual missing source proposition.
10. Keep cue spans, semantic evidence spans and scoring footprints separate.

The exact official offset convention must be checked against the pinned project artifact; I did not independently verify it here.

### 7.2 Design A: deterministic lexical/structural router

Purpose: test whether linguistic feature selection beats B5 and random routing before introducing a semantic model.

Mechanism:

- Detect numbers, percentages, currencies, dates and bounds.
- Detect modality, negation, exception/condition and restrictive-quantifier cues.
- Use shallow dependencies or clause boundaries to attach cues to predicates.
- Add a separate structural channel for unmatched clauses, list items and headings.
- Rank candidates by a fixed evidence hierarchy, not an invented probability.

Suggested priority:

1. Conflicting normalized constraints with a strong local anchor.
2. Missing constraint in a strongly anchored counterpart.
3. High-consequence construction with ambiguous realization.
4. Cue-only candidate.
5. Structural absence candidate competing under a protected budget share.

Output: candidate spans only; no claim of detected error from cue presence.

Cost: approximately linear scanning plus parsing if enabled; no Apertus inference.

Failure modes:

- Broad lexical matches yield many false positives.
- Legal paraphrases lack expected cues.
- The missing target passage is never correctly anchored.
- High-consequence features crowd out ordinary lexical substitutions.
- Parser mistakes fabricate governing relationships.

### 7.3 Design B: structured semantic-constraint comparator

Purpose: compare administrative propositions instead of individual lexical matches.

Representation:

```text
constraint_id
actor
action
object_or_recipient
modal_force
polarity
quantifier_or_numeric_bound
unit
condition
exception
temporal_anchor
deadline_or_interval
provenance_spans
unresolved_fields
```

Mechanism:

1. Extract candidate constraints separately from each language.
2. Align records using action, participants, headings and local anchors.
3. Compare compatible fields.
4. Produce typed relationships:

```text
compatible
force_mismatch
bound_mismatch
different_condition
different_exception
unmatched_constraint
unresolved
```

5. Assign evidence only to minimal participating spans, with separate proposition-wide coverage diagnostics.

Example deterministic rule:

> If the same strongly anchored actor/action/object has numeric bound \(x\geq a\) in one version and \(x\geq b\) in the other, with the same unit and \(a\neq b\), report a bound discrepancy.

Do not call every weakening a contradiction. Permission versus obligation, for example, is a force discrepancy; the statements are not necessarily logically inconsistent without additional assumptions.

Cost: parsing plus local record matching; potentially \(O(k^2)\) within an anchor block, reduced by partitioning on predicate/participant keys.

Failure modes:

- Equivalent nominalized and verbal predicates do not align.
- Exceptions are attached to the wrong rule.
- One language distributes a constraint across sentences.
- Temporal intervals lack reference events.
- Participant coreference fails.
- The extraction model overcommits instead of abstaining.

### 7.4 Design C: hybrid router with bounded Apertus verification

Purpose: test whether Apertus adds information after deterministic and embedding features.

Router features:

- Design A linguistic cues.
- Design B constraint discrepancies.
- B4 anomaly.
- Anchor ambiguity.
- Structural absence.
- Optional disagreement from already permitted cached alignment features.

Do not require new embedding regeneration for the first experiment.

Apertus input:

```text
source passage + heading/context
anchored target passage + heading/context
one explicit suspected relation
two controlled interpretations or target alternatives
```

Apertus output:

```text
supported alternative
unsupported alternative
unresolved
evidence spans copied from inputs
```

Recommended first role: choose between the observed constraint and one controlled alternative, not enumerate all errors in a document.

Cost: bounded by candidate count and passage length; record tokens processed and wall time. Pairwise anomaly ranking can become quadratic and should not be the first integration.

Failure modes:

- Fluent wrong alternatives win.
- Label and presentation order affect the result.
- Controlled alternative is unnatural.
- Model “repairs” meaning using world knowledge.
- Evidence spans do not support the decision.
- Short passages omit governing context.

## 8. Apertus: five possible roles and their evidence

| Role | Closest actual prior art | What it establishes | What it does not establish | Required local test |
|---|---|---|---|---|
| A. Semantic verification | REFreSD divergence detection; GEMBA-MQM; xCOMET | Anchored bilingual inputs can support divergence/error judgments | Apertus 8B legal competence, exact source localization, reliable multilingual scope | Same/different/unresolved accuracy, counterparty swaps, order invariance, minimal evidence fidelity.  [aclanthology](https://aclanthology.org/2020.emnlp-main.121/) |
| B. Contrastive choice | Sennrich contrastive pairs; ACES; DEMETR | Controlled alternatives isolate sensitivity to specific meaning changes | Natural prevalence; reliable performance when both alternatives are plausible legal phrasings | Human-reviewed four-language pairs; alternative-order reversal; neutral paraphrase controls; real-data incremental ranking.  [aclanthology](https://aclanthology.org/E17-2060.pdf) |
| C. Constraint extraction | xTower’s bounded error explanation/correction is related, but not a dedicated four-language legal constraint extractor | Specialized LLMs can produce helpful translation-error explanations/corrections | Complete, calibrated obligation/exception/deadline extraction | Field-level precision/recall, exact evidence spans, abstention, nested-scope tests.  [aclanthology](https://aclanthology.org/2024.findings-emnlp.892/) |
| D. Conditional surprisal | Vamvas–Sennrich contrastive conditioning; Lim et al. translation surprisal | Translation-model likelihood can support omission/addition detection or predict human difficulty | Causal-LM likelihood as semantic truth; Apertus-specific calibration | True teacher-forced likelihood, counterpart shuffle/ablation, fluency controls, length normalization.  [aclanthology](https://aclanthology.org/2022.acl-short.53/) |
| E. Relative anomaly ranking | Learning-to-rank semantic divergences; contrastive metric evaluation | Relative ordering can be trained/evaluated for divergence sensitivity | Untrained Apertus pairwise transitivity or rank consistency | Reversed comparisons, cycle rate, consistency, held-out family ranking gain.  [aclanthology](https://aclanthology.org/2020.emnlp-main.121/) |

### 8.1 Teacher forcing is not generation confidence

For a fixed target sequence \(y_{1:n}\), actual teacher-forced conditional log likelihood is:

\[
\log p_\theta(y\mid x)
=
\sum_{t=1}^{n}
\log p_\theta(y_t\mid x,y_{<t}).
\]

Every \(y_t\) is the observed target token; every preceding target token is supplied rather than generated.

A useful experimental feature could be:

\[
\Delta_t=
\log p_\theta(y_t\mid x,y_{<t})
-
\log p_\theta(y_t\mid x_{\mathrm{control}},y_{<t}).
\]

But this is a hypothesis about source-conditioning sensitivity, not a semantic-error probability.

By contrast:

- The probability of a generated answer label measures preference over labels.
- Generation top-logprobs do not necessarily include the observed target token.
- Likelihood of model-generated continuation is not likelihood of the fixed document passage.
- A system exposing only next-generated-token probabilities does not implement full passage teacher forcing.

There is empirical reason for caution: recent translation-perplexity research reports that models can be more confident in their own literal outputs than in high-quality human translations, and that lower perplexity is not a universally reliable quality indicator. [aclanthology](https://aclanthology.org/2025.uncertainlp-main.7/)

### 8.2 Narrowest measurable Apertus contribution

Use role B first:

> Given one bounded, anchored administrative claim and two minimally different interpretations, which interpretation does the other-language passage support?

Before SwissGov evaluation, require:

- Alternative-order stability.
- Label-permutation stability.
- Correct rejection of meaning-preserving paraphrases.
- Evidence copied from the actual passages.
- Better performance than a frozen deterministic alternative.
- Sensitivity to changing the counterpart, not merely target fluency.

This directly addresses the instability reported in PR #17 rather than assuming it has disappeared.

## 9. Proposed B6 experiment

### 9.1 Scientific question

At a fixed intervention budget, does linguistic/constraint-based routing capture more gold-positive tokens missed by B4 than B5 suspicious-region routing and random routing, and does a bounded verifier improve the unchanged B4 ranking?

This is one staged experiment, not six opportunities for post-hoc tuning.

### 9.2 Freeze before evaluation

Freeze:

- Exact 30-document manifest.
- Published B4 artifact hashes.
- B5 selector and outputs.
- Source-family grouping.
- Router lexicon and rules.
- Anchor procedure.
- Candidate footprints and tie-breaking.
- Token and inference budgets.
- Contradiction/discrepancy rules.
- Score-fusion formula.
- Random seeds.
- Primary metrics and gates.
- Bootstrap scheme.
- Apertus prompt, model revision, tokenizer, precision and decoding/scoring method.

Prediction APIs must not accept gold. Generate and hash candidate manifests before the scoring process reads annotations.

No official-test content, filenames, blob sizes, metadata, directory listings or identifiers should be inspected. Use explicit permitted development paths, not broad repository trees. This avoids repeating the metadata-access blemish disclosed in PR #19.

### 9.3 Comparison arms

| Arm | Routing | Scoring |
|---|---|---|
| 0 | None | Published B4 unchanged |
| 1 | Frozen B5 suspicious regions | Router diagnostics; same frozen downstream rule when applicable |
| 2 | Equal-budget random regions | Same scoring rule; multiple predeclared seeds |
| 3 | Linguistic risk router | Router diagnostics; B4 unchanged initially |
| 4 | Linguistic risk router | Frozen deterministic discrepancy correction |
| 5 | Linguistic risk router | Deterministic features plus bounded Apertus, only after gates pass |

Important: routing alone does not create a different Spearman score if B4 values remain unchanged. Report routing performance separately; only report new official predictions when a scoring rule actually changes values.

### 9.4 Equal budgets

Use B5’s five-window setting as the compatibility point, but match actual unique official-token scoring coverage—not merely the number of candidate groups.

A clause-wide linguistic candidate must not receive free extra recall.

Maintain separate budgets:

1. Scored source tokens.
2. Context tokens read.
3. Model calls.
4. Total model tokens processed.

For fixed-size-window compatibility, route on a cue or constraint head and use the same five-token scoring footprint. Read broader clause context without silently increasing the scoring footprint.

Also report a secondary equal-token-budget span condition if already predeclared; do not replace the primary comparison after seeing results.

### 9.5 Primary routing metrics

Define “B4-missed” without selecting a new threshold from gold. One reasonable protocol is to freeze the top-\(q\) B4 score set using score ranks and a predetermined \(q\), then evaluate positive tokens outside that set:

\[
R_{\text{missed}}=
\frac{|S_{\text{router}}\cap G^+\cap M_{\text{B4}}|}
{|G^+\cap M_{\text{B4}}|}.
\]

Report:

- Recall of B4-missed gold-positive tokens.
- Overall positive-token recall.
- Precision of selected tokens.
- Gold-negative selected tokens per recovered positive.
- Unique token coverage.
- Documents and language pairs reached.
- Performance by risk category.
- Structural-only contribution.
- Router enrichment relative to random.

Use the existing official positive-label definition; do not invent a binary cutoff for continuous labels without declaring it.

For random routing, use enough predeclared seeds to characterize variability. Match document-level token budgets and legal region boundaries. Add a length/position-matched random control if the primary random policy is unconstrained.

### 9.6 Scoring and official metrics

For any scoring arm:

\[
s_i^{\mathrm{new}}=
(1-\lambda)s_i^{\mathrm{B4}}+\lambda v_i
\quad\text{for selected tokens},
\]

with all other scores unchanged.

Freeze \(\lambda\) and the mapping from discrepancy/verifier evidence to \(v_i\) before evaluation, or use family-separated cross-fitting with an explicitly declared tuning protocol. Never fit and report on the same 30 documents as if the result were untouched validation.

Report:

- Official pooled Spearman according to the actual evaluator.
- Per-language pooled Spearman.
- Macro average separately, not mislabeled as pooled.
- Paired differences against B4.
- AP or another ranking diagnostic only if label conventions permit.
- Finite-score/token-count integrity.
- Tie burden.
- Positive-ranking changes and negative-ranking inflation.
- Runtime, calls and total processed tokens.

### 9.7 Source-family uncertainty

PR #19 reports 27 shared-English groups across 30 documents. Use the actual frozen family mapping.

Bootstrap source families, carrying their language variants together. Do not bootstrap individual tokens as independent observations.

Also report:

- Leave-one-family-out effects.
- Per-language heterogeneity.
- Largest influential family.
- Difference between linguistic and random routing.
- Difference between Apertus and the identical non-Apertus pipeline.

Because this development sample has already informed B4/B5, gold-blind manifests prevent direct leakage but do not erase adaptive researcher exposure. Treat B6 as bounded development evidence, not a fresh confirmatory test.

### 9.8 Proposed gates

These are proposed operational criteria, not literature-derived constants.

Gate 1—routing:

- At the primary equal-token budget, linguistic routing exceeds random B4-missed-positive recall by at least five percentage points.
- Family-bootstrap uncertainty supports a positive difference.
- The result is not driven by one family.
- Precision/negative burden remains within a frozen acceptable range.

Gate 2—deterministic scoring:

- Official pooled Spearman improves by a predeclared useful amount, for example +0.005.
- No severe regression is hidden by macro averaging.
- Score coverage remains complete.
- Rule-level audit does not reveal systematic false contradictions.

Gate 3—Apertus preflight:

- Pass order/label/meaning-preserving controls on a separate synthetic set.
- Demonstrate counterpart sensitivity.
- Meet runtime limits.

Gate 4—incremental Apertus value:

- Compare against arm 4 on identical candidates and scoring footprints.
- Require positive family-aware ranking improvement of the frozen practical size.
- Include shuffled-counterpart and reversed-alternative controls.
- Count unresolved decisions and cost.

Synthetic contrastive examples are capability diagnostics. Their accuracy must never be presented as performance on real SwissGov annotations.

### 9.9 Deadline-compatible execution

Given the October 16 deadline:

- October 14: offset integrity, deterministic rules, frozen candidate manifests.
- October 15: routing gate and deterministic comparator.
- October 16: Apertus only if both earlier stages justify it; otherwise package the negative result and retain B4.

Do not spend the remaining time building a comprehensive ontology or scraping terminology resources.

## 10. The five strongest reasons the Atlas may fail

### 10.1 Important constructions may already be translated accurately

The negation study provides direct contrary evidence to a simplistic “negation is often wrong” assumption. High consequence does not guarantee enough error prevalence for useful routing. [aclanthology](https://aclanthology.org/2021.tacl-1.45/)

Failure signature: many modal/negation candidates, little missed-positive enrichment.

### 10.2 Benchmark differences may primarily be content/version differences

A stale page, removed paragraph, changed publication scope or bad segmentation can produce divergence without a high-risk lexical cue. Addition/omission detection is an established separate problem. [aclanthology](https://aclanthology.org/2022.acl-short.53/)

The present evidence does not quantify how much SwissGov error is caused by publishing workflows. That is a hypothesis to audit, not a verified explanation.

Failure signature: structural-only routing beats construction cues.

### 10.3 Semantic extraction may introduce more errors than it removes

Cue recognition is easy relative to determining scope, participants and exception attachment. High-overlap inference diagnostics show how models can fail on relationships despite recognizing all the words. [aclanthology](https://aclanthology.org/P19-1334/)

Failure signature: deterministic “contradictions” disappear under human review because the governing predicate, unit or condition was mismatched.

### 10.4 Learned verifiers may prefer fluent translations rather than faithful ones

QE partial-input bias is documented: models can reward fluent, grammatical target text despite source-meaning failure. Confidence and surprisal can likewise reflect model preferences rather than adequacy. [aclanthology](https://aclanthology.org/2022.acl-long.104/)

Failure signature: shuffling or removing the counterpart barely changes Apertus decisions.

### 10.5 Local corrections may not improve token-ranking metrics

A model may correctly identify an administrative discrepancy but assign evidence to the wrong official tokens. Conversely, coarse score boosts can damage many negatives. The project’s B4 evidence already identifies token projection as a bottleneck.

Failure signature: passage judgments improve while official pooled Spearman and source-token precision decline.

### 10.6 A specific abandonment result

Abandon construction-based routing as the main B6 direction if, at the frozen equal-token budget:

- Linguistic routing gains fewer than five percentage points of B4-missed-positive recall over random;
- uncertainty does not support a positive gain;
- its negative burden is worse;
- deterministic scoring fails to improve the official pooled metric;
- and oracle replacement within its selected tokens has no meaningful advantage over random-region oracle replacement.

That would not refute linguistic semantics. It would refute this operational candidate-selection hypothesis on the permitted sample.

If Apertus fails counterpart-sensitivity or order-invariance controls, abandon its verifier role independently—even if the deterministic Atlas succeeds.

## 11. Ranked research opportunities

Ratings are reasoned assessments, not measured project results.

| Rank | Opportunity | Literature strength | Novelty | Falsifiability | Reusable resources | SwissGov / observatory value | Apertus role | Deadline feasibility |
|---|---|---|---|---|---|---|---|---|
| 1 | Anchored numeric, temporal and bound comparison | Strong contrastive evidence; mature normalization | Low component novelty; useful provenance combination | Very high | High for tools; terminology not required | High interpretability; likely practical notices/eligibility value | Contrastive adjudication of ambiguous anchors | High |
| 2 | Obligation/permission/prohibition plus condition/exception comparison | Strong theory; uneven natural-error evidence | Moderate application novelty | High | Medium; small original lexicon feasible | Potentially high material consequence | Bounded alternative choice | Medium–high |
| 3 | Structural omission/version-aware routing | Strong omission/divergence prior art | Moderate workflow integration novelty | Very high | Medium | May outperform lexical Atlas if benchmark differences are publishing-driven | Verify unmatched proposition against broader context | High for shallow version |
| 4 | REFreSD-style fine-grained divergence comparator or xCOMET baseline | Strong direct task evidence | Low method novelty | High | Good, subject to exact model licences | Valuable independent comparator; DE/IT/domain transfer uncertain | Apertus must improve on it, not merely imitate it | Medium–low |
| 5 | Contrastive-conditioning likelihood features | Strong adjacent translation-model evidence; important caveats | Higher Apertus-specific novelty | High with source-ablation controls | Medium | Uncertain; may reveal source sensitivity or omissions | True teacher-forced scoring | Low unless local inference already exposes logits |

The strongest literature-supported opportunity is not necessarily the most novel. For this deadline, falsifiability and reusable infrastructure matter more than architectural originality.

## 12. Final recommendation

Build a small Atlas with four separately recorded feature families:

1. Normalized quantities and temporal constraints.
2. Modal force, polarity and applicability conditions.
3. Terminology concepts and ambiguity—not automatic mismatch.
4. Structural absence and unresolved anchoring.

Every entry should include:

```text
construction
languages and patterns
semantic consequence
empirical evidence type
natural error-rate status
known equivalence patterns
false-positive mechanisms
resource provenance
redistribution status
detector implementation
evaluation results
```

Most initial entries should say:

```text
natural error-rate status: unknown
```

That is scientifically stronger than attaching invented risk percentages.

Preserve B4 unchanged as the full-coverage baseline. First measure whether the Atlas selects better places to intervene. Then measure whether deterministic comparisons improve scores. Only then give Apertus a bounded contrastive task, with explicit instability and source-sensitivity controls.

The central lesson from the literature is:

> Linguistic knowledge identifies semantic relationships worth checking; contrastive and divergence research supplies ways to check them; only denominator-aware, matched-budget evaluation establishes whether those checks find real errors efficiently.

For Lost in Switzerland, the defensible contribution is not “we know where translation errors occur.” It is “we expose high-consequence semantic constraints, preserve their multilingual evidence, and test whether those constraints improve gold-blind search beyond embedding alignment and random routing.”