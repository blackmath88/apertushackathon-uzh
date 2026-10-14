# Federal discovery → campaigns → findings → better searches

Decision record and implementation handoff · 14 October 2026

## Product direction

Lost in Switzerland is a federal multilingual quality observatory. Users start with an organisational map, choose an audit scope, run dated investigations, and receive findings with evidence and original links. The bilingual reader is an evidence drill-down, not the primary product. Benchmark experiments remain a separate scientific workstream.

## End-to-end experience

1. **Explore the federal directory.** Browse seven departments plus the Federal Chancellery; expand offices, filter by name/domain, and see what is listed, discovered, captured and analysed. Show the catalogue's source, date and incomplete coverage. Organisation, website and page are separate entities: one organisation can operate many sites; a cross-government portal can serve many organisations.
2. **Select scope.** Pick offices or websites into a campaign, e.g. DETEC → energy/environment, or Finance → taxes/customs. Selecting a department must state whether it selects only indexed children. Save the exact selection; do not silently expand it when the catalogue changes.
3. **Discover pages.** Preview a bounded discovery job, respecting site policy, exact host scope, rate and page budgets. Record a dated discovery snapshot: URLs, parent links, titles, language observations, language-family evidence, hashes, failures and exclusions. Present a searchable tree/table with unknown and unvisited states. A homepage index is not a complete sitemap. Language-switcher links and reciprocal hreflang are evidence of relationships; similar titles alone are insufficient.
4. **Prepare a batch.** Choose discovered page families, language pairs and an investigation recipe. Preview eligible captures, exclusions, request ceiling, detector version and runtime availability. Keep discovery separate from model work. Missing language versions are coverage observations until publication expectations and page correspondence have been established.
5. **Run.** Persist a dated run manifest before execution, pinning scope, discovery/capture identities, recipe, prompt/model/runtime versions and budgets. Progress shows actual queued/running/completed/blocked work. Requests are sequential initially; uncertainty stops the batch and reserves the runtime. Never overwrite or automatically retry a run.
6. **Read the report.** Start with coverage and exclusions, followed by confirmed findings, unresolved suggestions and rejected suggestions. Each finding has an ID, organisation, affected URLs/languages, explanation, exact evidence, source capture times/hashes, originating run/method and human decision. Links lead to live originals; the captured evidence explains what was observed then. Empty results are not a certificate of equivalence.
7. **Inspect and decide.** Open a finding to read its excerpts or full bilingual context. Confirm, reject or leave unresolved, with reviewer and rationale. Omission claims require checking the full relevant sources. Model confidence, exact evidence location and human acceptance are distinct.
8. **Compare over time.** A later run creates new observations. Suggest recurrence links using page-family identity and semantic category; require confirmation when the match is uncertain. Display new / recurring / changed / verified fixed / not rechecked. Disappearance from a crawl or a failed model attempt never means fixed.
9. **Improve the next investigation.** Confirmed findings suggest useful targets; false positives suggest exclusions or a better detector. Save a versioned hypothesis with supporting positive and negative examples. Evaluate it on separate development examples with a fixed comparison and budget before activation. Preserve old recipes and results. Never feed benchmark test data into this loop.

## Initial official-source inventory

The executable seed catalogue is `src/uzh_rsd/federal_inventory.py`: **34 website entries, eight top-level branches and 26 selected units**. Entries include exact domains, parent IDs, an official classification source, index date, and explicit `listed_not_crawled` status. The first scope is executive administration. Parliament, courts, independent organisations, cross-government portals, overseas representations and the rest of the offices are not yet comprehensively indexed. No current office-holder names are needed.

Sources inspected on 14 October 2026:

- https://www.admin.ch/en/federal-administration — seven departments and the Chancellery; executive scope.
- https://www.admin.ch/en/federal-administration-departements — department identities and official links.
- https://www.stelle.admin.ch/en/organization-federal-administration — office/department associations and domains used in this seed inventory. A selected directory, not proof that every office appears or every linked site is reachable.
- https://www.admin.ch/en — explicitly says the English website contains a selection of information. Therefore missing English content must not automatically be labelled a translation mistake.

The domain root is an inventory identity, not a verified capture seed. Catalogue membership grants neither crawling permission nor evidence that language versions exist. Do not substitute old organisation charts for current evidence. Track future reorganisations as new catalogue revisions with source provenance; retain historical run scope.

## Delivered in this slice

- A federal directory with hierarchical browsing, search, website links, site selection and persistent campaign scope.
- 34 source-backed initial entries; no broad live crawl.
- Dated sequential comparison batches over explicitly selected, already imported BFE page pairs. Run records pin capture digests, scope version, detector and runtime configuration. The global per-store reservation prevents competing local batches. Failure stops the remaining queue; an uncertain request or process restart keeps the reservation for explicit reconciliation.
- Findings register and finding-oriented reports with human review state, evidence excerpts, original links, capture dates, HTML hashes, bundle IDs and run/method provenance. Source evidence remains available in the existing reading desk.
- Saved version-1 search hypotheses with immutable copies of confirmed/rejected review examples. These are explicitly not evaluated or activated and do not modify inference. Demo examples stay labelled synthetic.
- Old campaigns remain readable. New scope/batch/pattern fields are optional. Existing review and capture schemas stay unchanged.

## Next bounded modules, in dependency order

| Module | Deliverable | Acceptance evidence |
|---|---|---|
| D1 · Registry enrichment | Versioned organisation/site graph, ownership/attachment distinction, additional official directories, redirects and stale-source flags | Official-source samples; no inferred parent treated as verified; catalogue update does not expand historical campaigns |
| D2 · Discovery snapshots | Connect a selected site to the existing Scout through reviewed host/policy profiles; save queued/visited/excluded pages and link edges; show observed language families | Synthetic HTTP fixtures for robots failure, redirects, off-host URLs, pagination/sitemap budgets and uncertain pairing; one authorised bounded live run when eligible |
| D3 · Capture preparation | Capture selected families with exact snapshots, permission/provenance and completeness checks; register additional federal profiles instead of relaxing BFE's allowlist | Hash/offset reproducibility; language/version correspondence review; unsupported or forbidden site remains blocked |
| D4 · Investigation recipes | Page-family/language selection; bounded targeted queries and compare modes; dated manifests with input/output and costs | Same frozen inputs reproduce selections; queue stops on uncertain delivery; no overlap with an active benchmark |
| D5 · Longitudinal findings | Persistent finding identity separate from observation/run identity; recurrence proposals and verified-fixed decisions | Known renamed/changed/missing pages; failed or omitted scans never auto-resolve findings; ambiguous matches visible |
| D6 · Evaluate and evolve | Recipe proposal → isolated evaluation → reviewed promotion → new version; retain negatives and broad coverage sample | Compare confirmed yield, rejection rate, review effort, coverage and calls/time against prior recipe; protected benchmark test excluded |

Prioritise D2, then D3. D2 should initially discover metadata and relationships only, with no implicit model calls. The recorded BFE collection restriction still applies; do not bypass it through a new profile. No permission to crawl a whole department follows from selecting it in the UI.

## Important implementation limits

Current catalogue organisation→site mapping is deliberately simple and not the final many-to-many graph. Language availability is unknown until observed. The existing import/detector adapter remains BFE-only; other selected domains are planning scope. Automated discovery, automatic repeat scheduling, cross-run deduplication/resolution, and recipe evaluation/promotion are not connected yet. The UI explicitly says so. A batch is a bounded group of existing captures, not a scan of all selected websites.

Each captured pair gets one model attempt. A later investigation needs a fresh capture record; it must not reset completed records. Per-pair attempts and batch records are dated; this is not yet a full event-sourced database. Review revisions are saved separately; current campaign reports show latest decisions. Standalone text export is a report; campaign JSON also includes private captured source text.

The local server uses one process/store ownership lock. Separate data directories do not share an inference lock, and no GPU/baseline scheduler is implemented. Enable inference only when its owner has established runtime availability. No baseline inference, paid compute, deployment or main merge was performed during this slice.

## Verification / resumable handoff

Tests use authored fixtures and mocked model transport, not benchmark samples or government discrepancies. Run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_federal_inventory_campaign.py'
PYTHONPATH=src python -m unittest discover -s tests -p 'test_campaign_center.py'
PYTHONPATH=src python -m unittest discover -s tests -p 'test_federal_desk.py'
# With a locally running campaign server and Playwright/Chromium:
node tests/federal_directory_browser.cjs http://127.0.0.1:8766 /tmp/directory-check
node tests/campaign_center_browser.cjs http://127.0.0.1:8766 /tmp/campaign-check
```

Before starting D2, inspect current PR32 and project state again, preserve existing work, review Scout's transport/policy behaviour, and check runtime settlement. Self-review is not independent acceptance. Full combined repository gates, independent review and live federal/model acceptance remain open.

### Task ledger entry

- Input: PR32 `a46ea23f4b574f4d165add100310aa050757f1fa`; current branch checked before edits and before push. Root and track-level AGENTS.md absent at that revision. Existing Weavr conversational contract inspected; no Mission dispatch or governed state changed.
- Scope: inventory + campaign scope/batches/findings/proposals + focused tests/docs; same application PR. The external accessibility-red-team repository was not modified.
- Source discovery: official directory read through public search, organisation structure cross-checked against admin.ch. Indexed metadata only, not a live scan of the 34 sites.
- Evidence: 28 focused Python tests pass. Both Chromium browser scripts pass, including desktop/mobile overflow and JavaScript-error checks. Screenshots inspected. One partial-review UX bug found and corrected; regression script made independent of portfolio ordering.
- Runtime: direct coordinator implementation; authored fixtures, mocked model transport, temporary local UI server. No actual Apertus request, protected benchmark data, deployment, merge, or active background worker. Self-review only.
- Remaining: D2 discovery-to-capture connection and broader site adapters; full combined gates, independent review and live acceptance. Plans do not imply these are implemented or scheduled.
