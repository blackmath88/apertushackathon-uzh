# GitHub Pages demonstration

Implemented 15 October 2026. This is a static companion to the Python application, not a migration of its backend.

## Included

- The same sourced 34-entry federal catalogue and a dedicated control-center visual theme.
- Browser-local case portfolio, per-case scope, review queue, evidence, activity and reports.
- Event-stepped theatre character and explicitly scripted Apertus preview; no runtime connection.
- Migration of the earlier single campaign into the case portfolio, preserving its reviews.
- Existing project-authored DE/FR evidence, exact candidate data, source hashes and fixture provenance.
- Human review history, filters, readable report and JSON evidence export.
- Explicit demonstration labels; no live findings, crawler, model calls, uploads, analytics or shared persistence.

Browser storage is not an immutable audit store. Anyone controlling the browser can edit it. The exported records are demonstration decisions, not server-validated review artifacts. Keep the Python store for real investigations. The site does not load private campaigns, captures, logs, credentials, or SwissGov-RSD data. Its CSP prohibits network connections; only a visitor following the catalogue-source link leaves the site.

## Build and verify

From the repository root (Python standard library and Node only):

```sh
PYTHONPATH=track_2a/src python3 -m unittest discover -s track_2a/tests -p test_pages_build.py
PYTHONPATH=track_2a/src python3 track_2a/scripts/build_pages.py --out _site
node track_2a/tests/pages_demo_test.cjs _site
python3 -m http.server 8080 --directory _site --bind 127.0.0.1
```

The build reads only code, the authored demo generator and the sourced catalogue. Only `_site` is uploaded, never the checkout. Relative assets support a project subpath. Two builds are byte-identical. DOM-contract tests cover scope → authored findings → review → report without a network API. Rendered desktop/mobile browser acceptance remains outstanding. No browser dependency was installed.

## Publish

`.github/workflows/pages.yml` builds and deploys on relevant pushes to `main`. It also supports manual dispatch once GitHub discovers the workflow on the default branch. Official Actions are pinned to commits verified 15 October 2026. Build permission is contents:read; only deployment has pages:write and id-token:write. Checkout does not persist credentials.

Repository owner setup:

1. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. If the `github-pages` environment restricts branches, allow `main`; preserve any required reviewers. The historical feature branch is no longer a deployment source.
3. Open Actions → Federal observatory Pages demo. Rerun the latest failed deployment after enabling Pages, or push a relevant change. Verify the deployment's actual page URL and walkthrough.

The owner requested integration into main on 15 October. Main is now the intended development and deployment branch.

GitHub Free requires a public repository for Pages. GitHub Pro/Team support private source repositories. A private source repository does not by itself make the published site private. Verify the account's actual plan in Settings; it was not observable through this connector. Do not publish the entire research repository merely to expose the authored website without reviewing repository history and publication/licence constraints.

Official references:
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

## Acceptance status

Local offline build, reproducibility, JS syntax and DOM-contract journey passed. Self-review only. The owner made the repository public on 15 October. The previous feature-branch deployment was rejected by github-pages environment branch restrictions; main-only deployment now matches the intended branch. Live deployment acceptance still needs verification. No claim of a live site is made.
