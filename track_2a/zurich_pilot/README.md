# Lost in Switzerland — Zürich evidence desk

Real website → dated capture → reviewed DE/EN relationship → experimental B2 candidates → inspectable evidence → separate human review events.

This pilot is independent of the SwissGov-RSD benchmark and judge entrypoints. It has no gold labels, benchmark score, validated production detector or continuous monitoring.

## Implemented

- Bounded, same-host HTTPS Scout: robots wildcard/longest-match subset, rate limits, alternate-link priority, Zürich web-component links, explicit HTTP/redirect failures and stop on 429/5xx. No implicit redirects, forms, login or PDF processing.
- Private immutable HTML and extracted documents: headings, paragraphs, list items, table rows, free text and audited Zürich contact attributes. Character offsets, HTML locators/line numbers, UTC capture times, source/content/record hashes and extraction revision.
- Pair acceptance requires a review record pinned to both capture digests. Explicit language metadata is required; URL shape never establishes correspondence. Reviewer type distinguishes assistant review from human review.
- Provider-independent adapter uses the existing B2 prompt/parser/tokenizer unchanged. One attempt per pair; 1–5 pairs, 2,500 combined whitespace-token input ceiling, 1,024 completion-token cap, 90-second request timeout. The CLI permits only explicitly confirmed localhost Apertus on port 11436. No paid/cloud fallback.
- Candidates retain exact/ambiguous/missing excerpt localisation, model severity, method/model provenance, raw output and unresolved states. Confidence is unavailable. Missing-side claims require human review and are not verified omissions.
- Offline viewer: side-by-side source text, original links, evidence highlights, filters, provenance and review drafts. Drafts are exported, validated by CLI and displayed as separate review events; source/model records stay unchanged. Review identity is operator-asserted, not authenticated.
- Offline extraction regeneration and B2 replay. WATCH is design-only.

## Run locally

From `track_2a`, use `PYTHONPATH=src python -m uzh_rsd.observatory --help`.

### Reading desk v2

The offline viewer now offers **Read sources**, **Source values**, and **Review candidates**. Search page contents or search within the selected pair; jump independently to German/English headings; select block numbers for exact evidence locations. Source values are literal dates, times, phone values and numbers with contexts/offsets—not a discrepancy detector. A value occurring on one side alone is not a verified omission.

Review drafts are retained in browser storage when available, scoped to the exact bundle digest. Export/import is available when browser storage is restricted. Imported drafts are never silently promoted to confirmed records. Bundle exports preserve the original numeric serialization and pass Python integrity verification.

### One-command local analysis

After exporting a capture bundle and verifying the existing Nebuchadnezzar runtime, this is the preferred execution path:

```sh
PYTHONPATH=src python -m uzh_rsd.observatory local-run \
  --bundle runs/capture-bundle.json --runtime runs/runtime.json \
  --model "$LLM_NAME" --confirm-local-inference --out runs/zurich-local

PYTHONPATH=src python -m uzh_rsd.observatory serve \
  --html runs/zurich-local/index.html --port 8765
```

The first command checks the loopback endpoint's reported model ID before any generation request, preserves immutable attempt intents/raw checkpoints and writes `run.json`, `bundle.json`, and `index.html`. An unavailable/mismatched endpoint still yields a reading desk with a BLOCKED status and zero generation calls. A transport failure stops the batch; interruption records an unsettled attempt and never retries it. Completed attempts and parseable model-output coverage are separate from semantic reliability, which remains unestablished. Exit 0 means all pairs returned parseable, untruncated model output; exit 4 means attempts completed with unresolved output; exit 3 means blocked/incomplete. No equivalence or human verification is implied by these statuses.

`runtime.json` must contain actual `model_family: Apertus`, a full `model_sha256`, and `runtime_revision`. Optional `--gguf /actual/model.gguf` verifies that local file against the pin. Endpoint model listing is an observed ID, **not attestation of served weights**. Local requests disable environment proxies and automatic redirects. The command never starts/reconfigures a model service or selects a fallback route.

The second command serves the already-built page read-only on 127.0.0.1. It has no inference/mutation routes, directory listing or public binding. Ctrl-C stops it. File opening also works without a server.

### 1. Capture (explicit network action)

Read [city terms](https://www.stadt-zuerich.ch/de/service/rechtliche-hinweise.html). Downloads are for personal use; further reuse/publication requires rights review. Only German content is legally binding. Never commit captured HTML/text or distribute this viewer publicly without permission.

```sh
PYTHONPATH=src python -m uzh_rsd.observatory capture \
  --seed https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich.html \
  --seed https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich/other-languages/en.html \
  --max-pages 15 --confirm-live --personal-use-only --out runs/zurich-new
```

Outputs go to a fresh run directory: `scout.json`, `html/<sha256>.html`, `documents/<capture-id>.json`. Each capture records restrictions. A blocked robots lookup writes an audit manifest and refuses page requests. Unsupported encoded robots rules/targets fail closed. Discovery success does not imply pairing success.

### 2. Review correspondence

```sh
PYTHONPATH=src python -m uzh_rsd.observatory pair-template \
  --run runs/zurich-new --out runs/pair-reviews.json
```

Reciprocal metadata generates **pending** templates. If metadata is absent, a reviewer can add an explicit `reviewed_relationship` entry with `de`, `en`, both `*_record_digest` values, `status: accepted`, `reviewer`, `reviewer_type: human|assistant`, timezone-bearing `reviewed_at_utc`, rationale and both source URLs in `evidence_urls`. Inspect both complete source pages and service scope. Same topic alone is insufficient. Empty pairing is valid.

```sh
PYTHONPATH=src python -m uzh_rsd.observatory bundle \
  --run runs/zurich-new --reviews runs/pair-reviews.json --out runs/capture-bundle.json
```

### 3. Analyze with local Apertus

Use the already-installed Nebuchadnezzar Apertus runtime; do not change Morrow or create a new provider route. Independently verify the local server/model before invoking the adapter. Supply `runtime.json` with the actual `model_family: Apertus`, full `model_sha256` and `runtime_revision` (and relevant quantization/backend settings). These pins are operator-supplied evidence, not independently attested by this adapter.

```sh
PYTHONPATH=src python -m uzh_rsd.observatory analyze \
  --bundle runs/capture-bundle.json --runtime runs/runtime.json \
  --endpoint http://127.0.0.1:11436/v1 --model "$LLM_NAME" \
  --confirm-local-inference --out runs/zurich-analysis
```

Per-pair raw checkpoints survive interruption. A final `bundle.json` exists only after the bounded attempt sequence finishes. Never automatically rerun failed pairs. Over-budget documents remain unresolved without truncation. No test/development dataset is loaded by pilot commands. The semantic adapter performs no scoring.

### 4. Inspect, replay and review

The capture bundle is also viewable before analysis; it clearly says **analysis not run**.

```sh
PYTHONPATH=src python -m uzh_rsd.observatory verify --bundle runs/zurich-analysis/bundle.json
PYTHONPATH=src python -m uzh_rsd.observatory replay --bundle runs/zurich-analysis/bundle.json
PYTHONPATH=src python -m uzh_rsd.observatory view \
  --bundle runs/zurich-analysis/bundle.json --out runs/evidence.html
```

Open `runs/evidence.html` locally. It needs no server/CDN and makes no background website/model requests. Review drafts stay in memory until exported. Import exported drafts with:

```sh
PYTHONPATH=src python -m uzh_rsd.observatory review-import \
  --bundle runs/zurich-analysis/bundle.json --drafts runs/zurich-review-drafts.json \
  --out runs/review-events.json
PYTHONPATH=src python -m uzh_rsd.observatory view \
  --bundle runs/zurich-analysis/bundle.json --reviews runs/review-events.json \
  --out runs/reviewed-evidence.html
```

Ambiguous/unlocated evidence and truncated output cannot be promoted to human-confirmed by these controls. A model response with no differences does not prove equivalence. Human review of absence requires the complete corresponding page, including extraction gaps and service context. Review events are not public accusations or legal conclusions.

For changed extraction code, use `reextract --run ORIGINAL --out FRESH` over saved raw HTML. Retrieval timestamps stay unchanged; the new extraction revision is explicit. Replay refuses changed method-source hashes rather than pretending a method upgrade is a website change.

## Live acceptance on 13 October

The initial 15-page-budget Scout captured 11 pages, recorded four redirects and found zero reciprocal pairs. A one-page English-directory reconnaissance and four-page service capture then retrieved two DE/EN service relationships (Welcome Desk and German-course advice). The coordinator reviewed correspondence with matching service/contact context; this was **assistant pairing review**, not human confirmation of discrepancies. Opening-hour free text was recovered in extraction v2 by offline regeneration without refetching sources.

The private viewer contains genuine captures, with **zero model calls and analysis not run**. The cloud development session has no local Apertus service on 11436. B2 integration and review interactions are verified with synthetic fixtures only. No invented city differences are included. Text-free capture evidence is in `evidence/live-20261013.json`; source HTML/text and the private viewer remain outside VCS.

## WATCH design (not implemented)

Keep stable URL-based pair identity separate from capture, extraction, method and review revisions. A future repeat scan should distinguish SOURCE_CHANGED, EXTRACTION_CHANGED, METHOD_CHANGED, unchanged source, lost coverage and NOT_COMPARABLE. Never call a disappearing model candidate a resolved discrepancy. No scheduler or repeat-monitor claim exists.

## Verification and boundaries

- `make s1-check`: 160 tests, no skips, manifest reproduced and test split refused on the implementation source before final viewer-only hardening; final verification is recorded in the delivery note.
- Live captures have no semantic accuracy acceptance; no municipal benchmark score is computed.
- Independent review remains open. Coordinator checks are self-review.
- No scientific frozen files, judge entrypoints, Weavr commands, paid inference, merge, deployment or outreach.

Architecture attribution: [accessibility-red-team](https://github.com/blackmath88/accessibility-red-team), particularly Scout, immutable evidence, provenance, triage, report and WATCH principles. This is a Python/domain-specific adaptation; no WCAG findings or accessibility scores are imported.
