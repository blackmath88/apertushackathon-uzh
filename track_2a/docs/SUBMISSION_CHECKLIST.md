# Submission checklist — Hack Apertus Track 2A, UZH SwissGov-RSD

Rules transcribed from the sources pinned in [SOURCES.md](SOURCES.md) on
2026-10-07. Status reflects S1 only. Later stages fill in the artefact column.

Legend: ✅ verified · 🟡 partial / in progress · ⬜ not started (later stage) · ⛔ blocked

## Event-level requirements

| # | Requirement (source) | Status | Evidence / owner stage |
|---|---|---|---|
| E1 | Submit on hackapertus.ch/online-hack/submissions by **16 Oct 2026 12:00 CEST**, no extension (how-to-submit) | ⬜ | Human, after S6 |
| E2 | Follow the template repo: keep `track_2a/` as-is, delete other tracks (template README) | 🟡 | Layout kept; S6 to confirm |
| E3 | `make run` from the project root on a clean checkout runs the project **in Docker** (template, how-to-submit) | ⬜ | S2 |
| E4 | Use `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` (template README) | 🟡 | `apertus_smoke.py` reads exactly these; S2 for the pipeline |
| E5 | Follow the specified input/output format; run end-to-end when judges run it (how-to-submit) | ⬜ | S2/S5 |
| E6 | `data/` ≤ 100 MB (template) | ✅ | Raw data is ignored, never committed; tracked `data/` holds only `.gitkeep` |
| E7 | Solution built with the Apertus family; other open-weight models only as support, described in the report (Track 2 page) | 🟡 | Only Apertus is configured; no supporting model used in S1 |
| E8 | Open source; CC BY 4.0 per template report, Terms §6 (template) | ⬜ | Owner decision on visibility/licence (repo currently private) |
| E9 | Fill `technical_report.md` sections 1–8 (template) | ⬜ | S6 |
| E10 | No secrets or model weights committed (template `.gitignore`) | ✅ | Credentials only via env; smoke record redacts key, userinfo and query (tested) |

## UZH challenge requirements

| # | Requirement (track-2a-uzh page) | Status | Evidence / owner stage |
|---|---|---|---|
| U1 | Data from HF or GitHub `ZurichNLP/SwissGov-RSD` | ✅ | HF revision `f16aa05…` pinned; dev loader verified (504 records) |
| U2 | **Test set must not enter development in any form** (training, prompt examples, tuning), or disqualification | ✅ (S1) | No test file registered; split guard tested with I/O spies; CLI refuses `--split test` |
| U3 | Primary metric: token-level Spearman per pair, macro over EN–DE/FR/IT; provided evaluation script defines preprocessing and punctuation | ✅ | Parity with pinned `compute_correlations`; macro added as in the brief |
| U4 | Models: Apertus v1.5 8B or 70B | ⛔ | Endpoint access missing (see blockers) |
| U5 | Reproduce a baseline from the SwissGov paper with your Apertus model | ⬜ | S2 (B0 from `template_*_admin.txt`) |
| U6 | Deliverables: code/reproducible implementation, **model predictions**, short method description; optional demo/visualisation and adapters | ⬜ | S2–S6 |
| U7 | Secondary criteria: computational efficiency, innovation/creativity | ⬜ | S2/S3 run records (calls, latency, tokens) |

## Open Needs (unresolved rules)

| ID | Question | Why it matters | Ask |
|---|---|---|---|
| N-RULES-1 | How do judges evaluate on the held-out test? Do teams submit test predictions, or do judges run `make run`? | Determines whether we ever run inference on test, and how | UZH Q&A 8 Oct 12:00, or the Q&A doc |
| N-RULES-2 | Are the 34 `list_to_drop.txt` ids excluded in final scoring for LLM systems? | The official script drops them for LLM prediction files only | UZH Q&A |
| N-RULES-3 | Is `text_*` (whitespace-tokenised) the required input, or may systems read `*_untokenized`? | Prompt construction and offset mapping | UZH Q&A |
| N-RULES-4 | Official prediction file format for submission (encoder-style `{id,text_a,text_b,labels_a,labels_b}` assumed) | Export format in S2 | UZH Q&A |
| N-RULES-5 | Is span/chunk decomposition plus deterministic projection fully valid? (PLAN.md Q1) | B2 validity; the brief lists decomposition/chunking as encouraged, which suggests yes | Confirm at Q&A |
| N-LIC-1 | The SwissGov-RSD repo has no top-level licence | We fetch the evaluator at run time instead of vendoring it | Ask UZH, or keep run-time fetch |
| N-COMPUTE-1 | Approved Apertus endpoint, model id and budget | Live smoke, and every S2+ gate | Owner: CSCS key (distribution closed 6 Oct), HF credits, or own deployment |
