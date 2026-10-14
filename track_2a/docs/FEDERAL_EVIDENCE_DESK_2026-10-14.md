# Federal-first evidence desk

## Product direction

Lost in Switzerland helps a federal public-service editor compare language versions, inspect evidence and record a review decision. Federal sources are the primary workflow. Zürich remains a secondary transfer example, not the default product story.

The benchmark evaluates detector quality. The application owns capture provenance, reading, review and export. Neither a valid JSON response nor a human review draft is a benchmark-quality claim.

## Delivered slice

New module: `uzh_rsd.federal_desk`, built on PR21's existing `capture_html` extraction and exact-host federal profile. It does not change the existing crawler, scientific methods or judge entrypoints.

- Import permitted local BFE HTML pairs with explicit provenance and language labels (DE/FR/IT/EN); no implicit crawl.
- Finding-led bilingual reading with exact excerpt highlights and expandable full captured context.
- Separately named experimental detector `federal-exact-excerpts-v1`, one bounded local request, both-direction comparison, exact/ambiguous/missing evidence locations.
- Loopback endpoint fixed to 127.0.0.1:11436, model-list identity check, redirects and environment proxies disabled. Operator-supplied weight hash/runtime revision are provenance, not weight attestation.
- Immutable attempt intent, raw response and output bundle. No automatic retry or overwrite. Interrupted attempts leave intent and must be settled before another attempt.
- Review drafts scoped to bundle digest, optional browser persistence, JSON export and CLI validation. Confirm/reject/unresolved require a reviewer and reason. Confirmation rejects ambiguous evidence; absence claims require explicit full-source review.
- Validated review exports carry source URLs/hashes, candidate excerpts/locations, method and fixture/publication status; original captures are unchanged.

This reuses the evidence-desk interaction principles from PR22, not a merge of that branch's DE/EN-only schema. Full consolidation and migration of historical bundles remains follow-up work. The new detector is not benchmark B2 and has no measured reliability claim.

## Run the complete offline example

From `track_2a`, in a fresh output directory:

```sh
PYTHONPATH=src python -m uzh_rsd.federal_desk demo --out runs/federal-desk-demo
```

Open `runs/federal-desk-demo/index.html` locally. The DE/FR example and its two candidates are project-authored, not government content or actual model output. Read, review and export a draft, then validate it:

```sh
PYTHONPATH=src python -m uzh_rsd.federal_desk review \
  --bundle runs/federal-desk-demo/bundle.json \
  --drafts /actual/path/federal-review-draft.json \
  --out runs/federal-review-validated.json
```

Export is a private review record, not automated publication. Identity remains self-declared. The model never supplies human review state.

## Import permitted federal captures

Keep original HTML files private alongside the imported bundle. Their hashes are recorded. Metadata example (replace every example value with verified evidence):

```json
{
  "content_use_permitted": true,
  "rights_basis": "Reference to the actual applicable permission or licence",
  "pairing_rationale": "Evidence that these are corresponding versions of the same service",
  "reviewer": "Actual reviewing person",
  "captured_at_utc": "2026-10-14T12:00:00+00:00",
  "left": {"url": "https://www.bfe.admin.ch/de/actual-page", "language": "de"},
  "right": {"url": "https://www.bfe.admin.ch/fr/actual-page", "language": "fr"}
}
```

This is operator-supplied evidence, not automated legal or pairing validation. Do not set permission true merely to bypass the recorded BFE policy block.

```sh
PYTHONPATH=src python -m uzh_rsd.federal_desk import \
  --left /private/source-de.html --right /private/source-fr.html \
  --metadata /private/metadata.json --out runs/federal-pair.json
PYTHONPATH=src python -m uzh_rsd.federal_desk view \
  --bundle runs/federal-pair.json --out runs/federal-reading.html
```

Import currently supports BFE's exact-host profile only; adding another federal authority needs its own profile/rights review. Language identity is declared by the importer, not automatically established from text.

## Local model acceptance on Nebu

First refresh actual baseline process/ownership and current Weavr state. Do not compete with the running baseline, start/reconfigure services, or touch Morrow. Read the canonical Weavr contract. The owner authorised app development; this document does not dispatch a Mission or expand scientific experiments.

When the already-installed Apertus service is available for this bounded app check, use one permitted pair (or a fresh imported authored fixture), one call maximum, 2,500 combined whitespace tokens, 1,024 output tokens, 90-second request timeout. No cloud fallback, downloads, model tuning or hidden-test access.

```sh
PYTHONPATH=src python -m uzh_rsd.federal_desk analyze \
  --bundle runs/federal-pair.json --model "$LLM_NAME" \
  --weight-hash ACTUAL_64_CHARACTER_SHA256 --runtime-revision ACTUAL_REVISION \
  --confirm-local-inference --out runs/federal-analysis-unique
```

The command writes a reading desk even after ordinary model failures. A timeout leaves actual server completion uncertain: settle it before trying again. `model_calls: null` means delivery/count is unknown; it must not be reported as zero. Exit 0 means complete parseable output, not semantic correctness; failure exits 4. An interrupted attempt has no final bundle and retains its intent.

Model invocation is CLI-driven; this release is not a browser-hosted inference service. Opening the HTML makes no background network/model calls.

## Validation and remaining acceptance

14 focused unit tests pass: immutable/revision-bound review, tampered evidence, ambiguous and absent-side claims, permission metadata refusal, two-sided language contract, single attempt/checkpoints, no output reuse, truncation, interruption, script payload escaping, endpoint mismatch and transport failure. Generated JavaScript passes `node --check`; demo generation succeeds.

No full repository suite was run in this partial cloud checkout. Desktop (1440px) and mobile (390px) Chromium checks passed; screenshots were inspected. No local Apertus or real federal capture was run. Self-review only; independent review remains open. The previously recorded BFE collection block remains unchanged.

Next acceptance: first-time user walkthrough; actual local model call after baseline settlement; a permitted real federal pair; verify a reviewed export with original source context. Preserve failures and distinguish authored fixtures from live evidence.

## Next modules, in order

1. Consolidate federal and Zürich bundle contracts without weakening provenance/review checks; keep old bundles readable through explicit migration.
2. Connect approved crawler captures directly to this import contract and show pairing/extraction gaps.
3. Add detector registry only when another implemented detector is ready; preserve method revision per candidate.
4. Add repeat-capture comparison distinguishing source change, extraction change, method change and lost coverage.

WATCH, authenticated collaboration, public deployment and automatic discrepancy publication are not implemented. A better benchmark model can replace this experimental detector without changing the editorial workflow.

## UX polish — 14 October

Outcome: a guided introduction, selectable findings, side-by-side exact quotations, full-context expansion, plain-language review decisions, completion count, local draft persistence and readable text summary alongside JSON. The authored example includes changed deadlines and omitted advice. A missing-content confirmation stays disabled until the full-source check is acknowledged. Summary exports label unfinished decisions. The backend validation contract remains unchanged.

Scope: renderer/template, authored fixture, package-data declaration, browser acceptance script and this handoff. No model calls, paid services, benchmark modifications, live source capture, merge or deployment. Direct coordinator implementation and self-review; no independent review claimed.

Validation: 14 Python tests, JavaScript syntax check, Chromium desktop/mobile interaction checks, page-error and horizontal-overflow checks, persisted review after reload, omission confirmation gate, summary and JSON downloads. The browser-exported JSON was accepted by the Python review command. Screenshots were visually inspected. Browser tools were installed only in temporary scratch space; no frontend runtime dependencies are added to the application.

Reproduce the browser check with Playwright installed and a compatible Chromium available:

```sh
node tests/federal_desk_browser.cjs runs/federal-desk-demo/index.html runs/ui-check
# Optional CHROMIUM_PATH selects an existing browser binary.
PYTHONPATH=src python -m uzh_rsd.federal_desk review \
  --bundle runs/federal-desk-demo/bundle.json \
  --drafts runs/ui-check/review-draft.json \
  --out runs/ui-review-validated.json
```

The renderer's HTML is explicitly included in setuptools package data. This is still a capture-backed review application, not an automated live crawler or a browser inference service. The demo makes no claims about actual federal discrepancies.

## Campaign workspace

The new [campaign control center](CAMPAIGN_CONTROL_CENTER.md) provides the browser entry point for multi-pair work: create/open campaign → import captures → explicit local comparison → evidence review → campaign report. Run `python -m uzh_rsd.campaign_center --data runs/campaign-center` with `PYTHONPATH=src`. Inference is disabled by default.
