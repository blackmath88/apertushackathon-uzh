# B2 projection-cap evidence

Scientific question: does the frozen B2 method lose useful evidence because its
strict excerpt projector rejects generated excerpts longer than 40 whitespace
tokens? P0 is the existing 40-token projector. P1 changes only the predeclared
cap to 160 tokens; matching remains exact-first, then case/quote-normalised, and
all real occurrences of an ambiguous excerpt are retained and counted. P2 was
not run: neither the frozen prompt nor saved responses contain offsets, so no
offset can be validated without manufacturing information.

## Results

All correlations are token-level Spearman on the dev split. The local table is
the 17/30 parseable documents (DE 8, FR 5, IT 4); P0 and P1 use the identical
documents, raw responses, decisions, parser, and scoring. It is not a claim
about the frozen BF16/HF configuration.

| Run / projection | EN-DE | EN-FR | EN-IT | Macro | matched excerpts | unmatched | ambiguous | coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| frozen replay P0 (40) | 0.354985 | 0.074941 | 0.095206 | 0.175044 | 62 | 18 | 1 | 9/9 |
| frozen replay P1 (160) | 0.332990 | 0.130489 | 0.112702 | 0.192060 | 76 | 4 | 1 | 9/9 |
| frozen replay P2 | — | — | — | — | — | — | — | infeasible |
| local Q8 P0 (40) | 0.174778 | 0.160441 | 0.232632 | 0.189283 | 103 | 34 | 0 | 17/30 |
| local Q8 P1 (160) | 0.135377 | 0.115968 | 0.289035 | 0.180127 | 131 | 6 | 0 | 17/30 |
| local Q8 P2 | — | — | — | — | — | — | — | infeasible |

P1 recovered 14 exact excerpts in the frozen replay. In the local Q8 run it
recovered 28 exact excerpts; four other formerly over-cap excerpts still failed
strict matching. P1 improved frozen-replay macro by 0.017016 but reduced local
Q8 macro by 0.009157. Thus the 40-token cap demonstrably discards matchable
evidence, but retaining that evidence does not consistently improve accuracy.
Projection recovery is not evidence of better semantic reasoning.

The local run made 30/30 calls with no transport failure, but 12 responses hit
the frozen 1,024-token completion cap and only 17 responses were parseable.
There were 39,210 prompt tokens, 19,995 completion tokens, 680.789 s aggregate
latency, 24.361 s median latency, and 29.370 completion tokens/s. Cost was $0.
Among parseable local responses, one item had invalid severity and two had an
unknown kind; P0/P1 never repaired these semantic/format decisions.

## Concrete local cases

- Improvement: `admin_fr_156`, per-document Spearman -0.226179 → 0.240364.
  P1 projects long exact passages rejected by P0; failure/source attribution is
  projection for the changed vectors, while the structured semantic decisions
  themselves are unchanged.
- Regression: `admin_fr_105`, -0.126117 → -0.499409. The newly retained long
  exact passage is a valid projection of the model output but correlates worse
  with gold, so “more projected evidence” is not automatically useful evidence.
- Unchanged failure: `admin_de_105`, -0.650330 under both variants. Its failure
  is not caused by the projection cap; the unchanged structured model decision
  and downstream scoring dominate.

Bounded source passages, the complete structured decision, before/after
diagnostics, and exact per-document scores for these cases are in
`local-q8-20261013/analysis-final/analysis.json`. The equivalent frozen-replay
cases are `admin_fr_136` (improvement), `admin_fr_197` (regression), and
`admin_fr_43` (unchanged failure).

## Reproduction

```sh
make -C track_2a s1-fetch
PYTHONPATH=track_2a/src python3 -m unittest track_2a.tests.test_mvp_methods -v
PYTHONPATH=track_2a/src python3 -m uzh_rsd.projection_experiment analyse \
  --raw track_2a/results/20261012T062327Z-ff965461/raw.jsonl \
  --manifest track_2a/manifests/s1-dev.json \
  --out /tmp/b2-replay --label frozen-pilot-replay
```

The committed manifest was generated before inference with:

```sh
PYTHONPATH=track_2a/src python3 -m uzh_rsd.projection_experiment manifest \
  --out track_2a/experiments/b2-projection-evidence/manifest.json
```

For the one-time local inference, start llama.cpp commit `7ab4ee7` with the
verified GGUF and `--host 127.0.0.1 --port 11436 --ctx-size 8192 --parallel 1
--n-gpu-layers 99 --device SYCL0 --flash-attn on --no-ui`, then run:

```sh
LLM_NAME=apertus-v1.5-8b-text-q8_0 \
LLM_BASE_URL=http://127.0.0.1:11436/v1 LLM_API_KEY=local \
PYTHONPATH=track_2a/src python3 -m uzh_rsd.cli infer --methods b2 \
  --manifest track_2a/experiments/b2-projection-evidence/manifest.json \
  --runs-dir track_2a/experiments/b2-projection-evidence \
  --run-id local-q8-20261013
```

Stop only that server process, verify no listener remains on 11436, and confirm
the pre-existing Morrow listener remains on 11435. The raw run is immutable;
offline P0/P1 replay is reproducible into a new output directory.

## Controls and limitations

- The sample was fixed in commit `17a8922` before local inference: 10 documents
  per language, source-length quotas 4/3/3 (short/medium/long), with deterministic
  round-robin over declared gold-derived burden/type. Gold never entered prompts.
- The official test split was neither enumerated nor read. No HF final job,
  fallback model, cloud inference, paid compute, prompt tuning, retry, fuzzy
  matching, JSON repair, or offset invention occurred.
- Q8 GGUF is a distinct local configuration and is not numerically equivalent
  to the frozen BF16/HF pilot. High local truncation/parse failure means the
  broader local estimate has substantial selection/coverage limitations.
- Frozen pilot artifacts remained byte-identical; all new outputs live here.

