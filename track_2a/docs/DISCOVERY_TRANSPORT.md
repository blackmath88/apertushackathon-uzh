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
