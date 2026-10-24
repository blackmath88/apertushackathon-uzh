# Independent review — Nebu full-dev Apertus B0 baseline

Review date: 2026-10-15 CEST  
Reviewed execution commit: `a5e50e9483f387153769fe8a4f9a7a62edb205fa`  
Reviewed freeze commit: `1384e04642b6be805e9b8baa7560845dda3afb42`  
Finding: **INCOMPLETE — not draft-PR ready as a frozen-protocol result**

This was a read-only review of the frozen package, committed text-free outputs,
and the ignored local execution evidence. It made no model call, accessed no
test split, emitted no source or response text, and did not mutate any frozen,
execution, B8, Morrow, or submission artifact.

## Findings

### F1 — HIGH — execution changed the frozen runner

The freeze checksum pins `src/uzh_rsd/full_dev_baseline.py` to
`7f257fa8b5...`, but the execution commit changes it to `7f325235a3...`.
The execution commit adds the exact-token overflow branch, changes attempt
accounting, and adds interrupted-intent reconciliation. Its test file likewise
changes from the frozen `5519b90c9b...` to `1a41b0af84...`.

These changes are sensible and the added behavior passes its tests, but they
were not part of the pre-inference freeze. The outputs therefore cannot be
claimed as execution of the byte-exact frozen runner. Because the code changes
and results first appear in the same post-inference commit, Git history also
does not independently establish the exact code state at call time.

Required action: label this run as a protocol deviation and create an amended
post-hoc execution contract that hashes the runner actually used. Do not call
it a strictly frozen-protocol run. Any future confirmatory run must freeze the
overflow and reconciliation behavior before the first request.

### F2 — MEDIUM — runtime evidence is not fully hash-anchored

The committed execution checksum file anchors predictions, summary, report,
and the private ledger. It does not anchor `token-preflight.json`,
`prompts.json`, either server-identity capture, the generation/resume
summaries, the Morrow snapshots, or the server logs. Those private files
currently support the runtime and budget narrative, but they can change
without invalidating any committed checksum.

Required action: commit a text-free checksum inventory for every private
runtime-evidence file, plus stable counts/identities needed for review. Do not
commit prompts, raw responses, gold, or source text.

### F3 — MEDIUM — Morrow continuity is not demonstrated

The before snapshot records PID 1240/start tick 8199; the after snapshot and
current read-only check record PID 1224/start tick 11150 on port 11435. The
command line is unchanged and port 11436 is currently closed, which supports
service configuration continuity, but not process continuity. The after
snapshot also lacks an audit-file hash comparable to the before snapshot.
This is consistent with the documented host restart, but it is insufficient
evidence for an unqualified claim that Morrow was “unchanged.”

Required action: state that the host restart replaced the Morrow process, that
the same command/configuration was observed afterward, and that mutation-free
continuity was not independently established. Preserve a comparable after
audit hash in future runs.

### F4 — LOW — package status and usage wording are stale or ambiguous

The package `README.md` still says real inference is “NOT RUN,” and the frozen
protocol header says “PREPARED / NO REAL MODEL CALLS.” The latter can remain
as an immutable historical snapshot, but the package-level README needs a
clear pointer to the executed state. Also, the report's token totals cover the
333 returned requests; the one transport/runtime failure has unavailable
usage. The totals are therefore verified known usage, not a complete bound on
all 334 attempted endpoint calls.

Required action: update only non-frozen narrative documentation to distinguish
freeze-time status from execution-time status and qualify the token totals as
known endpoint-reported usage.

## Checks that passed

- Manifest self-digest recomputes. Its 489 included and 15 excluded unique,
  disjoint identities account for all 504 declared dev rows, in `de,fr,it`
  and original-row order. All 33 official exclusion entries are represented
  as 15 present exclusions plus 18 declared absent IDs.
- All six private inference/scoring files match the manifest hashes. The
  inference loader verifies 489 identities, text hashes, and order; no
  gold-bearing top-level field enters generation. Private files are ignored
  and none is tracked by Git.
- The three pinned official evaluator files and three prompt templates match
  their declared hashes. Prompt storage has 489 unique values and every key is
  the SHA-256 of its value. Reconstructed ledger intents reproduce the pinned
  plan digest and config hash.
- The ledger has exactly 489 unique intents and 489 terminal results with no
  unresolved entry: 333 returned, 155 deterministic context overflows, and
  one transport/runtime failure. All 333 response hashes verify. Returned raw
  attempts, including 89 `finish_reason=length` responses, are preserved; the
  failure was terminally reconciled without a second intent, and resume began
  at the next never-started sequence.
- Exact-token preflight covers all 489 requests and agrees with each intent's
  prompt hash: 155 exceed 8192 when reserving 4096 output positions. The
  all-prompt total is 1,820,256, below the frozen 2,002,944 prompt ceiling.
  Known completion usage is 936,390, known combined usage 1,826,142, and
  generation wall time 28,565.194 seconds, all within the frozen ceilings.
- Endpoint captures match the model hash, model size, llama.cpp binary hash,
  llama.cpp commit, alias, Q8_0 type, 8192 context, one slot, embedded chat
  template hash, port, GPU-layer, device, and flash-attention contract in both
  execution segments.
- Committed predictions contain only identity/status fields and numeric
  vectors—no prompt, response, source, or gold text. Their 489-row order and
  generation/parse counts agree with the ledger and summary.
- A clean offline rescore with the pinned official evaluator reproduces
  `predictions.jsonl`, `summary.json`, and `REPORT.md` byte-for-byte. Reported
  all-manifest macro `0.01021567996488429`, available-only macro
  `0.0875492679378083`, per-language values, and denominators 18/18/23 match.
  Local and official Spearman values agree to the enforced `1e-12` tolerance.
- The full baseline unit suite passes 12/12 using the pinned evaluator
  dependencies, including test-split refusal before I/O, raw-response hash
  verification, lock exclusion, no resend of unresolved intents, pause on
  failure, overflow-without-endpoint-call, and official-evaluator parity.
- B8 settlement commit `4cb217650d3b4b45bc56f6d040851ccd346b19d5`
  exists, and the freeze-to-execution diff touches no B8, Weavr, or Morrow
  file. Port 11436 is closed; Morrow alone listens on 11435 at review time.

## Claim limitations

- This is a repeatedly exposed development set, not a holdout or test result.
  It is descriptive and must not be presented as an unbiased model-selection
  or leaderboard estimate.
- Only 59/489 documents produced parseable vectors and only one was strictly
  valid. The primary all-manifest score substitutes zero-difference vectors
  for 430 documents; it principally characterizes the frozen failure policy,
  not successful paper-format prediction quality. The available-only score is
  conditional on 18 EN-DE, 18 EN-FR, and 23 EN-IT documents.
- “Official” means the pinned official correlation implementation was used on
  these protocol-produced vectors. It does not mean official submission,
  hidden-test evaluation, or endorsement.
- The original pinned dataset blobs were not present in this checkout, so
  their Git/SHA-256 pins could not be rehashed directly. Completeness was
  independently checked against the hash-verified private derivatives,
  manifest identities/order, and pinned official exclusion file.
- Model/binary hashes attest local artifacts and endpoint captures attest
  advertised runtime identity; neither cryptographically proves which process
  generated each individual response.

## Review disposition

Numerical outputs and failure accounting are reproducible from the preserved
ledger and private inputs, and no evidence of source-text publication or gold
leakage was found. The run remains **INCOMPLETE** as a frozen-protocol paper
baseline because F1 invalidates strict freeze compliance and F2/F3 limit the
runtime-settlement claims. The next action is a review-only documentation and
checksum amendment that explicitly records the deviation and claim limits;
no rerun is required to preserve these results as a descriptive, deviated run.
