# Federal campaign control center

## Start locally

From `track_2a`:

```sh
PYTHONPATH=src python -m uzh_rsd.campaign_center --data runs/campaign-center
```

Open http://127.0.0.1:8766. Create a campaign, or open the clearly labelled authored demonstration.

The application is a local campaign workspace with eight tabs and a federal directory:

- Overview: page-pair counts, review progress, next step and recorded activity.
- Scope: choose websites from the source-backed organisational directory. Selection does not start a crawl.
- Sources: import two corresponding permitted BFE HTML captures with language, URL, capture time, pairing and permission provenance.
- Runs: select imported pairs for a dated sequential batch, or start one bounded local comparison. Capture, scope, detector and runtime revisions are pinned.
- Findings: filter candidate/confirmed/rejected findings and follow provenance links to originals.
- Review: inspect bilingual evidence and save validated decisions back to the campaign.
- Report: download a findings report or the full campaign JSON, including unfinished reviews, run dates and source hashes.
- Patterns: save review-backed search hypotheses; these do not activate themselves or change inference.

Campaigns and review revisions persist in the data directory. Browser drafts remain separate until saved to the campaign. Accepted server reviews repopulate the desk when there is no browser draft. All data is local; export contains captured source text and reviewer identities. Back up the directory for durable retention.

## Inference

Inference is disabled by default. This implementation never starts or reconfigures the model service. After the benchmark is positively settled and the existing local Apertus endpoint is available, the operator may explicitly start the server with:

```sh
PYTHONPATH=src python -m uzh_rsd.campaign_center --data runs/campaign-center \
  --enable-inference --model ACTUAL_MODEL_ID \
  --weight-hash ACTUAL_64_CHARACTER_SHA256 --runtime-revision ACTUAL_REVISION
```

The browser asks before a local comparison. The existing experimental federal detector owns the fixed loopback endpoint, input/output limits, identity check, intent/raw checkpoints and no-retry rule. Campaign state records actual start/completion events; it does not simulate crawler activity or progress percentages.

One process owns the data directory via a file lock. Durable `unsettled-attempt.json` and `active-batch.json` reservations prevents overlapping inference within this store, including after restart. Interrupted runs are explicitly marked interrupted; unknown delivery retains the reservation. Operator reconciliation is deliberately manual: verify the original model request has settled before removing the reservation. Do not use another data directory to bypass it. The workspace cannot observe other applications sharing the GPU; baseline settlement remains an operator prerequisite.

## Reuse from accessibility-red-team

Inspected reference `control-center/src/main.tsx` (blob `eb07b599c65067d47871cabf4517434afe5896ad`), control-center README, runner and campaign architecture note. Reused the interaction structure, not its source code or Cloudflare deployment:

- Portfolio → persistent campaign detail.
- Workflow tabs → Overview / Sources / Runs / Review / Report.
- Run console → recorded campaign activity and explicit attempt status.
- Evidence stays attached to the page pair and its exact capture.
- Operator actions stay separate from model output.

The Python engine and existing exact-evidence validator remain the foundations. This is the federal application branch, not another research PR.

## Acceptance and limits

Verified: seven campaign tests and fourteen existing federal-desk tests; Chromium desktop/mobile flow for campaign creation, review save, report download, reopening, restoring saved reviews after clearing browser drafts, disabled inference, missing session-token refusal, no page errors or horizontal mobile overflow. Screenshots inspected. The mocked comparison test checks one successful attempt, duplicate refusal and retained ownership after uncertain delivery. No real model invocation or live federal crawl was performed. Self-review only, not independent security review or production acceptance.

Run campaign tests with:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p test_campaign_center.py -v
```

The browser acceptance script requires a running server, Playwright and compatible Chromium. It creates an authored demonstration campaign in the chosen test server's data directory, so use a temporary directory:

```sh
node tests/campaign_center_browser.cjs http://127.0.0.1:8766 runs/campaign-browser-check
```

Optional `CHROMIUM_PATH` selects an installed browser.

Not yet connected: automatic Scout discovery/capture, scheduled WATCH, remote workers, multi-user authentication, outreach, campaign import/restore UI, cancellation and retry reconciliation. These are capability gaps, not successful stages. The local server is bound to loopback with Host/Origin/session-token checks and must not be exposed through a public tunnel. Requests are limited to 3 MB; each capture is limited by the existing importer. Existing BFE permission restrictions still apply.

See [Federal discovery and findings](FEDERAL_DISCOVERY_AND_FINDINGS.md) for the sourced initial inventory, full UX, implemented limits and dependency-ordered modules.

Next implementation: connect policy-approved Scout manifests into Sources, showing candidate pairing and capture gaps before comparison. Then add a worker adapter so an authorised campaign can execute remotely while retaining stable campaign/pair/run identities. Public deployment and outreach require separate explicit intent.

## Directory and findings slice · 14 October

Additional verification: seven inventory/campaign tests (34-entry hierarchy, scope validation/persistence, serial batch completion, pinned scope, stop/reservation on uncertain delivery, restart, and review-backed pattern snapshots). Both browser scripts pass on desktop/mobile, including catalogue selection, persisted scope, partial review save, finding status filter, original links, proposal save and report export. 28 focused Python tests total. No real model call, broad crawl or automatic recipe promotion. Coordinator self-review only.
