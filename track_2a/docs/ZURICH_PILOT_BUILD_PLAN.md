# Lost in Switzerland — federal-first field-pilot implementation plan

Updated 13 October 2026. **This supersedes the Zürich-first priority of the 13 October version, without removing Zürich as a transfer pilot.** Scientific submission work remains separate.

## Product goal

Deliver a real-world pipeline:
`DISCOVER → PAIR → CAPTURE → ANALYZE → VERIFY → TRIAGE → EXPLORE → WATCH`.

The evaluated UZH SwissGov-RSD benchmark is a *scientific testbed*; the field pilot is an *unlabelled, dated source capture* and must never inherit benchmark scores or gold labels.

## Why federal first?

SwissGov-RSD source material comes from multilingual Swiss **federal government webpages**. Start with pages as close as practical to that publishing environment, *without inspecting the official held-out test split*.

Three explicit source profiles, evaluated in order:

| Profile | Scope | Why | Pilot goal |
|---|---|---|---|
| `bfe-federal` — **first** | `www.bfe.admin.ch` or actual resolved official BFE host; exact host allowlist | Source-domain similarity to SwissGov-RSD, multilingual official pages, administrative and regulatory information | 3–5 verified DE/FR pairs; EN/IT only when actual equivalents exist |
| `ch-citizen` — second | `www.ch.ch` or exact resolved official ch.ch host | Multi-language public-service guidance close to the civic impact story | 2–3 pairs around arrival, registration, health insurance, deadlines |
| `zurich-city` — transfer | `www.stadt-zuerich.ch` | Different government level, city publishing structure and English translation practice | 2–3 genuine DE/EN matched pairs; do not assert equivalence from similar slugs |

Confirmed public seed *candidates* (retrieved 13 October; revalidate before crawling):
- BFE DE: `https://www.bfe.admin.ch/de/dunstabzugshauben`
- BFE FR: `https://www.bfe.admin.ch/fr/hottes-domestiques`
- ch.ch EN: `https://www.ch.ch/en/work/working-in-switzerland-as-a-foreign-national/`
- Zürich DE starting area: `https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich`

The BFE pages are plausibly equivalent by subject. **Their pairing is not proven by subject alone**, and no discrepancy has been verified. Full EN/DE/FR/IT coverage must not be assumed. Profile targets are candidate URLs, not implicit permission to crawl.

## Safety and authority boundaries

- Respect robots.txt, site terms, allowed reuse, rate limits and redirects; review each host's actual policy and permissions before live requests. Approved-profile hostnames only, HTTPS only, no login, forms, external service calls or open crawling.
- Do not scrape or inventory the UZH **test split**, including metadata paths. Prior B5 reported an accidental GitHub tree metadata exposure of test *path names and sizes*; no test contents were read, but avoid repeating even such metadata queries. Permit only explicit train/dev scopes.
- Do not commit whole government HTML or protected third-party text unless rights permit; keep source URL, hash, retrieval timestamp, extraction revision and minimal context needed for auditable review. Raw locally retained captures follow declared retention rules and are gitignored by default.
- Do not automatically publish an error accusation. Human verified source-backed findings are distinct from candidate model outputs. Legal language authority varies by source: avoid making every German federal page uniquely authoritative; document translations versus legally authoritative DE/FR/IT where applicable.
- Do not modify frozen B0–B5 results or other workers' branches. No Weavr Mission dispatch/Need waiver, merge, deployment, publicity, paid compute or change in repo visibility as part of this plan.
- **Submission caution:** B5 verdict NOT SUPPORTED. Published B4 DiffAlign macro 0.187117 on the frozen 30 dev pairs is the strongest *measured complete-coverage alignment baseline* described in PR #17, but its published Qwen3-Embedding-4B predictions require **zero Apertus calls**. It cannot, by itself, demonstrate the challenge's purposeful use of Apertus. Submission method, permissible supporting models, exact final prediction contract, publication rights and Apertus contribution remain independently unresolved; do not quietly submit “B4 Apertus method.”

## Implementation stages (separate independent branch from scientific submission)

### Stage 0 — situational orientation
- Read active PR #13 and current science PRs #12–#19, the current official UZH challenge and publication guidance, repository/Observatory if available and overlapping workers.
- Keep production pilot code and research results isolated; do not rebase or merge another writer's branch. In GitHub preserve an explanatory stacked draft PR.
- Record which seed sites and multilingual source document types are represented in **permitted dev** material only. Reuse existing dev source URL fields with traceable sample IDs; do not enumerate test objects.

### Stage 1 — turn Zürich-only Scout into profile-based Scout
- Existing `src/uzh_rsd/zurich_pilot.py` provides bounded Python discovery: URL normalization, strict host, robots fail-closed, no redirects, delay, HTML sizes, hreflang candidate pairing and SHA-256 HTML capture metadata. **It has not demonstrated a live completed crawl.**
- Extract generic `government_scout` primitives while retaining existing Zürich behavior and tests. Use explicit read-only configuration for `bfe-federal`, `ch-citizen`, `zurich-city`: exact allowlisted hosts, approved seed URLs, max 20 pages, depth <=2, >=2s gap, byte/time ceilings and safe redirect normalization.
- Maintain and enrich page status: fetched, disallowed, redirected, error, no language partner, candidate partner, reviewed pair. Never turn an ordinary cross-link or matching topic into a confirmed language pair.
- Unit-test SSRF redirects, hostname lookalikes, URLs with credentials, tracking-parameter normalization, robots unavailable/disallow, HTML encoding, duplicate pages and languages. Allow a manually reviewed explicit link relationship only with evidence and reviewer status.

### Stage 2 — safe bounded live federal reconnaissance
- Once source access/terms are checked, run a conservative BFE crawl from fixed seeds; no wholesale `admin.ch` crawl. Prefer 10–20 discovered pages and 3–5 *confirmed* DE/FR pairs if actual metadata supports it.
- Record unpaired pages and failures honestly. Manually inspect 2–3 pairs from different topics and source document types, with original URLs and retrieval UTC.
- ch.ch and Zürich remain later profiles; their absence cannot invalidate first federal milestone.
- Provide a small machine-readable source inventory of **what was really retrieved**, distinct from expected benchmark page taxonomy.

### Stage 3 — capture actual content
- Extract main content while preserving headings, paragraphs, list-item context, tables and section order. Preserve original language, URL, text offsets and extracted-span IDs; do not feed HTML navigation and duplicated boilerplate into semantic analysis.
- Establish snapshot schema: page_id, profile, language, canonical/source URLs, retrieval UTC, HTML digest, extract digest/version, section structure, paired relationship, rights/reuse status and document change identifiers. Preserve enough locally retained evidence for reviewer reproducibility; published viewer quotes only minimal permitted excerpts.
- Idempotent reruns and content-addressed caches; *never* silently overwrite earlier evidence.

### Stage 4 — method adapter and reviewable outputs
- Adapter `source_kind=live_government_pilot` maps a verified pair to a stable pair/section/evidence model. It must be independent of gold labels and official test vectors.
- First always compute an explicit non-Apertus/deterministic alignment or lexical baseline suitable for retrieved text. If invoking existing B2 or B3 Apertus, label clearly *experimental and unvalidated* with model/runtime/prompt revision and errors. If running B4 DiffAlign, mark its supporting Qwen model and its non-Apertus status. No method promotion without demonstrated evidence.
- Preserve `CANDIDATE`, `UNRESOLVED`, `REJECTED`, `HUMAN_VERIFIED`; mark parsing failure or unsupported claim as unknown, never agreement.
- Sample human review on real source passages and record precision of reviewed candidates, not Spearman (there is no city/federal live gold).
- Build tiny read-only bilingual evidence viewer with linked original source pages, side-by-side sections, source-backed candidate spans, method provenance, human verdict and legal-language caveats. No invented impact claims.

### Stage 5 — campaign and WATCH (after operational loop)
- Demo story: real federal content → paired multilingual sources → candidate difference → inspection and uncertainty. A verified *equivalence* case can demonstrate trustworthiness without needing to allege an error.
- Add ch.ch citizen-service and Zürich municipal transfer case profiles. Test extraction/generalization failures explicitly.
- WATCH compares versioned captures only where extraction/method/host profiles are compatible, using `NEW / PERSISTING / RESOLVED / METHOD_CHANGED / NOT_COMPARABLE`. Automated notification/outreach is out of scope.

## Acceptance gates

- [ ] All old Zürich offline tests remain passing; new multi-profile safeguards tested
- [ ] Profile allowlists and robots checks verified, not bypassed
- [ ] BFE seeded bounded capture returns actual reported counts and auditable failure statuses
- [ ] At least 3 *verified* DE/FR pairs if site permits; otherwise accurately state limitation
- [ ] A single real bilingual pair flows from capture through baseline analysis to a read-only source-linked evidence viewer
- [ ] Source text/provenance and rights separated from scientific benchmark/test data
- [ ] Frozen benchmark results untouched; no test split metadata/contents accessed
- [ ] B5 negative result and B4 non-Apertus status accurately represented
- [ ] Draft PR and reproducible run manifest; no deployment, merge or unapproved inference

## Reuse matrix (from accessibility-red-team)

| Existing component | Adaptation |
|---|---|
| `src/scout/links.ts`, `scout.ts`, `seeds.ts` | Deterministic URL ranking, bounded discovery, profile seeds |
| `src/scope.ts`, `src/network-policy.ts` | Exact-host, redirect/robots/network restrictions |
| `src/provenance/*` | Content addressing, source timestamps and offsets |
| `src/triage/*`, `src/report/*` | Candidate/verification separation and inspectable site report |
| `src/watch/*` | Later compatible-version change comparison |
| `docs/CAMPAIGN.md` | Neutral evidence-first communication, no automatic accusations |
| WCAG/axe probes, safe journeys, Cloudflare control center | Do not port; wrong problem or scope |

## Current live status as of this plan

Only the profile proposal and Zürich Scout code are known from repository inspection. **No successful BFE/ch.ch/Zürich crawl, live pair verification, content adapter, viewer or WATCH run is established by this plan.** The attached Codex implementation task is separate; this document is not a request to start a governed Weavr Mission.
