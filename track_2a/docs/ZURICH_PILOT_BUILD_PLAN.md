# Stadt Zürich pilot — executable build plan (13 October 2026)

Status: concept accepted by owner, implementation permitted on a separate branch; research submission and PR #12 unchanged.

## Milestone 0 — protect the benchmark (gate)
- Read PR #12's up-to-date experiments, next-experiment protocol, contracts, submission blockers and current branches.
- Never confuse `main`'s stale README with active branch status.
- Keep all pilot inputs and outputs outside pinned SwissGov-RSD dev and final inference paths.
- Do not import site text into benchmark training/prompt fixtures.

## Milestone 1 — inventory federal source examples (read-only)
- From permitted **dev** records only, tally URLs, domains, subjects, language coverage, page kinds and annotated difference categories.
- Produce a reproducible inventory manifest with URL-to-row provenance, **not** a narrative guess about 224 documents; protect the test split even from inspection.
- Select a representative federal example to explain the benchmark without contaminating evaluation.

## Milestone 2 — adapt Scout (code, offline tests first)
- Implement `src/uzh_rsd/zurich_pilot.py` in Python standard library; keep commands separated from `make run`.
- Parse HTML anchors, language alternates and canonical link tags. Normalize tracking-only URL parameters; restrict to approved HTTPS host. Exclude assets, login, forms, external redirects; respect robots exclusions with conservative refusal if robots cannot be evaluated.
- Explicit max-pages, max-depth, timeout, byte-size budget, polite delay and clear statuses. The pilot must not submit forms or run scripted browser journeys.
- Pair only via explicit reciprocal or manually reviewed mappings. Uncertain page association remains `unpaired`.
- Store minimal machine-readable discovery and capture manifests with source URLs, retrieval UTC, SHA-256 and extraction-version labels; no third-party full-text included in committed outputs.
- Offline unit tests verify host restriction, canonicalisation, pairing, robots failure, changed redirects, limit and no invented matches.

## Milestone 3 — real Zürich reconnaissance
- **Only after network-policy review**, run with explicit seeds e.g. a page in `https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich/`; inventory 10–20 pages, depth <= 2, request spacing >= 2s.
- Select 3–5 *confirmed* pairs when available, otherwise report actual paired/unpaired counts. Evidence from DE/EN with independently recorded timestamps.
- Review reuse/terms before preserving or distributing extracts.

## Milestone 4 — B2 adaptation boundary
- Add adapter mapping verified page-pair excerpts to the existing Apertus B2 semantic IR while keeping a dedicated `source_kind=live_city_pilot` and a different output directory.
- No claims of comparable Spearman (no gold), no automatic severity publication.
- Record absent, invalid, unstable and ambiguous source passages; human review each public example.
- Optional example renderer: side-by-side excerpts, links, dates, evidence spans, status `candidate / verified / unknown` and legally binding DE caveat. Viewer is optional after benchmark readiness.

## Milestone 5 — WATCH after submission
- Compare runs only when URL/pair/content extraction/scoring versions are compatible. Classify NEW/PERSISTING/RESOLVED/METHOD_CHANGED/NOT_COMPARABLE. This is future scope, not necessary for Oct 16.

## Acceptance
- [ ] Docs and reuse matrix on a separate branch; PR #12 untouched
- [ ] Offline Python Scout tests pass
- [ ] Bounded Scout emits auditable manifest and explains failures
- [ ] No automatic language pair guess
- [ ] Public-site access is explicit and robots-respecting
- [ ] 3–5 real pairs **if available**, no invented pilot outcomes
- [ ] Benchmark and pilot metrics separated
- [ ] 130+ existing checks unaffected (re-run on relevant host)
- [ ] No test split opened; no secret or site text committed
- [ ] A draft PR with evidence and honest limits

## Reuse assessment
| Accessibility-red-team component | Decision | UZH adaptation |
|---|---|---|
| `src/scout/links.ts` | Port small algorithms | URL normalization, asset filtering and service discovery priority |
| `src/scout/scout.ts` | Rebuild | Bounded BFS, observable failures, policy enforcement in stdlib Python |
| `src/scout/seeds.ts` | Adapt later | Optional same-host sitemap discovery, not a prerequisite |
| `src/scope.ts`, `src/network-policy.ts` | Rebuild safeguards | HTTPS host allowlist, redirect checks, robots |
| `src/provenance/*` | Port principles | Retrieval timestamp, source URL and digest per record |
| `src/triage/*` | Rebuild later | Semantic change categories, uncertainty, evidence trace |
| `src/report/*` | Rebuild later | Source-paired difference viewer, never WCAG claims |
| `src/watch/*` | Defer | Only comparable versioned source captures |
| `docs/CAMPAIGN.md` | Adapt principles | Respectful findings, no unsolicited contact |
| WCAG, axe, journeys, Cloudflare, control-center | Exclude | Wrong domain and too much footprint |

## Follow-up work
Keep development bounded in this branch; code/build PR can be reviewed independently and cherry-picked after user approval. Link this plan from a pilot README, **do not** overwrite `MVP_PLAN.md` or the submission report, as those encode benchmark decisions.
