# B4 — Alignment-First SDM: research and hypotheses

## Scope and evidence status

B4 asks whether the benchmark bottleneck is semantic recognition, cross-lingual alignment, or projecting a correct decision onto official whitespace tokens. Experiments use only the byte-identical B2/B3 frozen 30-document development manifest (10 EN–DE, 10 EN–FR, 10 EN–IT). Test data is refused in code before a path or URL is constructed.

The complete Perplexity report mentioned in the governing brief was not present in the supplied attachment or repository. A workspace search found only the brief's summary. The hypotheses below therefore use that summary plus the primary sources and pinned implementations listed here; no access to the missing report is claimed.

## Primary sources

- [SwissGov-RSD benchmark paper](https://arxiv.org/abs/2512.07538) defines document-level, cross-lingual token regression. The evaluator is pinned at [`ZurichNLP/SwissGov-RSD@1807a421`](https://github.com/ZurichNLP/SwissGov-RSD/tree/1807a42100e742ed03d337c54c4b9ea86995f565); B4 masks only positions whose gold label is `-1`, then computes global per-language Spearman exactly as that evaluator does.
- [Towards Unsupervised Recognition of Semantic Differences](https://aclanthology.org/2023.emnlp-main.835/) introduces DiffAlign: a token's anomaly is one minus its best cross-document embedding similarity. Its central result is that alignability is a stronger unsupervised signal than deletion or masking.
- [Scaling Unsupervised Word Alignment to Documents via Structural Constraints](https://arxiv.org/abs/2608.21023) and its [MIT-licensed implementation at the pinned commit](https://github.com/ZurichNLP/document-level-word-alignment/tree/60ad0a32bbceb5570ed8440f6bc7a2f470a04c25) extend the alignment study to documents and publish SwissGov-RSD dev prediction vectors.
- [SimAlign](https://aclanthology.org/2020.findings-emnlp.147/) provides unsupervised word alignment from multilingual contextual embeddings. Itermax trades precision for recall and is the natural alternative when explicit counterpart links are required.
- [Vecalign](https://aclanthology.org/D19-1136/) provides embedding-based sentence alignment with one-to-many support and an [Apache-2.0 implementation](https://github.com/thompsonb/vecalign). Its dynamic program is monotone, so arbitrary passage reversal requires a separate retrieval stage.

## Predeclared hypotheses and gates

1. **Location dominates severity.** A1 (exact positive locations, binary score) should remain close to A0 exact gold. If true, finding affected tokens matters more than estimating five severity levels.
2. **Coarse projection is costly.** Broadcasting a perfect decision across a sentence or passage should lose substantial rank correlation. If A3/A4 are weak relative to A1, another sentence-level classifier is not the next experiment.
3. **Small boundary errors matter.** Expansion/contraction and soft decay should quantify sensitivity to token boundaries without model inference.
4. **Continuous alignment is a viable deterministic baseline.** Gold-blind DiffAlign should exceed the frozen full-sample B2/B3 default-zero baselines while producing a finite value for every official token.
5. **Apertus is conditional.** Experiment C is justified only if A and B leave semantic recognition as the leading bottleneck. Otherwise no model calls are made.

Oracle outputs are diagnostics only. They are never passed to prompts, alignment, routing, production features, or submission predictions. A8 is likewise gold-derived: it modulates positive-token severity with deterministic token salience (numeric/URL/case/length) to test whether continuous within-span attribution can reduce ties; it is not a deployable feature.

## Alignment choice

The selected B baseline is the upstream authors' published DiffAlign layer-20 Qwen3-Embedding-4B dev prediction set, pinned by commit and SHA-256. The implementation computes `1 - max(non-negative cosine similarity)` for each subword and averages subwords back to the official whitespace token. Full-document all-to-all matching naturally tolerates passage reversal and does not force a silent zero for unmatched text.

This is the smallest defensible implementation because it is task-native, licensed, continuous, already computed for the exact pinned dataset revision, and avoids inventing an aligner or downloading a multi-gigabyte encoder merely to reproduce published vectors. B4 validates every ID, text, length, finite score, and source hash before evaluation.

The deliberate trade-off is evidence granularity: the published vectors retain each token's maximum alignment confidence (`1 - anomaly`) but not the argmax counterpart index. B4 records that limitation in every evidence record. A future production baseline should regenerate vectors and persist links, ideally comparing unconstrained DiffAlign with CTFAlign; published generation latency and hardware are also unavailable, so B4 reports local replay resources separately.

Alternatives not selected:

- **CTFAlign/MDPAlign:** valuable structural priors, but their order constraints can conflict with the required reversal support; use as an ablation after retaining explicit links.
- **Vecalign + LASER/LaBSE:** strong sentence alignment and one-to-many support, but adds a sentence embedder and remains monotone without retrieval.
- **SimAlign:** offers explicit word links but requires local contextual-model inference and separate sentence/document routing.
- **Custom lexical alignment:** smallest in code, but scientifically weaker cross-lingually and unnecessary given a directly relevant licensed implementation.

No dependency was vendored. Upstream prediction bytes are cached under ignored `data/`, while immutable filtered results and their hashes are committed.
