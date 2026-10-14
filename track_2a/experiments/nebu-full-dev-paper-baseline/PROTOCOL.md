# Full-dev B0 paper baseline — frozen protocol

Status: **PREPARED / NO REAL MODEL CALLS**. Freeze date: 2026-10-14 CEST.
The protocol-freeze commit must precede any real request. This package neither
starts port 11436 nor authorizes inference.

## Immutable scope

Run the B0 paper prompting method once on every permitted pair in the pinned
SwissGov-RSD development files, in manifest order. Apply only the pinned
official `list_to_drop.txt` exclusions. Do not select by length, score, prior
success, or model output. Test-set paths, filenames, metadata, and content are
outside scope and must be rejected before I/O.

The implementation base is repository commit
`d6f14191b673925752b97ca06572ee1b626a7848`, based exactly on
`origin/docs/nebu-full-dev-baseline-20261014`. B0 was introduced at `a338d1e`,
the measured pilot ran from `19b6183`, and the current B0 data, evaluator,
prompt, runner, backend, scorer, token, and split files are byte-identical to
that measured base except for a B2-only injectable excerpt-cap change in
`methods.py`. This package's runner is narrowly separated in
`src/uzh_rsd/full_dev_baseline.py`.

## Pinned data and evaluator

- Dataset: `ZurichNLP/SwissGov-RSD` at
  `f16aa0536811b8c0cf975fede21eec5996e4b3c1`; exactly the three explicit
  `data/{de,fr,it}/dev_*.jsonl` blobs recorded in `manifest.json`.
- Evaluator/parser/prompts: `ZurichNLP/SwissGov-RSD` commit
  `1807a42100e742ed03d337c54c4b9ea86995f565`; exact SHA-256 values are in the
  manifest. The official evaluation concatenates documents in input order,
  excludes gold `-1` positions, computes one global Spearman per language, and
  the challenge macro is the mean of the three defined correlations.
- The manifest contains each of the 504 pinned dev rows exactly once as either
  included or officially excluded. `list_to_drop.txt` has 33 unique lines; 15
  occur in these pinned dev files and 18 do not.

The full dev set has already been repeatedly exposed through development work:
the nine-pair B0/B2 pilot, B4/B5/B6/B7 development analyses, and full-dev
structural artifacts. This run creates no holdout. Its score is descriptive,
not an unbiased model-selection estimate. The prior B0 fallback macro 0.268 is
an offset-sensitive pilot diagnostic and is not a target.

## Model, runtime, prompt, and parser

Use only the existing local
`apertus-v1.5-8b-text-q8_0.gguf` (8,567,121,856 bytes, SHA-256
`dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`).
Use the existing `llama-server` binary SHA-256
`d0538ae0a50a97ede6c4fece9054ed8d3b891a82e230a1defe810249ee7b93f1`
from llama.cpp `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. The frozen launch identity is
loopback `http://127.0.0.1:11436`, alias `Apertus-v1.5-8B-Q8_0`, Q8_0, SYCL0,
99 GPU layers, context 8192, parallel 1, flash attention on. Endpoint-advertised
identity must be captured separately at execution; weight and binary hashes are
the attestation of the artifacts, not of an endpoint response.

GGUF metadata independently identifies architecture `apertus`, name
`Apertus v1.5 8b Text`, base repository
`https://huggingface.co/swiss-ai/Apertus-v1.5-8B`, tokenizer model `gpt2`,
pre-tokenizer `tekken`, quantization version 2, and file type 7 (Q8_0). The
embedded `tokenizer.chat_template` is 16,614 bytes with SHA-256
`d23af2850029e9df88bb017e06e0c14a0462604588f1dbe4f519cdfac3e260e0`.
llama.cpp must apply that embedded template to the single user message; no
system message or template override is permitted.

Use the three pinned admin templates, including their three few-shot examples
and 0–5 similarity scale. Render benchmark whitespace-token lists with
`json.dumps(..., ensure_ascii=False)`. Map similarity `s` to difference
`1-s/5`. Decode greedily (`temperature=0`), one request at a time, with exactly
4096 maximum output tokens and no repair or retry.

Parser deviations from upstream are frozen: use `json.loads` then safe
`ast.literal_eval`, never `eval`; non-ASCII token-list rendering is retained;
model `-1` labels map to numeric difference 0; out-of-range or missing labels
use the upstream similarity-5 fallback and are counted. Punctuation labels,
fallbacks, malformed output, and finish reason remain separately visible.

## Length, failure, scoring, and budgets

Before every launch, tokenize each fully rendered prompt with the exact loaded
runtime tokenizer. If prompt tokens + 4096 exceeds context 8192, record
`context_overflow` without sending the request. Never truncate input. The
numeric request timeout is 600 seconds. The total wall ceiling is 115,200
seconds (32 hours) for 489 planned requests. Basis: the BF16 pilot generated
22,945 B0 completion tokens in 732.8 seconds (about 31.3 tokens/s), with
86.3-second median and about 131-second cap-hit calls; 200 seconds/request plus
18% aggregate headroom gives about 32 hours. These are ceilings, not a promise
and never self-extend.

Reserving all 4096 output positions leaves at most 4096 prompt tokens per
request. The dry-run ceilings are therefore 2,002,944 prompt tokens,
2,002,944 completion tokens, and 4,005,888 combined tokens across 489
requests. Any exact-tokenizer context overflow is accounted as a failure, so
these bounds fit the 8192-token context and do not rely on truncation.

Persist and fsync an intent before a request and fsync its raw result/status
immediately afterward. A persisted intent without a result is unresolved and
must never be resent automatically. Resume only never-started entries under
identical manifest/config hashes. A transport/runtime failure checkpoints and
pauses. A returned malformed or length-ended response is preserved without
repair or retry. Every response hash is immutable; overwrite is forbidden.

Primary scoring is all-manifest: parser failures and other missing numeric
vectors receive the explicitly labelled upstream similarity-5/all-zero
difference fallback, while failure status remains unchanged. Report official
per-language and macro Spearman, coverage, and fallbacks together. Secondary
available-only results use only usable vectors and must name denominators.
Constant or otherwise undefined correlations are `undefined`, never coerced to
zero. Exact vector length and official token order are mandatory.

## Privacy and authority

Private inference JSONL, scoring JSONL, rendered prompts, raw responses, and
predictions contain Swiss government dev text or derived text and remain under
ignored local paths. Commit only code, hashes, counts, statuses, and text-free
summaries. No cloud/paid call, download, training, upload, publication, merge,
deployment, submission, Weavr mutation, or Morrow mutation is authorized.

B8 is settled and untouched. Evidence is commit `4cb217650d3b4b45bc56f6d040851ccd346b19d5`:
its owned PID exited, port 11436 closed, Morrow was unchanged, the 234-call
local derivative finished, and the independently reviewed transfer conclusion
is INCONCLUSIVE. No B8 file is copied or modified here.
