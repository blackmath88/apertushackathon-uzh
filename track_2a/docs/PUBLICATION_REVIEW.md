# Publication review

First pass on 13 Oct 2026 by the Packet B subagent; second pass the same day by the coordinator, which added the log and Docker inventory and a recommendation. No visibility change, deletion, history rewrite or operative licence is made here. Repo visibility on 13 Oct (`gh repo view`): **PRIVATE**. Not legal advice.

## Inventory

| Material | Licence / status | Source | Status |
|---|---|---|---|
| Labels (SwissGov-RSD) | CC BY 4.0 | HF dataset card, retrieved 13 Oct ("cc-by-4.0"); SOURCES.md cites dataset `LICENSE.md` | Card confirmed; `LICENSE.md` not re-read. SOURCES says the text part has different terms: reconcile. |
| Source text (Swiss federal websites) | © Swiss federal authorities, admin.ch terms of use | SOURCES.md, citing the dataset `LICENSE.md` | **Unresolved:** admin.ch terms not read; redistribution conditions unknown. |
| Apertus v1.5 8B | Apache-2.0, gated | SOURCES.md (HF cards, 7 Oct) | Recorded in repo notes; gated-access terms not re-read. No weights committed. |
| Upstream prompts and evaluator (`ZurichNLP/SwissGov-RSD` @ `1807a42`) | No top-level licence; `rsd/LICENSE` (MIT) covers only `rsd/` | SOURCES.md | Fetched at run time and hash-checked, not vendored. **However, the full prompt text is embedded in committed `raw.jsonl`.** |
| HackApertus template | Apache-2.0 | template README, 13 Oct | Confirmed. |
| Hackathon terms | Code Apache-2.0, docs CC BY 4.0; keep pre-existing third-party material separate | hackapertus.ch/terms-and-conditions, 13 Oct | Confirmed by the first pass. |
| Own code | **No LICENSE file** | repo search, 13 Oct | Gap. The terms expect Apache-2.0 on submission. |
| Own docs / report | The report's licence section is scoped (13 Oct, `662e14d`): our docs CC BY 4.0, code intended Apache-2.0, third-party material keeps its terms | `technical_report.md` §License | Done. Not an operative licence grant for code until a LICENSE file is added. |

## Text-bearing files (inspected 13 Oct)

| Path | Third-party text? | Notes |
|---|---|---|
| `results/<run>/raw.jsonl` (167 KB) | **Yes:** full prompts, containing upstream template text, few-shot examples and the 9 dev source documents (EN + DE/FR/IT), plus Apertus outputs | The only file needed for offline replay |
| `results/<run>/predictions/{b0,b2}/*.jsonl` | **Yes:** `text_a` / `text_b` of each valid document (e.g. `admin_fr_136`, 1.2 k chars) plus our labels | The "model predictions" deliverable |
| `results/<run>/job.log`, `prior_jobs/*.log` | No dataset or model text found (searched for prompt markers, JSON keys, `admin.ch`). The B0/B2 job log has document IDs, token counts and latencies. | Smoke log contains a `SMOKE_TEST_OK` marker; a full manual read was not done |
| `results/<run>/{results.json,results.md,run_meta.json,launch.json,compute.json}` | No; metadata and scores | |
| `diagnostics/<run>/audit_supplement.*` | No; excerpts are referenced by sha256 and token length | Added 13 Oct |
| Docker image (`Dockerfile`) | **Yes:** `COPY results` puts `raw.jsonl` and predictions into the image. `data/`, `runs/`, `tests/`, `docs/` are excluded by `.dockerignore`. | No image has been published. Pushing an image would redistribute the same text. |
| Git history | Same files since `2adaeda` | History rewriting is out of scope. |

## Recommended path (owner decision)

**Ask first, then publish with a third-party notice (option 4 → 1).**

1. Send the consolidated organiser message ([JUDGE_READINESS.md](JUDGE_READINESS.md)). Its question 5 asks whether committed raw outputs containing dev source text and the upstream prompt text are acceptable in the public repository.
2. Meanwhile prepare, without committing to it yet:
   - a `LICENSE` (Apache-2.0) for our code;
   - a `NOTICE` / README section stating that the dataset labels are CC BY 4.0 (ZurichNLP), source texts are © Swiss federal authorities, upstream prompts and evaluator are ZurichNLP material without a stated licence, and none of these is relicensed.
3. If UZH agrees, or does not object before the deadline, make the repository public as the terms require.

Why this path: the hackathon requires open source and model predictions, and predictions in the official format inherently contain the dataset text. The dataset, source texts included, is already publicly distributed on Hugging Face (card: cc-by-4.0, with the text terms still to be reconciled). The open risk is the upstream prompt text (no licence), and the provider can resolve that in one answer.

## Alternatives

- **Publish as is, with the notice.** Fastest. Carries the unconfirmed prompt-text redistribution risk.
- **Publish without text-bearing artefacts.** Keep `raw.jsonl` and predictions private, or replace them with IDs plus hashes. This breaks `make reproduce` and the predictions deliverable, so it is not recommended unless UZH objects.
- **Stay private and grant judges access.** Conflicts with the open-source requirement; only if the organisers explicitly allow it.

## Unresolved permission questions

1. Do the admin.ch terms permit redistributing the dev excerpts, and with what attribution? (not read)
2. May the upstream template text (no licence) appear inside committed `raw.jsonl`? (N-LIC-1; ask UZH)
3. Do the dataset `LICENSE.md` and the HF card agree?
4. Rightsholder name for LICENSE/NOTICE: team name and members are an owner input.
5. Are the Apertus gated-model terms compatible with publishing its outputs? (not re-read)

Sources retrieved 13 Oct: hackapertus.ch/terms-and-conditions; github.com/HackApertus/project-template; huggingface.co/datasets/ZurichNLP/SwissGov-RSD; hackapertus.notion.site (track and submission pages).
