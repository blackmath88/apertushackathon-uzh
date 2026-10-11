# Submission MVP — 11 October 2026

Owner direction: focus on one UZH MVP, clean up and merge reusable work into main; owner arranges Apertus access. This is the current repository build priority, superseding the broader research/roadmap scope for this submission. It is not a Weavr command or Mission acceptance.

## Deliverable

Reproducible Apertus B0 versus B2 comparison on SwissGov-RSD dev data, with valid predictions, per-language and macro Spearman, failure/coverage counts, calls, latency and reported token usage. Follow the official challenge/template requirements. A negative B2 result is acceptable; invented model results are not.

## Ordered work

1. **Foundation:** reuse PR #11's pinned adapter, manifest, evaluator and smoke check. Keep S1 live readiness explicitly blocked until the owner supplies a working endpoint. Do not redo the plumbing.
2. **B0:** implement the paper baseline using the pinned upstream prompt and document any deviation. Start with one EN–DE pair, then the existing nine-pair manifest (three per language). Produce exact-length vectors and a documented prediction export. Reject invalid output; never silently pad or truncate it. Confirm the judge's expected interface/format before claiming submission compatibility.
3. **B2:** one structured span approach with deterministic token projection, evaluated on exactly the same IDs/model/settings as B0. Record invalid spans, UNKNOWN and failures. Do not hide failed examples or compare only selectively successful runs.
4. **Evaluation:** the nine-pair run is a smoke/comparison pilot, not a full benchmark. Freeze prompts and selection before expanding dev evaluation; reserve untouched dev documents for the final dev comparison where feasible. Report subset, denominators, missing languages and undefined correlations explicitly. Keep test data untouched; resolve final judge procedure separately.
5. **Package:** clean-checkout Docker execution through root `make run`; model credentials supplied via environment; predictions, method/report, dependencies and exact rerun instructions. Record actual measurements and limitations. Keep report incomplete until evidence exists.
6. **Optional:** a small bilingual results viewer from measured dev outputs, only after the required package works.

## Targets (Europe/Zurich)

| Date | Target |
|---|---|
| 11–12 October | First real Apertus pair, then nine-pair B0 |
| 13 October | B0/B2 comparison; select/freeze strategy |
| 14 October | Docker and report; expand dev evaluation as compute permits |
| 15 October | Clean-checkout verification, publication decision and submission buffer |
| 16 October, 12:00 | Deadline recorded in challenge resources; recheck portal |

Compute delays reduce experiment breadth; they do not justify replacing Apertus with another model or claiming an offline heuristic is the submission baseline.

## Deferred

Canton pilot/external data; B2a/B3; ensembles/self-consistency/fine-tuning; 70B exploration; campaign game; additional hackathon tracks; Weavr/Faictory delivery trial. Retain older notes as history, not execution instructions.

## Authority and remaining decisions

The owner explicitly authorized repository cleanup and merge on 11 October. This does not authorize paid inference, visibility changes, portal submission, Mission dispatch, Need waivers or canonical Weavr state changes. No live Weavr read connector was available in this review. Staged contracts are not active state.

Next contributor starts from refreshed main and inspects current branches before editing. Runtime compute access, unresolved submission rules and publication remain explicit dependencies; unit tests alone do not complete S1 runtime readiness or the submission.
