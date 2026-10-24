# Bounded next experiment — paired-evidence verification gate

**Status: planned only; not executed. Gate A remains closed.**

## Single change

Keep C1 generation, parsing, severity mapping, the 40-token locator, max-overlap projection, and official scoring fixed. Add one second-pass verifier that sees the original passage pair plus the parsed C1 difference items and returns only a JSON list of item indices to keep. Its instruction is narrow: keep an item only when the paired excerpts support a factual mismatch; reject faithful translation, paraphrase, reordering, navigation boilerplate, and claims not supported by both cited passages. It must not rewrite excerpts, add findings, change severity, or see gold.

This targets the leading error-analysis category (wrong or unsupported judgement in 11/18 documents) without repeating B2's cap change or confounding the experiment with a new projector.

## Frozen development holdout

Use only the six source groups in `validation_pool` that were not in `validation_execution`: 18 development documents, balanced 6/6/6 across DE/FR/IT and 6/6/6 across short/medium/long. The fixed IDs are:

- short: `admin_{de,fr,it}_199`, `admin_{de,fr,it}_94`
- medium: `admin_{de,fr,it}_215`, `admin_{de,fr,it}_169`
- long: `admin_{de,fr,it}_185`, `admin_{de,fr,it}_104`

Freeze the existing group keys, input hashes, order, prompts, runtime identity, and request ledger before any call. These cases are development holdout only and already carry the broader B0–B8 exposure warning; after execution they must also be marked exposed to this experiment.

## Budget and procedure

- Generate C1 once per document: 18 calls.
- Verify the saved parseable C1 item lists once per document: at most 18 calls; no retries.
- Hard ceiling: 36 calls, temperature 0, loopback Nebuchadnezzar runtime only, existing runtime/model hash checks, no test access.
- If a C1 response is unparseable, both arms use the same explicit zero fallback; do not ask the verifier to repair it.
- Write-ahead intent/result ledger, immutable raw cache, hashes, latency/token counts, and no overwrites.
- Gold remains unavailable to both generation and verification. Join development gold only after all 36 scheduled tasks are settled or explicitly failed.

## Comparison and decision rule

Compare the same saved C1 generation under two projections:

- control: all parseable C1 items;
- treatment: only verifier-kept C1 items.

Primary diagnostic: all-subset fallback-based official macro Spearman. Report per-language scores, paired source-group bootstrap interval, coverage, kept/dropped items, response validity, latency, and call count. Also manually audit a fixed outcome-blind subset of six documents (one source group per stratum, all three languages) for supported-item precision.

Advance this change for further research only if treatment improves macro score, does not reduce usable-document coverage, and improves supported-item precision in the fixed audit. Otherwise reject it. This experiment does not open Gate A and cannot authorize a submission or full run.

