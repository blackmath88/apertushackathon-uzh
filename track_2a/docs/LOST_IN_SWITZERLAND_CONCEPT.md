# Lost in Switzerland — concept (13 October 2026)

## Thesis
**Same city. Different language. Same information?** Government information should be understandable regardless of language; the question is empirical, not an allegation that a public authority is publishing errors.

Our Hack Apertus UZH Track 2A entry has **three deliberately separated layers**:
1. **Scientific engine (submission-critical):** reproduce the SwissGov-RSD paper B0 baseline and compare Apertus v1.5 B2 typed differences projected to token scores on a frozen dev sample. Report Spearman per EN–DE, EN–FR, EN–IT, macro averages, coverage, failures, cost and uncertainty. The held-out test split remains untouched during development.
2. **Stadt Zürich real-world pilot (extension):** discover a small, safely bounded set of German and English municipal public-service pages, establish *actual* correspondence rather than guess from similar URLs, capture reproducible dated evidence, and apply the same semantic engine to plausible mismatches subject to human verification. **No SwissGov-RSD gold scores exist for these pages**; do not call pilot observations benchmark results.
3. **Evidence-first story (optional):** a compact source-linked bilingual demonstration with full context, unknown/abstain states and German-authoritative-content caveat. No rankings, unsupported accusations, fake finding counts, automated outreach or full-document republishing.

## Data origin and generalisation
The UZH SwissGov-RSD benchmark comprises 224 multilingual Swiss **federal** government documents sourced from admin.ch in EN/DE/FR/IT. Audit dev-only source URL fields and document types before selecting pilot examples; never open test rows for inventory. Stadt Zürich is intentionally out-of-domain: machine-assisted multilingual city website content is a useful *field trial*, not a validated research corpus. Capture and disclose domain shift.

## Product workflow
```
OFFICIAL PAGE SEEDS
  → SCOUT (bounded allowlist, robots, no login, no site actions)
  → PAIR (hreflang/canonical/manual reviewed equivalence)
  → CAPTURE (URL, UTC retrieval, content hash, extraction version, language, excerpt offsets)
  → DETECT (Apertus B2 candidate semantic changes)
  → VERIFY (span localisation, uncertainty, human review)
  → EXPLAIN (paired original citations, caveats, no automated publication)
  → WATCH (future, only on comparable revisioned evidence)
```

## Working case
Pilot host `www.stadt-zuerich.ch`; focus first on newcomer information, registration deadlines and adjacent high-consequence service guidance. A changed deadline, fee, required document, eligibility qualifier or absence could matter, but **none is asserted here**. Accept explicit DE/EN pairs only; log `unpaired` instead of inferring equivalent pages from a URL translation. German page is the primary legal text; translations are assistance, not binding legal advice.

## Reuse from accessibility-red-team
Reuse **concepts and small deterministic algorithms**: scoped discovery, URL canonicalisation and noise filtering; explicit breadth/depth budgets; surfaced not-silenced access failures; immutable capture manifests; evidence references; candidate versus verified distinctions; manual review; no-LLM scout; optional comparison only when versions remain comparable. Rewrite in the UZH project's Python stack and its domain-specific evidence contracts; do not import WCAG, axe, site assessment, outreach, governance control center, Cloudflare, Playwright journeys or accessibility finding taxonomy. Attribution to `blackmath88/accessibility-red-team` should remain explicit.

## Authority and evaluation boundaries
- New pilot branch is isolated from the existing draft B0/B2 PR #12; no merge or deployment.
- Running against a live public website requires robots and site rules compliance, rate limits, retention minimisation and review of lawful quotation/reuse.
- The pilot does not determine wrongdoing or translation quality from model scores alone.
- Do not use test data, initiate paid compute, publish third-party text, send outreach, change repository visibility or dispatch a Weavr Mission without distinct approval.
- Keep baseline experiments and final submission preparation first priority through 16 October 2026 12:00 CEST.
