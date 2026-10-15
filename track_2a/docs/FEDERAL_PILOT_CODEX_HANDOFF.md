# Codex local handoff — Federal-first Lost in Switzerland MVP

Context: user approved changing the *field-pilot plan*, **not** merging or broadening Weavr Mission authority. This work must remain independent from UZH judge readiness and frozen B0–B5 scientific results.

## Read-first

- Canonical `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md`; inspect Observstory/Observatory if present, current PR and worker/Orca ownership, current live Weavr state if available. Follow branch isolation. Do not dispatch unapproved Missions or waive Needs.
- `track_2a/docs/LOST_IN_SWITZERLAND_CONCEPT.md`
- `track_2a/docs/ZURICH_PILOT_BUILD_PLAN.md` (federal-first)
- `track_2a/zurich_pilot/README.md` and `src/uzh_rsd/zurich_pilot.py`
- PR #13 (Zürich Scout), #17 (B4), #19 (B5 NOT SUPPORTED); B4/B5 actual experiment reports
- Reuse architecture from `blackmath88/accessibility-red-team`, not its WCAG-specific code
- Current official Hack Apertus submission rules and separate packaging blockers

## Specific assigned outcome

**Build the first operational website-to-evidence path** with federal BFE pages as the primary source and a safe profile-based Scout. Keep ch.ch and Zürich configured as later target profiles, not required to be fully crawled now.

Deliver one reproducible example from real reviewed source pair → bounded capture → deterministic baseline analysis → minimal read-only bilingual evidence viewer.

There is no requirement to report a real semantic discrepancy if none is verified.

## Build order and stop points

### 1. Source-profile abstraction (offline implementation)
- Start from `feat/zurich-semantic-observatory-pilot` or its new federal-first plan descendant, in an isolated worktree; preserve ongoing science branches.
- Refactor hardcoded `HOST` in existing Python Scout into a **versioned explicit host/seed profile**. First profile `bfe-federal`; provide `ch-citizen` and `zurich-city` configuration but do not broaden actual crawl scope.
- Keep HTTPS, no URL credentials/alternate ports, robots fail-closed, limited redirects, SSRF protections, fixed crawl budgets and audit log for refusals. No forms, site writes or unrestricted sitemap ingestion.
- Tests must cover aliases, hostname spoofing, redirects, robots and the original Zürich behavior.

### 2. Real federal page-pair discovery
- Review each BFE page's terms/robots and actual current URLs before live traffic; authorized bounded research only.
- Seed:
  - DE: https://www.bfe.admin.ch/de/dunstabzugshauben
  - FR: https://www.bfe.admin.ch/fr/hottes-domestiques
- Capture page metadata; search no more than 20 pages total, depth <= 2 and >= 2-second interval per host. Both seeds may be fetched as reviewed candidates. Reject/record pages if rules restrict access or content collection.
- Verify pairing by actual metadata, navigation language switch, or **explicit manually reviewed pairing with provenance**. Similar topic is insufficient. Search for 3–5 confirmed DE/FR pair candidates *only if site structure supports it*.
- Record matched/unmatched counts, statuses, date, source URL and content SHA-256.

### 3. Extract and adapt
- Parse main content preserving sections, paragraphs, lists, tables and exact snippet offsets; avoid navigation/footer contamination.
- Build `live_government_pilot/v1` snapshot schema separate from SwissGov train/dev/test: profile, source URL, locale, retrieval UTC, page and extract hash/version, section offsets, rights notes, pair evidence/status.
- Write immutable gitignored raw capture or bounded extracts and a distributable metadata-only evidence manifest. Do not publish full third-party source content.
- Connect captured pair to a **clearly labelled deterministic baseline**, using available token/lexical alignment where feasible. B4's saved SwissGov vectors are not valid predictions for new live pages; local generation would need its pinned Qwen encoder and a documented runtime. B5's M1/M2/M3 cannot be treated as validated improvements. Existing B2/B3 Apertus may be an optional separately authorized experiment with explicit failure/unknown state, not a hidden prerequisite.
- No claim of Spearman on live pages: no gold labels. Never infer correctness or legal conclusion from a score.

### 4. Minimal evidence viewer
- Build a clean, static/read-only, minimal bilingual inspector showing: profile, paired URLs/languages, observed capture dates, side-by-side sections, candidate evidence snippets if any, method name, observed vs inferred, unknown status, source opening links and review decision placeholders.
- Demonstrate a *valid equivalence* case as a legitimate outcome. Clearly distinguish illustrative examples from real captured evidence.
- No backend/cloud deployment, automatic outreach, public naming-and-shaming, or unsupported factual claims.

### 5. Deliver and verify
- Unit + integration test report, source/profile hashes and reproduction instructions; no official test metadata/content read.
- Run a local end-to-end offline fixture and (if robots/rights permit) one real BFE capture. Honest blockers when site policies or source pairing prevent it; no bypass.
- Independent draft PR based on this federal-first plan branch; no merge. Preserve PR #13 existing code and PR #12–#19 scientific artifacts.
- Return actual crawl counts, verified page pairs, source provenance, classification method, viewer path/screenshots where produced, tests, worker/Orca settlement, and explicit open decisions.

## What NOT to do

- Do not run another B5 / competitive alignment experiment; B5 is **NOT SUPPORTED**.
- Do not claim B4's Qwen DiffAlign baseline is an Apertus-powered model; it made **zero Apertus calls**.
- Do not use the held-out UZH test split or even enumerate test metadata. B5 already documented a test-path metadata exposure; avoid repetition.
- Do not alter/substitute judge submission outputs, merge PRs, deploy a public site, contact an authority, make paid inference calls or dispatch Weavr Missions without separate approval.

## Work boundary

The first **deliverable** is a genuine federal pair presented as source-backed evidence with reproducible capture and an inspected, running local viewer. The next phase expands ch.ch and Zürich coverage, semantic finding review and WATCH only after this path works.
