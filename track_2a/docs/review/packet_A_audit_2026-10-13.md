# Packet A — evidence and implementation audit (read-only subagent, base 9874189, 2026-10-13)

Run `track_2a/results/20261012T062327Z-ff965461`, branch feat/b0-b2-mvp. Nothing in the repo was modified. No inference, network or compute. Only dev data (`data/raw/.../dev_*.jsonl`) was read.
Scratch scripts were kept outside the repository (read-only, python -B) and are not committed.

## Verified claims
- Model `swiss-ai/Apertus-v1.5-8B` rev a411d83, transformers, greedy, L40S (run_meta.json). 9 dev docs (43/136/197 x de/fr/it), 18 calls, 0 failed.
- B0: 3/9 parseable (`admin_*_43`). `*_197`: finish_reason=length at 4096 tokens (3 truncated). `*_136`: finish_reason=stop but invalid JSON
  (bare items such as `".", "12", 0]`) (3 malformed). Fallback 46 of 541 = 16+15+15; 541 = 88+89+88+93+88+95 (both sides of the three 43 docs). Denominator is correct.
- B2: 9/9 parseable, 41 items, 34 projected, 62 exact, 0 normalised, 4 not_found (all in admin_fr_43), 1 ambiguous (admin_de_197, ADDITION sev 1, 4 occurrences, all marked).
- Matched macro: B0 0.136 (0.143/0.133/0.132), B2 0.138 (0.324/-0.093/0.183). Our Spearman equals the official `compute_correlations` in every view/language/method (results.json `official_spearman`).
- Cost: B2/B0 completion tokens 4682/22945 = 20.4 %; latency 149.8/732.8 s = 20.4 %. Claim "~20 %" holds.
- compute.json: **three** jobs (failed smoke 6acbc136 $0.09, smoke 6acbc1d5 $0.09, measured run 6acc7ce1 $0.57 = (17+2) min x $0.03); sum $0.75. That is an upper bound, not checked against billing (`exact_billing_checked: false`). The "four jobs" wording is wrong.
- Prompts: rebuilt offline from `InferenceInput` for all 18 records; sha256 and stored text match exactly. Raw records carry no label fields, and no gold vector appears in any prompt.
  `InferenceInput` has no label fields (data_adapter.py:65-75). Gold is loaded only in scoring (scoring.py:3,142). No gold leak.
- Prediction files: every exported vector length equals the token count of its side. text_a matches the source, all values in [0,1].
- Severity: `difference = severity/5 = 1 - similarity/5` (severity.py). B0 uses the official mapping; B0 model `-1` → 0.0 (methods.py:96-100), disclosed as deviation 3 (report l.60), 9 tokens.
- Gold punctuation (-1) masked after concatenation. Side b is skipped if all-masked, which mirrors the official script (evaluation.py:67-86).
- Three views are implemented as documented (scoring.py:137-156). Language denominators: matched = 1 doc/language (160/166/168 unmasked positions); available B2 = 3 docs/language (840/930/892).
- Unit tests: 83 tests OK, 0 skipped, with `.venv/bin/python` (run via unittest directly; `make s1-check` not used because it writes runs/s1-check.log).

## Task 1 — the four unlocated excerpts in admin_fr_43 (repo `locate()` on local dev data)
| # | side | model excerpt | source text (closest same-side span) | classification |
|---|---|---|---|---|
| 1 | b | `... places d'apprentis employés ...` (ASCII `'`, emitted as `'`) | `... places d’apprentis employés ...` (U+2019) | normalisation mismatch (model substituted the apostrophe; `_normalise` strips quotes only at token edges, methods.py:135-136) |
| 2 | b | `N'h''esitez pas à présenter ...` | `N’hésitez pas à présenter ...` | model copy corruption (garbled word; this is not a paraphrase, and no locator change short of fuzzy matching recovers it) |
| 3 | a | `Links www.stelle.admin.ch Specialist staff` | `Links www . stelle . admin . ch Specialist staff` | tokenisation mismatch (model removed the spaces around punctuation, against prompt rule prompts.py:89) |
| 4 | b | `Liens www.stelle.admin.ch Contact spécialisé` | `Liens www . stelle . admin . ch Contact spécialisé` | tokenisation mismatch (as #3) |
None of the excerpts sits on the wrong side, and none is ambiguous. No implementation defect: the locator behaves as documented. Items 1 and 3 are partially projected (the other side was located). Item 4 is dropped entirely.

Sensitivity (diagnostic only, NOT a legitimate repair, since it uses hand-placed spans): fr_43 rho -0.093 → +0.021 with all four placed;
apostrophe-only +0.038; www-only -0.134. Matched B2 macro would be ~0.176. Unlocated excerpts explain part of the negative EN–FR score,
but placing them only lifts it to about zero. The report wording "driven by admin_fr_43, where four excerpts could not be located"
(technical_report.md:130) is a causal overstatement: n = 1 doc, and the effect is mixed in sign.

## Findings (ranked)
1. **MAJOR — 14 "too_long" excerpts silently missing from all human-readable reporting.** results.json coverage shows
   `spans_too_long: 14`, but results.md (scoring.py:251-253), per-document diag (scoring.py:198) and the report (technical_report.md:127, 64-75)
   mention only 4 not_found. The 40-token parser cap (methods.py:30, 148-149) is not documented in the report (the prompt asks for ≤15 words).
   6 of the 7 unprojected items are caused by the cap, not by not_found (de_136, fr_136 x1 + 2 half-items, it_136, de/fr/it_197 with
   104-token excerpts). The "4 not located" claim is true but incomplete. Repair (bounded): add `spans_too_long` to render_markdown and _doc_diag,
   and state the 40-token cap and its count in report §B2/§results. This changes no numbers (correlations unchanged), only disclosure.
2. **MAJOR — selection bias in the matched view.** Matched = only `admin_*_43` (the shortest doc, 88 EN tokens). It is one doc per language, and all
   three share the same English source, so they are not independent. B0 survives only on short documents, and B2 is compared on B0's easiest case.
   Report l.101 discloses the IDs, but "n = 3" reads as three independent samples. Repair: state "1 document per language, same EN source;
   per-language rho on ~165 tokens" and add no inferential claim. No number changes.
3. **MINOR — overstated causal sentence** (technical_report.md:130), see the Task 1 sensitivity. Repair: replace with "B2 EN–FR is negative on
   the single matched FR doc; 4 excerpts there were unlocatable (apostrophe substitution, garbled copy, de-spaced URL); a diagnostic
   placement of them yields ≈0.02, so they do not fully account for it." No number changes.
4. **MINOR — paper-protocol view favours B0 by construction.** B0 0.268 > B2 0.175 because 6 zero-filled docs (all ties) rank differently.
   It is labelled as a sensitivity check (scoring.py:10-13), which is fine. Ensure no headline uses it. Info only.
5. **MINOR — "four jobs" wording** (handoff l.37 already flags it): compute.json lists 3 jobs, total ≤$0.75. Use "three jobs". No number change.
6. **MINOR — test robustness:** with system python3 3.15 (no official-eval deps) test_mvp_pipeline.py:107 raises KeyError
   `official_spearman` instead of a clear skip/failure. It passes in .venv. Repair: assert the presence of the key with a clear message. No number change.
7. **INFO — B0 fallback composition:** most of the 46 fallbacks come from bare-string items (`"."`), which upstream `parse_token_labels` accepts
   without a label (official evaluation/utils.py:61-110). This is upstream-faithful. Our NaN sentinel → similarity 5 → diff 0 is equivalent to the upstream fallback.
8. **INFO — ambiguous excerpt** (de_197, sev 1, 4 marks): documented over-marking. Its effect is not quantified; it is low severity.
9. **INFO — B0 deviations 1–4** in the report match the code (prompts.py:68-77 token list ensure_ascii=False; methods.py:66-78 json/literal_eval;
   methods.py:96-100 -1→0; backend). No silent JSON repair, no fuzzy matching (only exact + casefold/edge-quote normalisation, 0 hits).

Would any repair change reported numbers? No. All proposed repairs are disclosure-only. The only number-changing intervention
(placing the unlocated spans) is a prohibited fuzzy/hand repair and is shown only as a diagnostic.

## Not checked
- Whether the 9 B0 `-1` labels fall on gold-punctuation tokens (if so they are masked and their effect is nil; not verified per token).
- The exact JSON error position in each `*_136` B0 output (only confirmed unparseable by both json and literal_eval).
- HF billing page (exact cost), job.log contents, prior_jobs logs, launch.json, bundle hash vs source commit 19b6183 vs base 9874189.
- Manifest selection rule (`select_manifest_docs`) and list_to_drop exclusion correctness, beyond the manifest sha recorded in run_meta.
- Report sections other than §B0/B2/results/limitations lines grepped.
