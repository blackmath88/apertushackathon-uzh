# Final long-input Apertus candidate — frozen protocol

Status at freeze: implementation and synthetic checks complete; no development
or final inference performed under this protocol yet.

## Method

`b2-windowed-v2` preserves the original `b2-spans-v1` prompt, response schema,
parser, 40-token excerpt limit, severity/5 token scores, and greedy decoding.
It adds only bounded presentation and exact mapping:

- split each official `str.split()` token sequence into at most 320-token
  sentence-preferred windows with 32-token overlap;
- align windows bidirectionally. Shared exact numeric, URL/email, capitalized
  entity, and long-token anchors dominate; absent anchors use proportional
  position. Pairings may cross, so reordering is representable. Each A and B
  window participates in at least one pair, so additions/omissions are not
  dropped;
- make one 1,024-new-token request per unique pair, one request in flight,
  temperature 0, with an intent persisted before dispatch and a return persisted
  afterward; never retry;
- reject call failures, `finish_reason=length`, malformed output, invalid items
  or severities, unknown kinds, over-limit excerpts, and every non-empty excerpt
  that cannot be located inside its supplied window;
- map local spans through the stored half-open original-token window ranges and
  merge overlap by maximum score;
- call a document complete only if every planned request is valid and every
  official token was included in a successful request. An explicit empty
  `differences` list is processed zero; unprocessed regions have no prediction.

Static bounds are 50,000 prompt characters and 1,024 generated tokens per
request. Acceptance additionally requires endpoint-reported
`prompt_tokens + 1024 <= 8192`. The final entry point supports an explicit total
wall-clock ceiling checked before each request.

## Frozen development acceptance

The manifest is `acceptance-manifest.json`, generated only from the committed
full-development manifest's IDs, languages, token counts, and text hashes. It
contains two source groups and six documents, balanced 2/2/2 across DE/FR/IT:
the longest complete group and the most asymmetric remaining group among those
at or above median total length. Gold did not participate in selection.

The frozen request plan contains 39 requests: 28 for the three longest documents
and 11 for the asymmetric documents. Development inference receives only the
private `inference/` directory. The separate scoring command receives the
private `scoring/` directory only after predictions have been written.

Acceptance requires 6/6 documents complete, all official tokens processed,
exact finite vectors in `[0,1]`, no rejected response, the measured context
bound, and byte-equivalent offline replay. Official Spearman by language and
macro is mandatory disclosure but is not a promotion threshold; this small,
deliberately difficult sample cannot establish an accuracy improvement.

## Frozen runtime

- model: local `Apertus-v1.5-8B-Q8_0` GGUF, SHA-256
  `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`;
- quantization: Q8_0; upstream BF16 revision
  `a411d838600baf0e3635a3daf66fb7c55fc97bb6` is provenance only;
- server: local llama.cpp revision `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`,
  binary SHA-256 `d0538ae0a50a97ede6c4fece9054ed8d3b891a82e230a1defe810249ee7b93f1`;
- server bounds: context 8,192, parallel 1, SYCL0, flash attention on;
- chat template: model-embedded template used by llama.cpp; temperature 0.

The Apertus server uses loopback port 11436. Morrow owns 11435 and must remain
unchanged. Runtime ownership is rechecked immediately before start and stop.

## Commands

```bash
PYTHONPATH=src python -m uzh_rsd.delivery_acceptance freeze \
  --full-manifest experiments/nebu-full-dev-paper-baseline/manifest.json \
  --out experiments/final-long-input-20261016/acceptance-manifest.json

PYTHONPATH=src python -m uzh_rsd.delivery_acceptance infer \
  --manifest experiments/final-long-input-20261016/acceptance-manifest.json \
  --full-manifest experiments/nebu-full-dev-paper-baseline/manifest.json \
  --private-dir /ABSOLUTE/PRIVATE/nebu-full-dev-b0-v1 \
  --out /ABSOLUTE/PRIVATE/final-long-input-dev-RUN_ID \
  --timeout-s 300 --total-timeout-s 3600

PYTHONPATH=src python -m uzh_rsd.delivery_acceptance score \
  --manifest experiments/final-long-input-20261016/acceptance-manifest.json \
  --run-dir /ABSOLUTE/PRIVATE/final-long-input-dev-RUN_ID \
  --scoring-dir /ABSOLUTE/PRIVATE/nebu-full-dev-b0-v1/scoring \
  --official-dir data/official/swissgov-rsd/1807a42100e742ed03d337c54c4b9ea86995f565
```

Prior B0, B2, C1, verifier, B4/B5, B7, and submitted/frozen artifacts are inputs
for context only and remain byte-for-byte unchanged.
