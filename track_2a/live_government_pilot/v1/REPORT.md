# Federal pilot v1 evidence report

Date: 13 October 2026

Branch base: `01c70b1a765587f70acf19d9e2a2de25e7798410`

Source profile: `bfe-federal`

Status: **POLICY_BLOCKED for live content; offline fixture pipeline complete**

## Outcome

The Stadt Zürich Scout is refactored into versioned `bfe-federal`, `ch-citizen` and `zurich-city` profiles in that order, with a compatibility facade for the original Zürich API. The reusable pipeline now covers bounded discovery, content-addressed HTML retention, structured main-content extraction, exact extracted-text offsets, deterministic analysis, explicit pairing/reviewer states and a local bilingual evidence viewer.

No BFE content page was fetched. The two requests made were policy preflight requests only:

| URL | UTC | HTTP | Body SHA-256 | Result |
|---|---|---:|---|---|
| `https://www.bfe.admin.ch/robots.txt` | `2026-10-13T19:54:40Z` | 200 | `9b8ada28ab94e051e4870b7240ff2f3e9a6fa011e696ba0a2df62d60401fa01f` | Wildcard group has empty `Disallow`; this is not a reuse licence. |
| `https://www.admin.ch/de/rechtliches` | `2026-10-13T19:54:42Z` | 200 | `0a27e15ef3cec2be9197dd28803ba9b7de97e3e51cfea97266df87f7e16c9891` | Applicable notice reserves rights and requires prior written permission to reproduce site elements. |

The official Hack Apertus terms reviewed on 13 October 2026 require submitted code to be Apache-2.0, non-code material to be CC-BY-4.0 and datasets to be CDLA-Permissive-2.0, and require third-party material to be publishable under compatible rights: `https://hackapertus.ch/terms-and-conditions`. That open-source publication obligation reinforces the stop decision. Written permission or a clearly applicable reuse licence is the remaining requirement before real BFE source capture can proceed.

## Actual live counts

- Total HTTP requests: **2**, both policy preflight.
- BFE content-page requests: **0**.
- Content pages captured: **0**.
- Candidate, unresolved, rejected or human-verified live pairs: **0** each.
- Apertus/model calls: **0**.
- BFE seeds requested: **neither**.
- Authorities contacted: **none**.

This does not satisfy the preferred genuine-live-pair milestone; it follows the mandated policy stop point and supplies the complete offline path instead. The zero-page machine-readable run is `live-run-manifest-20261013.json`.

## Offline demonstration

The German/French fixtures under `tests/fixtures/live_government_pilot/` are authored for this repository and intentionally equivalent in structure and meaning. They are not BFE text. Their `HUMAN_VERIFIED` state is explicitly scoped to the synthetic fixture pair and is supported by `PAIRING.md`; the baseline candidate remains `UNRESOLVED` because lexical overlap across languages cannot establish equivalence or discrepancy.

The capture schema records source and canonical URLs, locale, retrieval time, HTML and extract SHA-256, extraction revision, ordered heading/paragraph/list/table blocks, exact offsets into `extracted_text`, rights note, pairing evidence and review state. Raw captures use immutable `sha256/<prefix>/<digest>.html` paths and are gitignored; the committed manifest contains bounded synthetic excerpts only.

Method: `deterministic-lexical-structural-v1`, explicitly non-Apertus. It uses no saved B4 SwissGov vectors, no gold labels and makes no live Spearman or scientific-quality claim. B4 remains a separate Qwen3-Embedding-4B result with zero Apertus calls; B5 remains **NOT SUPPORTED** and was not run.

## Safety controls

- Exact approved hostname and HTTPS; reject credentials, ports, lookalikes and non-HTML assets.
- Re-resolve public DNS immediately before requests; reject private, loopback, link-local, reserved and other non-global targets.
- Manual maximum-three redirect handling with full URL and DNS revalidation at every hop.
- Robots fail closed; unavailable/non-200/oversized policy produces a refusal manifest and zero page requests.
- Maximum 20 pages, depth 2, at least two seconds between all same-host requests including robots-to-first-page, 12-second request timeout and 1 MB page ceiling.
- No sitemap traversal, forms, logins, browser actions, site writes, retries, cloud inference or deployment.
- Audit records retain fetched, refused, disallowed, redirect, non-HTML and request-failure states.

## Verification

Focused tests:

```text
PYTHONPATH=src python -m unittest tests.test_zurich_pilot tests.test_government_scout tests.test_live_government_pilot -v
Ran 18 tests in 0.008s
OK
```

After repository-isolated setup and a pinned **dev-only** fetch:

```text
make mvp-setup s1-fetch
make s1-check
Ran 148 tests in 8.029s
OK
manifest reproduces: 61e0e98b7a9347716f4a71bc002364a600993c7346d6046e4f8d65899059a835
test split refused (expected)
```

No official UZH test content or metadata was accessed, enumerated, opened or used. The guard's refusal path was tested only with the literal split name already present in repository tests.

Viewer verification used a real Orca embedded browser against `http://127.0.0.1:8765/viewer.html`; its accessibility snapshot exposed both source links, locales, hashes, capture times, policy limitation, method, review state and observed/inferred caveats. A separate headless Chromium capture produced `demo/evidence-viewer.png` at 1440×1000, SHA-256 `8d1020f2668dd446721c876940aff928973301a7542f667db2e11b531daebecc`. The local server was stopped after the smoke test.

## Reproduction

```sh
cd track_2a
make federal-pilot-demo

# Expected POLICY_BLOCKED exit 3 and no content request under current review:
make federal-pilot-live

# Start, smoke and stop the viewer:
python -m http.server 8765 --bind 127.0.0.1 --directory live_government_pilot/v1/demo
curl --fail http://127.0.0.1:8765/viewer.html >/dev/null
# Ctrl-C stops the server.
```

Architecture concepts are attributed to `blackmath88/accessibility-red-team`: bounded prioritized discovery, strict scope, content-addressed provenance, explicit triage states and escaped static reports. Its repository exposes no licence, so this is a clean-room Python implementation and copies no source code.
