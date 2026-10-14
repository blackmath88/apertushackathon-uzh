# Discovery transport (issue #34)

`src/uzh_rsd/discovery_transport.py` (stdlib only) plus `government_scout.scout()`.

- **One ledger.** Every HTTP attempt (robots, sitemap, feed, HTML, each redirect hop, failures) is reserved in `RequestLedger` before dispatch, paced per host, and settled separately (`completed`/`failed`; `uncertain` after a crash). Typed `Purpose`: robots/sitemap/feed/html, with per-purpose response ceilings and bounded gzip/deflate decompression.
- **Budgets** (`Budgets`): page attempts 20 (existing default, HTML hops+failures), total attempts 40, body bytes 20 MiB, parsed candidates 500, wall clock 600 s. Only pages/depth/2 s delay are established defaults; the rest are **proposed, not frozen**. Exhaustion sets `stop_reason`; queued entries become `unvisited_at_budget`.
- **Network safety.** Environment proxies ignored (`ProxyHandler({})`); the validated address is the address connected to (`PinnedHTTPSConnection`), so a preflight/connect re-resolution gap cannot reach a private address. Manual redirects, each hop scope-checked, counted and loop-checked.
- **URL identity.** `fetch_url` keeps trailing slashes, query order and tracking-like params (only fragment dropped). Legacy `normalize_url` is unchanged for capture/campaign compatibility; `Captured.url` stays legacy-normalised, with additive `requested_url`/`final_url`.
- **Robots.** Fetched per host, fail-closed per host; one host's failure/rules never affect another.
- **Frontier.** `DiscoveryStore` (SQLite; `frontier_path=`): queued, leased, fetched, blocked, failed, excluded, unvisited_at_budget, interrupted. Reopening marks leased work `interrupted` and unsettled attempts `uncertain`; nothing is retried or resumed automatically; earlier interrupted entries are listed in the next result.
- **Compatibility.** Injected legacy `fetcher(url, profile, timeout=, max_bytes=)` still works; hops it reports are charged after the fact (not refusable). Result keeps `schema`, `captured`, `pairs`, `audit`, `request_count`, `page_request_count`, adds `stop_reason`, `frontier`, `attempts`, `accounting`.

Limits: fixture-tested only; no live crawl; Protego/Scrapy/Courlan not adopted (stdlib `robotparser` retained); sitemap/feed purposes are transport-capable but Scout does not expand sitemaps.

Tests: `PYTHONPATH=src python3 -m unittest tests.test_discovery_transport`.

## Discovery inventory (issue #35)

`discovery.py` runs robots-declared sitemaps (index, `.xml.gz`, cycle/depth/count/size ceilings, DTD refused), feeds linked from seed pages, and seed-page navigation/hreflang, all through the #34 ledger. Output is a dated snapshot (`snapshot-<id>.json` in the campaign directory) with sources, candidate states (fetched/blocked/failed/excluded/observed_not_fetched), and page families over de/fr/it/en. A family only joins URLs explicitly linked by an observed source; edges keep direction and `declared_by`; statuses: `single_page`, `one_directional`, `reciprocal_declarations`, `contradictory`; `not_observed` is never absence or translation evidence.

Campaign flow (`campaign_center.py`, Scope tab): preview (no network) → explicit start (`confirm: true`) → progress persisted on the run → selectable families → `scope.page_families` saved and reloaded. Only reviewed profiles are eligible (currently `bfe` → `bfe-federal`); with no injected transport, start is recorded as `blocked: live_discovery_not_authorised` (BFE restriction preserved). Interrupted runs are marked on restart, never resumed.

Not done: desktop/mobile browser run (Playwright not installed here; UI script syntax-checked only); no live observation.

## Evidence captures (issue #36)

`captures.py` turns a saved page family plus a reviewer-certified pairing into a federal_desk bundle with an additive, sealed `capture_evidence` block (schema `lost-in-switzerland/capture-evidence/v1`; old bundles/campaigns lack it and stay valid). Requests use only the #34 guarded transport for reviewed profiles; blockers (checked before any request): unsupported site/host, contradictory family, language not exactly one observed URL, uncertified pair, no recorded content-use permission for non-fixture capture.

Per side: requested/final URL, redirects, status, kept headers, retrieved time, raw sha256/content address (bodies stored once under `raw/sha256/..`), a distinct `retrieval_id`, permission provenance. Extraction records revision, config, offset basis and a completeness check (visible content-region words vs extracted words). Unmatched content => `partial` => `omission_confirmation.allowed=false`, and `federal_desk.review` refuses to confirm LEFT_ONLY/RIGHT_ONLY candidates; extraction failure yields no bundle but keeps the evidence. Pairing stays `CANDIDATE` with family uncertainty. Links separate `live_original` (may have changed) from `captured_evidence`.

Campaign: `Store.capture` / `Store.preparation` and POST `/capture`, GET `/preparation`; without an injected transport capture is recorded as `live_capture_not_authorised`.

Not done: browser UI controls for capture/preparation (API only); no live capture; no desktop/mobile browser run.

### #36 UI (Scope tab → Capture preparation)
Per saved family: pairing/uncertainty, status (`not_captured`/`blocked`/`captured`…), blockers, per-side extraction completeness, omission-confirmation block, distinct *Live original (may differ)* links vs *Captured evidence* hash+time. The capture form (reviewer, rationale, rights basis, languages, certification) appears only when the server has a fixture/authorised transport; otherwise "Capture unavailable". Status is server-derived, so it survives reload. Browser check: `python3 tests/campaign_capture_fixture_server.py 8767 &` then `node tests/campaign_capture_browser.cjs http://127.0.0.1:8767 OUT` (desktop + mobile, page errors, overflow). **Not executed in this environment: Playwright is not installed**; the script and UI were only syntax-checked, and the served API flow was smoke-tested with curl.
