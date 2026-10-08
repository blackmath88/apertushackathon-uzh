# Apertus Hackathon — UZH SwissGov-RSD

Private working repository for the Hack Apertus 2026 Track 2A UZH challenge.

**Working hypothesis:** structured semantic compilation over aligned spans, followed by deterministic projection to token-level scores, can outperform direct token scoring while improving interpretability, reproducibility, and efficiency.

This repository starts from the official Hack Apertus Track 2A shape and extracts only the reusable semantic-compiler kernel from [blackmath88/accessibility-red-team](https://github.com/blackmath88/accessibility-red-team). The SwissGov-RSD benchmark adapter is built fresh.

## Current phase

Exploration → minimum reproducible B0/B2 experiment.

- No test-set development.
- No UI.
- No generic agent framework.
- Apertus is the semantic model under test.
- Deterministic software owns ingestion, split enforcement, schema validation, projection, evaluation, caching, and experiment metadata.

See [track_2a/docs/PLAN.md](track_2a/docs/PLAN.md).

## Challenge sources

- [Full challenge brief](docs/challenge-source/CHALLENGE.md)
- [Source provenance](docs/challenge-source/source.json)
- [Links and requirements](docs/challenge-source/README.md)
- [Shared knowledge and ideas](https://github.com/blackmath88/hackpertus/blob/main/docs/challenges/UZH.md)

Official requirements and our exploratory ideas are separate. This repository stays private during development; source publication requirements are recorded for a later release decision.
