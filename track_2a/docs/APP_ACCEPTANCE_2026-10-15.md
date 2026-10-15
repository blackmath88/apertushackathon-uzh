# Federal application acceptance — 15 October 2026

Base: PR #39 at `d25331ce93d95c7b58836506e21daf7643179e2b`, targeting the existing federal application branch. This is an additive acceptance/repair slice, not a merge or deployment.

## User-visible outcome

A captured family now has downloadable historical HTML, separate from its live-original links. The download resolves a campaign-owned pair, verifies its content hash and is served as an attachment with `nosniff` and a sandbox policy; captured HTML is never executed inside the application origin. Existing imports without persisted raw evidence do not advertise a download.

After capture, the UI explains that comparison has not run and offers **View saved sources** and **Continue to comparisons**. Sources has the evidence downloads too. The overview includes discovery/capture, and outdated “discovery not connected” wording is removed. Saving one snapshot's family selection preserves other snapshots' saved selections and refreshes capture preparation. Action buttons refuse duplicate clicks while awaiting a response.

Reports retain discovery stop reasons and unvisited counts, capture failures, individual retrieval timestamps and final URLs, family/snapshot identity, and omission blockers. A failed or unexecuted comparison is not presented as a fix.

## Repairs

- Capture and one-shot Scout stores have explicit context-managed SQLite ownership, including exception/interruption exits. Test stores are closed too; failed TLS handshakes close their socket.
- Capture bundles retain each side's retrieval time and final URL. Successfully retrieved raw HTML remains stored even if the counterpart or extraction fails.
- Fixture capture cannot silently fall back to a real network transport. Campaign capacity is checked before capture requests.
- Guarded transport counts consumed body bytes on failures, limits reads to the remaining aggregate allowance, checks deadlines after pacing/DNS and during/after reads, and bounds socket timeout by remaining time. An exact aggregate-byte boundary is conservatively refused because EOF was not established.
- HTTP header names are handled case-insensitively. Truncated compressed streams and trailing compressed members are refused rather than accepted as complete evidence.
- Inventory collection enforces its candidate ceiling (including excluded records), records `candidate_budget` and preserves already collected candidates. Relative links resolve against the final response URL. Non-success feed responses are not treated as inventories.
- XML DTD/entity checks cover the entire bounded body, including UTF-16/32 null-byte representation; unknown sitemap roots are refused.

## Verification performed

In an isolated partial checkout containing the application modules and authored fixtures, using Python 3.12:

```sh
PYTHONPATH=track_2a/src python -W error::ResourceWarning -m unittest discover -s track_2a/tests -p 'test_*.py'
node track_2a/tests/campaign_report_test.cjs
node --check track_2a/tests/campaign_capture_browser.cjs
```

- **92 Python tests passed, zero skips** (78 pre-existing focused tests plus 14 added tests). This is not the full repository/benchmark suite.
- Real loopback HTTP handler exercised: create campaign → fixture discovery → snapshot → saved family → uncertified refusal → certified capture → preparation reload → byte-identical evidence download. Disabled inference and session-token refusal checked. Foreign-pair downloads, traversal, symlinked evidence and hash tampering refused.
- The actual JavaScript report function passed a Node contract smoke test, including failures, unknown/unexecuted status and individual source provenance. Extracted application JavaScript and the browser script pass syntax checks.
- Explicit closed-connection assertions cover capture success, failed counterpart and interruption. Python 3.13-specific warning behavior was not re-run here.
- All web content and model outputs used by tests are authored fixtures. No live government request, real model call or protected benchmark data access occurred.

## Browser gate and local command

The extended Playwright check covers capture, reload, hash-matching download, next-step navigation and disabled inference on desktop/mobile. It was **not executed in this environment**: Playwright's package is present, Chromium is absent, and automatic approval review rejected an attempted browser download because retained instructions prohibited dependency downloads. No workaround or alternate download was attempted. Syntax checks and HTTP tests are not substitutes for rendered interaction evidence.

Run where an approved Chromium already exists (no install step):

```sh
# Terminal 1, from the repository root
PYTHONPATH=track_2a/src python track_2a/tests/campaign_capture_fixture_server.py 8767
# Terminal 2: CHROMIUM_PATH should point to an existing executable, if not Playwright-managed.
node track_2a/tests/campaign_capture_browser.cjs http://127.0.0.1:8767 /tmp/lis-capture-acceptance
```

## Remaining gates / next bounded work

1. Run and inspect the browser fixture on desktop/mobile at the final pushed commit. Do not call this acceptance complete based on syntax checks.
2. Obtain independent read-only review of the final commit; this pass is coordinator self-review only.
3. Run combined application/repository gates in a complete approved checkout. The historical full-suite counts in the earlier ledger were reported by the prior run and are not reasserted here.
4. Before enabling any live discovery/capture, review an eligible source profile and wire robots policy checks for every redirected content target. The direct capture helper does not yet fetch/evaluate robots itself, and the injected legacy-fetcher adapter cannot enforce internally followed redirects. These are reasons to keep the current campaign live gate closed, not reasons to loosen it.
5. DNS/connect/read deadlines are application checks plus socket timeouts, not process-level hard cancellation. Inventory discovery persists its completed snapshot/attempt ledger, but does not resume a durable candidate queue like `government_scout.scout()`; crash recovery must not be described as automatic continuation.
6. BFE remains restricted; no other federal capture adapter was approved. Broad federal coverage, cross-run finding identity (#37) and recipe evaluation (#38) remain separate work.

## Execution and governance

Direct foreground coordinator work in ChatGPT's isolated runtime. Orca is unavailable here; no Orca workers or other agents were launched or claimed. The Weavr operating contract was consulted; no Mission/Need, staged intake, baseline, inference runtime, merge or deployment state was changed. No new application dependency or upstream code was adopted. This update stays in draft PR #39.

## Follow-up: redirect policy and a launchable offline walkthrough

The next repair pass closes the implementation gaps in item 4 above: a shared `RobotsPolicy` checks each guarded content hop before reservation/dispatch; Scout and discovery persist denied decisions as blocked; direct non-fixture capture loads per-host robots and prechecks both sides before content retrieval. Robots fetch failures deny content, and a robots redirect cannot supply another host's rules. Captures using legacy injected fetchers are fixture-only because those callbacks cannot enforce internal redirect hops before dispatch. Source/content-use permission remains a separate prerequisite, and the campaign live gate is unchanged.

New `--demo-discovery` mode exercises the normal app with fixed authored DE/FR/IT/EN responses and no network fallback. It creates an initial campaign, labels its runs/snapshots as fixtures, prevents mixing in existing non-demo discovery, and refuses simultaneous inference. See [OFFLINE_DISCOVERY_WALKTHROUGH.md](OFFLINE_DISCOVERY_WALKTHROUGH.md). Discovery starts are serialised across campaigns, and capture waits until active discovery finishes.

Follow-up verification: 105 focused Python tests pass, zero skips, including nine guarded robots/redirect tests and four offline-demo tests. Normal app CLI/loopback state smoke check passes; report-export smoke and JavaScript syntax checks pass. All upstream responses are authored. Full repository gates, real browser rendering, independent review, eligible live source policy and real Apertus acceptance remain open. The prior browser-download rejection was not retried.

The attached Hack Apertus resource notes were read as background: benchmark measurement and application workflow remain separate, deterministic code owns discovery/policy/provenance, and no benchmark claim or held-out-data access was introduced. Their early-stage checklist is not substituted for current repository status.
