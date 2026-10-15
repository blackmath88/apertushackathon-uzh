# Discovery delivery plan

Updated 14 October 2026. Executable issue order for the federal observatory.

## Decision

Extend the existing Scout; do not replace the campaign app or introduce a distributed/browser-first crawling stack. Deliver a trustworthy request/frontier layer, then a real selectable discovery inventory, then evidence-complete capture. Keep inference separate. Preserve blocked and missing states rather than manufacturing coverage.

This plan refines the sequencing in FEDERAL_DISCOVERY_AND_FINDINGS.md. Its broad D1–D6 architecture remains context; the issue sequence below is the current implementation order. The previous research proposal's combined longitudinal/evaluation ticket is deliberately split.

## Issues and dependency order

| Issue | Deliverable | Depends on | Pickup status |
|---|---|---|---|
| [#34](https://github.com/blackmath88/apertushackathon-uzh/issues/34) | Guarded request ledger, corrected URL semantics, pacing/budgets and persistent frontier | Existing application | First implementation slice |
| [#35](https://github.com/blackmath88/apertushackathon-uzh/issues/35) | Directory → bounded discovery → selectable page-family inventory | #34 gates | Continue after #34 within session budget |
| [#36](https://github.com/blackmath88/apertushackathon-uzh/issues/36) | Selected families → reproducible, completeness-aware captures | #35 gates | Continue after #35 within session budget |
| [#37](https://github.com/blackmath88/apertushackathon-uzh/issues/37) | Stable findings with every dated observation retained | #36 | Backlog; separate pickup |
| [#38](https://github.com/blackmath88/apertushackathon-uzh/issues/38) | Recipe evaluation with separate reviewed promotion | #36; align #37 identities | Backlog; separate pickup/budget |

Initial local execution envelope: #34–#36 only. A bounded session may complete fewer; checkpoint the exact remaining work instead of exceeding its deadline or claiming completion. No worker has been dispatched by this plan or issue creation.

## Research incorporated and evidence limits

Owner supplied a prior-art report on 14 October 2026. We retain these decisions rather than treating its entire dependency shortlist as approved:

- Fix current Scout weaknesses before expanding discovery: inherited proxies, DNS preflight versus connection-time enforcement, redirect/failure accounting, pacing, per-host robots, in-memory frontier, URL normalisation semantics, HTML-only request typing, alternate enqueueing and first-two-language pairing.
- Candidate parsers: Protego for saved robots files; Scrapy sitemap handling/tests as reference. Any third-party network helper must remain behind our guarded transport, not bypass it.
- Courlan is frontier/URL prior art, not a mandatory dependency. A small SQLite store may be sufficient; keep existing campaign JSON and review files readable rather than migrating the whole product.
- Trafilatura may be evaluated as a secondary extraction view; do not replace exact-offset evidence without validated mapping and completeness checks.
- Raw bodies plus manifests first. warcio export is optional and outside the critical path unless a concrete interoperability requirement emerges.
- Bitextor helps investigate correspondence. Its corpus cleaning and quality filters must not discard the mismatches, omissions and ambiguous pairs our observatory seeks.
- Learn history patterns from changedetection.io/DefectDojo, but retain repeated observations and never close findings merely because absent from a later report.
- Learn focused-crawl strategy from ACHE/Frontera without adopting their infrastructure.

Upstream five-project implementation/test audit, exact dependency pins, transitive licence/NOTICE audit and live compatibility remain outstanding. The supplied report explicitly did not complete these. Verify at pickup and record inspected code/test paths and exact revisions before adoption. A README feature is not proof that our safety/evidence contract is satisfied.

Research leads: https://github.com/scrapy/protego · https://github.com/scrapy/scrapy · https://github.com/adbar/courlan · https://github.com/adbar/trafilatura · https://github.com/webrecorder/warcio · https://github.com/bitextor/bitextor · https://github.com/dgtlmoon/changedetection.io · https://github.com/DefectDojo/django-DefectDojo · https://github.com/VIDA-NYU/ache

The research's 40-total-attempt / 20-MiB / ten-minute bounds and 70/30 targeted/exploratory allocation are proposals, not measured optima or current app settings. Freeze conservative explicit configuration for a run; retain the existing 20-page/depth-2/minimum-two-second default until deliberately revised within the issue contract.

## Product and data contracts

Maintain distinct organisation/site relationships, discovery snapshots/frontier outcomes, observed hyperlinks, page-family assertions, retrieval/capture records, run inputs, findings, observations and reviews. A directory is not a sitemap; an advertised language link is not a fetched translation; an alignment score is not verified equivalence; an empty result is not proof of quality.

Initial UI success: select an eligible website → preview limits → start discovery → see actual progress and exclusions → select observed page families → save campaign selection → reopen. Next: capture selected families with provenance and completeness. Review findings remain the principal application output, with bilingual context as drill-down.

Every run records its frozen scope/profile/strategy/version and budgets. Count failed requests and redirects, retain known-but-unvisited candidates, and show why collection stopped. Treat English availability as a publication-policy question before declaring omissions. All four languages are represented as families; requested comparison pairs derive from them.

## Local Codex / Orca execution contract

Read LOCAL_CODEX_DISCOVERY_HANDOFF.md and the installed route-orca-work plus orchestrate-work skills. Load Orca's actual orchestration guide using the executable resolved according to that skill. Do not invent flags or call native subagents Orca workers.

Inspect current GitHub/local worktrees, Observatory if present, and applicable instructions. For governed work inspect actual Weavr Project/Mission/Session/Need/Run ownership first; follow blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md. No Mission dispatch, scope widening, Need waiver, merge or deployment is authorised here. If canonical state is unavailable, do only isolated work that cannot conflict with existing ownership.

Default session envelope: 30 minutes total, at most two actual workers, one focused repair per packet, no new paid API spend. Verify enforced timeout/settlement and credential isolation before delegating. Use separate worktrees, exact input commits, scoped write paths and explicit acceptance. Serialise shared files and dependent work. Prefer eligible local/Mistral routes; never contend with Apertus or a running benchmark, including through another service sharing its host/GPU. If availability or isolation is uncertain, skip the route and use eligible foreground/subscription execution. Log observed identities and unavailable usage honestly.

Do not stop/start/reconfigure inference or touch baseline data, scientific branches, frozen outputs, judge entrypoints or held-out test content. No new model downloads. Discovery/capture can be built with authored fixtures and zero inference calls. Do not use another data directory to evade runtime reservations.

Use a fresh isolated discovery worktree based on the current app PR32 head. Reuse an existing owned discovery branch/PR if one appeared after this handoff. Prefer one implementation PR targeting the current application branch, containing coherent dependent commits and linked issues; do not create a new PR per worker. Do not push over concurrent app work or force-update refs.

Public live acceptance is conditional on an eligible reviewed profile, source policy and provenance. Keep existing BFE restrictions. If no site is eligible, deliver the implementation and fixture evidence with a real blocked-live status; do not request broader permission merely to label a stage complete.

## Gates and finish

Run regression tests tied to the repaired behavior and the existing applicable offline gates. Discover full gate commands from the repository; do not blindly run tests that fetch protected data. Exercise desktop/mobile UI for #35/#36 and preserve evidence from authored fixtures. Inspect diffs and combined state before handoff. Independent review must be bounded and source-read-only at an exact commit; otherwise label self-review and keep the independent gate open.

Update each issue with exact commits, observed checks, remaining acceptance items and real status. Do not mark live acceptance complete from mocks. Stop at the session deadline or acceptance completion; retain ownership of possibly-live attempts until settled, checkpoint unfinished work and report the next issue/action. No background monitor is created.

## Planning provenance

Application inspected at 53e775b2778bd006b8791432f04e0579a55e6c3e, PR32; foundation PR12 and research PR33 remain separate. Canonical Weavr contract inspected (blob 86f938b09665402e1a0c4db9742713b310c8e9e2). Plan and issues are preparation, not canonical Weavr state or runtime dispatch. Current app checks previously reported: 28 focused tests and two browser flows; those are not acceptance evidence for the future discovery implementation.
