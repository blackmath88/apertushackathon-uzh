# Publication review

Prepared 2026-10-13 by Packet B (read-only research subagent), integrated by the coordinator; no visibility change, deletion or history rewrite is proposed. Repo visibility re-checked 13 Oct via `gh repo view`: PRIVATE. Not legal advice.

## Inventory
| Material | Licence / status | Source | Status |
|---|---|---|---|
| Labels (SwissGov-RSD) | CC BY 4.0 | HF dataset page, retrieved 2026-10-13 ("cc-by-4.0"); SOURCES.md cites dataset `LICENSE.md` | Confirmed (page); `LICENSE.md` itself not re-read. HF page states a single cc-by-4.0, SOURCES says the text part differs: reconcile. |
| Source text (Swiss federal websites) | (c) Swiss federal authorities, admin.ch terms of use | SOURCES.md citing dataset `LICENSE.md` | Unresolved: admin.ch terms not read; redistribution conditions unknown. |
| Apertus v1.5 8B (and 70B, unused) | Apache-2.0, gated | SOURCES.md (HF cards, 2026-10-07) | Confirmed by repo notes; gated-access terms not re-read. Model outputs: no stated restriction found; unresolved. No weights committed. |
| Upstream prompts and evaluator (GitHub ZurichNLP/SwissGov-RSD @1807a42) | No top-level licence; only `rsd/LICENSE` (MIT, (c) 2023 Univ. of Zurich) for `rsd/` | SOURCES.md | Fetched at run time into ignored `data/`, hash-checked, not vendored (per SOURCES.md). Prompt text is embedded in `raw.jsonl` `prompt` fields, which are committed (see below): this is a copy of unlicensed upstream text. Unresolved. |
| HackApertus template | Apache-2.0 | template README, retrieved 2026-10-13 | Confirmed. |
| Own code | No LICENSE file anywhere in repo (searched outside `.venv`) | find, 2026-10-13 | Gap. T&C: code Apache-2.0 on submission (hackapertus.ch/terms-and-conditions, retrieved 2026-10-13). |
| Own docs/report | `technical_report.md` states "Creative Commons Attribution 4.0 (CC-BY-4.0). All HackApertus projects are open-sourced." (line ~171) | repo | T&C: non-code docs CC-BY-4.0 (confirmed). |

## Committed text-bearing artifacts (`track_2a/results/20261012T062327Z-ff965461/`)
- `raw.jsonl`: per call full prompt (incl. upstream template and few-shot examples), dev source tokens of 9 documents, model output. Contains third-party source text, upstream prompt text and Apertus output.
- `predictions/` (b0, b2): tokens/text and labels (labels CC BY 4.0 derivative; text third party).
- `job.log`, `prior_jobs/`, `launch.json`, `compute.json`, `run_meta.json`, `results.*`: logs/metadata; `job.log` and `prior_jobs` may echo model output or prompts (not checked for text). Checklist records a secret scan clean (12 Oct, unverified here).
- `Dockerfile` copies `results/` into the image, so any image distribution also carries these.
- Prior commits on the branch contain the same data; history rewriting is out of scope.

## CC BY wording and ownership
`technical_report.md` ("Creative Commons Attribution 4.0 ... All HackApertus projects") sits repo-wide with no scoping. Read literally it could imply the whole repo, including embedded dev source text (c) Swiss federal authorities and upstream prompts, is CC BY 4.0 from us. Per T&C, one should "keep separate" pre-existing material one will not open-source. Needed: a notice (e.g. NOTICE/README section) that third-party material keeps its own terms, and an explicit per-file scope. Not yet written; owner decision.

## Options (owner decision)
1. Publish as is with an added third-party notice (risk: redistributing admin.ch text and upstream prompts without confirmed permission).
2. Publish code + docs + aggregate scores/metadata, and exclude text-bearing artifacts from the public tree or ship them only as hashes/ids plus the `make reproduce` fetch path. Cached replay then needs the raw file, so this would change what `make reproduce` can do.
3. Keep private, grant read access to judges/organisers only, if the rules allow (unconfirmed; submission rule says open source).
4. Ask UZH/organisers for permission for dev text + prompt redistribution first, then pick 1 or 2.
These options need not delete or rewrite anything; evidence stays on the private branch.

## Unresolved permission questions
1. Does admin.ch terms of use permit redistributing the dev text excerpts, and under what attribution? (not read)
2. May the upstream template text (no licence) be committed inside `raw.jsonl`? Ask UZH (N-LIC-1).
3. Do dataset `LICENSE.md` and the HF card agree (CC BY 4.0 labels, text (c) authorities vs "cc-by-4.0")?
4. Do hackathon rules require open source on submission even where third-party material is restricted? (T&C: keep separate; submitted datasets must state per-item licences.)
5. Are Apertus gated-model terms compatible with publishing outputs? (not re-read)
6. Which repo LICENSE file(s) to add and who is the rightsholder (team name/members open)?
7. Do committed logs contain anything beyond the scanned secrets?

Sources retrieved 2026-10-13: hackapertus.ch/terms-and-conditions; github.com/HackApertus/project-template; huggingface.co/datasets/ZurichNLP/SwissGov-RSD. Notion pages unreadable.
