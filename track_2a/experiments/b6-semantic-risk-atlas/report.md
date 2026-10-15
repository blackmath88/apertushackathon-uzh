# B6 Semantic Risk Atlas — scientific decision report

## Verdict

**NOT SUPPORTED.** Do not integrate the B6 atlas router into the submission. Preserve it as a post-hackathon research artifact: the categories are interpretable, but the frozen lexical/structural routing failed the cheapest falsification gate by a wide margin. Apertus calls: **0**. Stage B: **not started**. Stage C: **skipped**. Port `127.0.0.1:11436` was never opened by B6; Morrow on `127.0.0.1:11435` was not touched.

## Frozen order and provenance

The worktree started from exact PR #19 head `25a9813507b6d0ab541ed10a7f9fce379c42148a`. The atlas, provenance, protocol, sanitized identities, all five routing arms, and the selection manifest were committed at `ad345c4` before gold evaluation. The selector checksum is `089848b977d324c04b67aa5bb77abdfac8ebafcaa80d178d92dbf5066d2ae228`; its API accepts no gold or dataset path. The scorer required that exact checksum before it loaded the permitted dev gold.

Primary references were the Swiss Federal Chancellery’s TERMDAT and legal/style guidance, MQM 2.0, Google/WMT human MQM annotations, and an MIT-licensed multilingual false-friends research resource. Exact URLs, revisions, reuse status, and limitations are in `provenance.json`. No terminology database or annotation corpus was bulk-extracted or redistributed. TERMDAT and Chancellery page reuse rights were not assumed where an explicit compatible licence was not found; the atlas patterns are independently authored and released CC0.

## Stage A result

All arms used five non-overlapping radius-2 regions per document. Coverage differences below arise only from boundary clipping and the official punctuation mask. “Oracle” replaces selected eligible B4 scores with dev gold and is diagnostic, not deployable.

| Arm | Eligible coverage | Gold-positive recall | Under-ranked positive recall | Enrichment | Oracle DE | FR | IT | Macro | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B4 unchanged | 0 | 0 | 0 | — | 0.217865 | 0.135347 | 0.208138 | 0.187117 | 0 |
| A0 exact B5 | 3.468% | 15.922% | 13.022% | 4.592× | 0.225287 | 0.160384 | 0.242142 | 0.209271 | +0.022154 |
| A1 risk atlas | 3.094% | 2.864% | 3.207% | 0.926× | 0.232096 | 0.154454 | 0.220236 | 0.202262 | +0.015145 |
| A2 family | 3.094% | 2.864% | 3.207% | 0.926× | 0.232096 | 0.154454 | 0.220236 | 0.202262 | +0.015145 |
| Uniform random | 3.495% | 4.802% | 4.568% | 1.374× | 0.225026 | 0.153863 | 0.234404 | 0.204431 | +0.017314 |
| Existing cue-first | 3.922% | 6.655% | 6.997% | 1.697× | 0.229315 | 0.164581 | 0.232559 | 0.208819 | +0.021702 |

The official B4 baseline covers 30/30 documents and 18,485 eligible tokens (DE 4,837; FR 7,522; IT 6,126). A2 selected 572 eligible tokens, only 34 gold positives and 33 of 1,029 under-ranked positives.

The shared-English-family cluster bootstrap used 27 source families, seed 20261013, and 500/500 valid replicates. A2 macro CI95 is `[0.157602, 0.256780]`; its delta CI95 is `[0.005301, 0.029223]`. These intervals describe sampling instability; they do not rescue a failed, directional gate.

## Gate A

The predeclared primary was A2. Every condition failed:

- under-ranked recall had to exceed A0 and random by 0.02; A2 was 0.032070 versus 0.130224 and 0.045675;
- oracle delta had to exceed both by 0.005; A2 was +0.015145 versus +0.022154 and +0.017314;
- enrichment had to be at least 1.25; A2 was 0.925660;
- at least two languages had to beat A0 under-ranked recall; zero did.

The blocking coordinator decision was “Stop and package.” The frozen failure action therefore sets the verdict to NOT SUPPORTED and prohibits model inference and Stage C.

## Failure analysis

The atlas route over-selected broad, high-frequency structures. Among the 150 A2 regions, category tags appeared 87 times for omission/connective cues, 73 for scope, and 68 for quantities. Those cues are semantically important in principle, but their lexical presence did not identify hidden B4 false negatives: aggregate enrichment fell below random prevalence. Italian was the clearest failure, with only 1.44% gold-positive recall and 0.505× enrichment; DE was less poor (6.49%, 1.487×), showing language imbalance rather than a stable multilingual mechanism.

A2 equals A1 because the exact 30-document sample contains no complete sibling set with the same English source represented in all DE, FR, and IT. The implementation refused to infer links from document-number similarity or incompatible text, so no family boost was applied. This is a pairing failure, not evidence against shared-English agreement in a sample that actually contains verified four-language families.

One evaluation implementation correction occurred after the selection freeze: the first local calculation ranked positives independently inside each document side. The research contract requires pooled-by-language midranks, so that preliminary uncommitted output was discarded and Stage A was rerun with official-style pooled language ranks. Selection bytes, strategies, budgets, oracle scores, and model-call count were unchanged. The committed result checksum is authoritative.

## Integrity and limitations

Every selected region was revalidated against exact official `str.split` tokens and mapped to source `[start,end)` character offsets; all 750 arm-document groups succeeded. B0-B5 frozen result/diagnostic/experiment artifacts remain byte-for-byte unchanged: 65 tracked blobs have canonical base-tree digest `93c4f4d8a05e1b5e9caa2a3f1b76f7c8f54235f16b3c11615f9f359790db99c4`, with an empty diff.

The 30 documents are a small stratified dev sample, the oracle uses gold only after selection, and its score is an unreachable ceiling rather than model performance. The lexical patterns are deliberately compact, incomplete, and context-dependent. No claim is made that absence of a cue implies safety, or that a cue implies a translation error.

No protected test path, metadata, or content was accessed, listed, queried, or downloaded. No external translation-error corpus supplied labels. No paid/cloud compute, model download, prompt search, inference service, final evaluation, or submission action occurred.

## Recommendation

**Post-hackathon only.** Keep B4 unchanged for the current submission. If work resumes later, first construct a larger gold-blind sample that actually includes verified DE/FR/IT shared-English families and replace broad lexical presence with context-sensitive contrast evidence; pre-register a fresh gate rather than tuning this failed router on the observed dev gold.
