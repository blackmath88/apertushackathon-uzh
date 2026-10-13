# B5 — Competitive Semantic Alignment report

## Verdict and recommendation

**Overall verdict: NOT SUPPORTED.** A establishes useful finite-budget oracle headroom, but B shows no evidence that the predeclared reciprocal, capacity-constrained NULL, or local affine-gap matchers realize it. Gate B failed, the coordinator ordered a stop, and C was correctly skipped without starting Apertus.

**Submission recommendation:** retain the pinned B4 DiffAlign prediction method. Do not submit A (gold-derived diagnostic), M1–M3 (all worse), or an unmeasured Apertus fusion. Architectural elegance does not outweigh the measured full-sample result.

## Route and ordering

This was supervised Orca run `run_158bac75bf36`, Task `task_6e2fa3b39103`, Dispatch `ctx_9bf06ed898d3`, worker `term_952ae3a7-947f-4d22-95d0-b2d5dade9f23`, coordinator `term_cd63a69b-33ce-4197-bd48-722351837e4a`. The worktree began at exact PR #17 head `25380bf280bf6639c71ebbff0a927ceef6e2fffc` on branch `blackmath88/b5-competitive-semantic-alignment`.

Delivery is draft PR [#19](https://github.com/blackmath88/apertushackathon-uzh/pull/19), stacked only on `blackmath88/b4-alignment-first-sdm`. The complete pre-delivery evidence package is commit `430d777`; the PR head adds only this delivery pointer and its refreshed package checksum.

The required order was enforced. The selector was committed at `dd4141f` before A gold scoring. Gate A reported the exact condition and uncertainty through a blocking coordinator ask; the reply authorized B. The B availability/cost/parameter freeze was committed at `231423a` before the 8.06 GB model download. Gate B was then reported through a second blocking ask; the coordinator ordered "Stop and package," so no C action occurred.

## Experiment A — oracle intervention

The deployable selector sees only fields genuinely present in B4: official tokens and their scalar DiffAlign anomaly scores. It creates clipped five-token windows centred on original-token positions and ranks them by a frozen combination of centre anomaly, regional anomaly, local score discontinuity and digit/URL/repetition cues. It uses no gold, embeddings, matrices, counterpart indices or margins. Candidate identity and positions for every policy and budget were frozen in `selector-manifest.json` (SHA-256 `34c485e68cc5584b91e1597440952f496e6f206eca2ff8a492140932e86cdd39`) before scoring.

Selected-region oracle replacement changes only the positions in the finite selected windows; the unrestricted ceiling replaces every unmasked score and is reported separately.

| Primary budget (groups/doc) | DE | FR | IT | Macro | Delta vs 0.187117 | Reachable positives | Precision | Token coverage |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.212652 | 0.141206 | 0.217003 | 0.190287 | +0.003170 | 4.13% | 38.89% | 0.68% |
| 3 | 0.219300 | 0.150795 | 0.230185 | 0.200093 | +0.012977 | 11.37% | 34.53% | 2.12% |
| **5** | **0.225287** | **0.160384** | **0.242142** | **0.209271** | **+0.022154** | **15.92%** | **29.49%** | **3.47%** |
| 10 | 0.242003 | 0.183644 | 0.264251 | 0.229966 | +0.042849 | 23.93% | 22.15% | 6.94% |

The first passing deployable condition is `suspicious_v1`, budget 5. Its paired document-cluster bootstrap (27 shared-English groups, 500 seeded replicates) gives macro CI95 `[0.162063, 0.268241]` and delta CI95 `[0.008375, 0.036505]`. Leave-one-document delta ranges around the full +0.022154; the largest influence is `admin_de_194` (delta without it +0.028607, influence −0.006452), so the point result is not wholly driven by one document.

Controls show that the oracle opportunity is not unique to the proposed ranking: at budget 5, highest anomaly reaches 0.204353 (+0.017237), the pre-frozen cue-first alternative 0.208819 (+0.021702), and deterministic random regions 0.208212 (+0.021095). This supports correction headroom, not a claim that the primary selector knows which replacement to make. The unrestricted gold-replacement ceiling is exactly 1.000000 and is not in the finite action set.

**Gate A: PASS** at the first primary budget reaching the predeclared +0.020000 criterion.

## Experiment B — same-cache competitive alignment

### Input availability and regeneration cost

B4 and the pinned upstream repository contain published official-token scalar predictions, not embeddings. Exact embeddings, subword maps, similarity matrices, counterpart indices and a pinned original model revision were absent. The upstream README explicitly says embeddings and similarity matrices are not included.

The smallest licensed local route used MIT-licensed upstream code/provenance and Apache-2.0 Qwen weights pinned at revision `5cf2132abc99cad020ac570b19d031efec650f2b`. Before download, the route recorded 8,059,521,975 model bytes, a 17 GiB task ceiling, 354 GiB free disk, 31 GiB RAM, the local Arc Pro B60, no paid/cloud compute and a 120-minute wall ceiling. Actual installation used 7.2 GiB, the verified weights used 7.6 GiB, 341 GiB remained, and all 30 matrices were generated in 11.08 seconds; the cache is 37,873,365 bytes.

All matchers consume the identical regenerated matrices and output one finite score per official token in exact order. M2/M3 emit explicit `-1` NULL counterpart indices. Parameters were frozen before download and never tuned.

| Method | DE | FR | IT | Macro | AP | Ties | Duplicate target reuse | NULL subwords | Positive detection @0.5 | Runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 independent max | 0.220659 | 0.135098 | 0.209144 | **0.188300** | **0.205576** | 2,907 | 2,821 | 0 | 0.84% | 0.30 s |
| M1 reciprocal + margin | 0.203854 | 0.146058 | 0.204966 | 0.184959 | 0.197269 | 0 | 2,821 | 0 | 71.78% | 0.35 s |
| M2 Hungarian + NULL | 0.197623 | 0.146713 | 0.193800 | 0.179379 | 0.122330 | 8,102 | 0 | 10,758 | 67.06% | 4.47 s |
| M3 local affine gap | 0.210034 | 0.145618 | 0.177104 | 0.177585 | 0.122041 | 6,603 | 0 | 6,960 | 51.47% | 33.43 s |

M1 is the best competitive method, but it is −0.002158 below published B4 and −0.024312 below the selected A diagnostic baseline. Its paired cluster-bootstrap delta CI95 is `[−0.018976, 0.014523]` versus B4 and `[−0.051972, 0.000984]` versus A. Capacity/sequence constraints eliminate duplicate reuse but produce many NULLs, ties and much lower AP. They slightly reduce number/date cross-occurrence mismatches (M0/M1: 184; M2: 160 plus 23 NULL; M3: 146 plus 46 NULL across both sides) without improving the benchmark objective.

Failure examples are mixed rather than selectively favourable. M1 improves `admin_fr_58` from per-document 0.036948 to 0.118626 and `admin_it_167` from 0.081890 to 0.130641, but regresses `admin_de_43` from 0.328569 to 0.251934, `admin_it_65` from 0.222851 to 0.170124 and `admin_fr_156` from 0.155089 to 0.103291. M3 falls to 0.006373 on `admin_de_140`, illustrating the cost of a single monotone local path for reordered documents.

Regenerated M0 is internally comparable to M1–M3 but not exactly identical to published B4: mean absolute official-score difference is 0.001527 and maximum 0.130091. The upstream result did not record the original model repository revision, so this package distinguishes successful local execution and internal integration from exact scientific comparability to the published bytes.

**Gate B: FAIL.** No competitive method clears the predeclared +0.005 over both B4 and A; uncertainty gives no support for promotion.

## Experiment C — gated skip

The coordinator explicitly stopped after Gate B. Apertus calls: **0**. Port 11436 remained closed throughout B5. Morrow remained unchanged at PID 1240 on `127.0.0.1:11435`. Therefore C has no measured incremental contribution and no prompt/config was opportunistically tuned after the negative gate.

## Coverage, integrity and protocol disclosure

Both A and B cover all 30 frozen dev documents, all three languages, and every official token with finite values. Gold enters only the separate A diagnostic scoring and B evaluation stages. No official test file or record was downloaded, opened, scored or used.

One broad GitHub tree metadata query during the B availability audit inadvertently printed official-test path names and blob sizes. It did not open content, enumerate record IDs, or download files. This violates the stricter "do not enumerate" wording and is disclosed rather than hidden; subsequent queries and all code were constrained to dev. It does not contaminate predictions, but it is a remaining procedural blemish.

The first model-download request received HTTP 429; the single bounded repair used direct immutable-revision file URLs. The first embedding cache used tokenizer-internal `word_ids`; scoring rejected it before producing results, and the single focused implementation repair rebuilt the mapping from exact character offsets. The rejected cache was never scored. These failures and measured resources are preserved in `resource-evidence.json`.

All B0–B4 tracked artifacts remained byte-for-byte unchanged. Package hashes are in `checksums.sha256`; per-stage raw evidence has its own `checksums.json`. Exact commands are in `README.md`.
