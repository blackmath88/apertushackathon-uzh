# Try the federal discovery workflow locally

This walkthrough uses four project-authored language versions. No government website is requested, and no model endpoint is called. The French example has a 20-day deadline while the other examples have 30 days. This is invented demonstration content, not a measured government discrepancy or benchmark result.

From the repository root on the PR #39 application branch:

```sh
PYTHONPATH=track_2a/src python -m uzh_rsd.campaign_center \
  --data track_2a/runs/offline-discovery-demo \
  --demo-discovery
```

Open **http://127.0.0.1:8766**. Use `--port 8767` if that port is occupied. Stop with Ctrl+C. No browser/dependency installation is part of this command.

## Discovery and capture

1. Open **Discovery walkthrough · authored example**, created on first launch.
2. Open **Scope**. BFE is already selected as the demonstration profile. The wider federal directory remains an incomplete inventory; this demo does not enable other adapters.
3. Under **Page discovery**, choose BFE, preview the bounds and explicitly start discovery.
4. Inspect the four-language family. Advertised language URLs can be known without having been fetched.
5. Select the family and **Save page-family scope**. Capture preparation refreshes immediately.
6. Choose DE and FR. Enter your name, a pairing rationale such as “Authored reciprocal language links”, and “Project-authored demonstration” as the rights basis. Certify the pairing, then **Capture fixture evidence**.
7. Download the captured HTML. The download hash must match its filename; fixture URLs are identifiers, not links to claimed government evidence.
8. Choose **View saved sources** or **Continue to comparisons**. These captures are ready, but no comparison has run. Inference stays disabled in this walkthrough.

## Review and report

For the existing fully authored findings/review example, return to **All campaigns → Open demonstration**. Use Findings, Review and Report to inspect evidence, save a decision and export it. That demonstration contains authored candidate output; it does not pretend a model was run on the newly captured family.

Both routes are labelled. The discovery demo is deliberately not a fake end-to-end Apertus result.

## Persistence and separation

Reopening the same demo data directory preserves its campaigns, discoveries and evidence. Discovery runs and snapshots carry `fixture: true`; the UI and report label them authored. The demo refuses a data directory containing non-fixture captures or unlabelled/non-demo discovery runs, and it cannot be combined with `--enable-inference`.

Unknown URLs return a fixture 404. The fixed fixture fetcher has no network fallback. Do not use this mode to assess real coverage, translation accuracy or model performance.

## Verification / limits

The normal CLI was launched on loopback and its HTTP state confirmed the initial campaign, demo mode and disabled inference. Automated tests cover four-language discovery, saved selection, capture and exact evidence download with external socket creation refused. Existing HTTP tests additionally exercise the actual API routes and security checks.

Rendered desktop/mobile interaction remains pending in an environment with an existing approved Chromium. No browser installation was attempted in this follow-up. Run the existing `tests/campaign_capture_browser.cjs` fixture check separately; it is not proof that every new walkthrough interaction renders correctly.
