# Apertus adaptation research — 14 October 2026

Status: research synthesis, not measured results. Start with PLAN.md.
This package archives the two owner-supplied reports unchanged in reports/. They are external research inputs, not accepted implementation instructions. Their attribution and notices remain intact; the repository's code licence does not relicense these reports.

## Decision
Research three separable routes:
- C: frozen Apertus representations with untrained cross-document scoring.
- B: same frozen representations with a small learned scoring head.
- A: generative LoRA/SFT; defer until feasibility and data justify it.

C is the control for B, not a claim of superiority. B requires a separate hidden-state/scoring runtime; working GGUF text generation does not establish that capability. No new inference has been run.

## Corrections to supplied reports
1. Four configurations plus early stopping on the reported validation partition make it a selection set. Reserve a separate evaluation partition, or use nested source-family cross-validation. Never tune against final evaluation.
2. Exactly 96 families, 24 validation families, +0.02 improvement and 22–24 GB free memory are proposed engineering choices, not established requirements. Derive limits from actual data and measured resources.
3. Frozen baseline prediction generation alone does not constitute adaptive exposure. Record whether labels, outputs, errors or aggregate results informed design. Shared English families and all chunks/translations must remain together. If a clean evaluation claim is impossible, report exploratory development results honestly.
4. Consensus cites SmoothQuant and OmniQuant for representation scoring; those quantization papers do not establish RSD effectiveness. Its Court Decisions SFT description conflicts with that project's frozen-backbone README.
5. Claimed dataset split counts and absence of training split need revision-pinned metadata verification before defining the manifest. Do not fetch test content or predictions to verify them.
6. A single A-then-B causal pass cannot give A token states access to B. Separate encodings with an external two-sided comparator are a candidate; their states still have only causal within-document context.
7. Repeating each word label on every subword changes token weighting. Specify pooling or loss normalization explicitly. Preserve exact original token identity; handle multi-token overlaps deliberately.
8. A learned null representation is not part of the proposed fixed best-match linear head unless implemented and evaluated separately. Low similarity is not proof of omission.
9. Head training should use continuous benchmark targets. Invented categorical severity labels must not be presented as human gold.

## Verified primary-source anchors
- Awesome Apertus: https://github.com/rnckp/awesome-apertus — discovery index, not execution evidence; inspected README blob 0fb77216bf37b985f21fce059a0bbd02e407d124.
- SpanDiff: https://github.com/moscraciunxxx/SpanDiff-HackApertus — inspected README blob 2c574eef89e0f7eacc3d708b6c821f6e7f7775ca. Reports hidden-state scoring and development macro 0.3340. Not reproduced here; selected layers/constants are research leads. Do not retrieve its test/full-set artifacts.
- JevPertus: https://github.com/Jaluus/JevPertus — README describes LoRA plus option pointer head, with v1.5 default. Not token RSD.
- Evidence Lab: https://github.com/hallzyx/apertus — inspected README blob 5b213cf028c48d4a571e2e586b7cb809e6b7a86a: frozen Apertus plus learned NLI decision head, separate native backend.
- Court Decisions: https://github.com/beyondExp/apertus-court-decisions — inspected README blob a20d4c9484ab607b667b144829b20a23d2c2b32a: frozen 1.5 reader and classification head.
- Recipes: https://github.com/swiss-ai/apertus-finetuning-recipes — generic recipes do not establish local Intel 1.5 training.
- Community conversion: https://huggingface.co/andreasmartin/apertus-v1.5-8b-text — documents newly initialized special-token head rows and absence of full logit-parity verification. Verify local GGUF lineage rather than assuming it.
- Official evaluator: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/scripts/evaluate_predictions_admin.py — inspected blob da46e98f3907c7914cc25e6fff8241cf2d8a0006. Global per-language correlation pools both sides and excludes gold -1. It can pad/truncate arrays; default split is full, and count-mismatch handling can read full gold IDs. New tooling must enforce dev-only loading and validate exact IDs/counts before invoking compatible scoring. Do not run the unsafe default path.
- Dataset card: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD/blob/main/README.md — documents continuous token labels on both sides and punctuation -1.
- Citation checks: https://arxiv.org/abs/2211.10438 and https://arxiv.org/abs/2308.13137 concern quantization.

Report-specific code compatibility claims not independently inspected here remain attributed leads. Pin and inspect exact implementation revisions before reuse; preserve licences.

## Repository context
At preparation: PR27 baseline handoff and PR29 prompting plan remain draft/open. Owner reports baseline running; remote PR status does not establish host process state. PR28 reports B8 inconclusive; B7's structural comparator remains separate from its unsupported Apertus verifier.
Issue30 contains translation-assisted research and its amendment: https://github.com/blackmath88/apertushackathon-uzh/issues/30.
This is a separate optional workstream; do not silently reorder current work.
