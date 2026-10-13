# Predeclared follow-up: B0 vs B2 on a larger dev slice (not run, not authorized)

Status: **draft protocol, 13 Oct 2026.** Nothing here has been launched. Running it needs explicit owner approval of compute (it exceeds the remaining $3.00 ledger ceiling) and an execution route (see the end). It is separate from the frozen pilot `20261012T062327Z-ff965461`, and from any final test-split run (N-RULES-1), which needs its own decision.

## Hypotheses (fixed before any data is seen)

- **H1 (accuracy, primary).** On the same dev documents, B2 (`b2-spans-v1`) achieves a higher official macro Spearman than B0 (paper baseline), scored the way the judges score: every document predicted, an unparseable output counted as all-zero difference (the "paper protocol" view).
- **H2 (robustness).** B2 yields a parseable output for more documents than B0.
- **H3 (cost).** B2 uses fewer completion tokens and less generation time per document than B0.

Decision rule for H1: claim "B2 better" only if the 95 % cluster-bootstrap interval of (B2 − B0) excludes 0. Otherwise report "no demonstrated difference". H2 and H3 are descriptive, with exact counts.

## Selection (dev only, independent of scores and labels)

- **Pool:** dev-split English sources whose three pairs (EN–DE/FR/IT) all exist, none of whose IDs is in `list_to_drop.txt`, with every side 40–400 whitespace tokens. These are the same gold-blind bounds as the pilot. On 13 Oct this gives **88 sources**. The 3 pilot sources (43, 136, 197) are excluded, leaving 85.
- **Order:** sha256(`next-dev-v1|<doc_index>`), the same mechanism as `select_manifest_docs`, with a new rule version string. Take the first **N = 24 sources**, i.e. 72 language pairs. The manifest is generated and committed **before** launch. Its sha256 is recorded in the run metadata.
- **No look at labels or pilot outputs** when choosing N, the bounds or the order. Labels are loaded only by the scorer after inference.
- Limitation, stated up front: the 40–400 token bound excludes long documents, so results do not cover the full length distribution.

## Units and grouping

- **The unit of independence is the English source.** Its three translations share content and are not independent.
- **Primary statistic:** the official per-language Spearman (global over all tokens of that language, punctuation masked), macro-averaged over the three pairs.
- **Uncertainty:** a cluster bootstrap over English sources (2,000 resamples, seed 0). Resample sources, keep all three pairs of each sampled source, recompute macro for both methods and take the difference.
- Report per-language results too. Do not test per language.

## Frozen strategies and budgets

| Item | B0 | B2 |
|---|---|---|
| Prompt | upstream `template_{de,fr,it}_admin.txt` @ `1807a42`, token-list rendering | `b2-spans-v1` (unchanged) |
| Parser | upstream `parse_token_labels`, fallback counted | unchanged locator; **40-token excerpt cap unchanged** |
| Decoding | greedy, `enable_thinking=False` | same |
| Output budget | `max_new_tokens` 4096 (as pilot) | 4096 (as pilot) |
| Model | `swiss-ai/Apertus-v1.5-8B@a411d83` | same |

A larger B0 budget, a JSON repair step, a removed or raised B2 cap, or fuzzy excerpt matching would each be a **separately named variant** (e.g. `B0-8k`, `B2-cap80`), run and reported apart from this comparison. None is part of this protocol.

## Reporting (all predeclared)

- **Coverage per method:** parseable / strictly valid / unparseable by finish reason; B0 fallback tokens out of tokens in parseable documents.
- **B2 accounting** via `make -C track_2a audit`: items complete / partial / unprojected; excerpts exact / normalised / not found / over cap / empty; ambiguous as a subset.
- **Accuracy:** primary paper-protocol macro and the bootstrap interval of the difference. Secondary: matched view (documents both methods parsed) and available view, labelled as such. Number of zero-filled documents per method.
- **Cost:** completion tokens, generation time (total and median), GPU running time, billed upper bound.
- **Provenance:** source commit, bundle hash, manifest hash, prompt hashes, model revision, hardware, library versions. Raw responses are committed unchanged.

## Compute estimate (assumptions stated, upper bounds)

Basis: pilot per-call latency on 1× L40S. B0: median 86 s, cap-hit calls about 131 s. B2: median 15 s, max 26 s. Pilot pairs median about 480 tokens; the pool median is 421.

| Scenario | Calls | Expected generation | Conservative bound |
|---|---|---|---|
| N = 24 (recommended) | 144 (72 × 2) | B0 72 × 86 s ≈ 103 min; B2 72 × 15 s ≈ 18 min; plus about 5 min load ≈ **126 min** | every B0 call 131 s, every B2 call 26 s ≈ 195 min |
| N = 12 (cheaper, wider interval) | 72 | ≈ 66 min | ≈ 100 min |

- **Cost at $0.03/min (`l40sx1`, price checked 12 Oct):** N = 24 ≈ $3.80 expected, ≤ $6.00 bound with timeout 200 min. N = 12 ≈ $2.00 expected, ≤ $3.10 bound.
- Recorded spend so far is at most $0.75 of the $3.00 ledger ceiling. **Either scenario needs the owner to raise the ceiling and authorize the job.** Recheck the HF price before launch.
- One job, `attempts=1`, no automatic retry; same launcher and ledger as the pilot.

## Requirements before launch

1. Owner approval: N, the new spend ceiling and the job timeout.
2. Route: HF Jobs batch, as in the pilot, on the owner's machine with `hf auth login`. A live endpoint would also work; but if it is the CSCS API, its 60 s gateway timeout would cut off B0 on longer documents, which would invalidate the B0 arm. Do not use it for B0 without a longer timeout.
3. Commit the manifest and this protocol (with any edits) **before** the job starts. Any later change is a deviation, recorded with a reason.
4. No test-split access. A final test run for the submission is a different decision (N-RULES-1).
