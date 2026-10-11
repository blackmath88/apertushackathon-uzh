# Track 2A — UZH SwissGov-RSD

Submission workspace for **Lost in Switzerland**: direct Apertus token scoring (B0) versus structured semantic spans with deterministic token projection (B2).

Read [MVP_PLAN.md](docs/MVP_PLAN.md) and [STATUS.md](docs/STATUS.md) first. The older research plan and staged delivery trial are historical context.

```bash
make s1-setup
make s1-fetch s1-validate s1-check
```

The dev adapter and evaluator exist. `make run` is still a synthetic scaffold demonstration; real B0/B2 and Docker packaging remain to build. Apertus access is pending.

Never use test data in development, download all splits, leak labels into prompts, fabricate measurements, or silently repair prediction lengths. Preserve model failures and uncertainty in the reported results.
