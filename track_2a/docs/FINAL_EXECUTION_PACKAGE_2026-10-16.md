# Final execution package — 16 October 2026

## Delivery decision

The frozen delivery method is **unchanged B2/C0** (`b2-spans-v1`) at method
code commit `e51a58cbb511eb9058f0235657e9cec61eb3cda4`. C1 is not selected: its
validation macro was below saved B0 and its confidence interval crossed zero.
The paired-evidence verifier is rejected: it reduced macro Spearman, precision
and recall. B7 S2 remains a stronger measured structural comparator, but it is
not a clean Apertus submission path and depends on an external Qwen embedding
cache. No fallback, JSON repair, chunking or zero-filled submission output has
been introduced.

This is the strongest implemented Apertus path, **not a complete candidate**.
The prior 168-document test execution parsed only 88 responses and correctly
produced no prediction files. A repeat of the unchanged method is expected to
retain that risk. Gate A and the separate final-test owner gate remain closed.

## Frozen method

| Component | Value |
|---|---|
| Model | `swiss-ai/Apertus-v1.5-8B`; historical exact revision `a411d838600baf0e3635a3daf66fb7c55fc97bb6` |
| Local weight option | Q8_0 GGUF, 8,567,121,856 bytes, SHA-256 `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d` |
| Local runtime | llama.cpp `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`, binary SHA-256 `d0538ae0a50a97ede6c4fece9054ed8d3b891a82e230a1defe810249ee7b93f1` |
| Local bounds | 8,192 context tokens, one slot/request, greedy temperature 0 |
| Prompt | `B2_PROMPT_VERSION=b2-spans-v1`; `prompts.py` SHA-256 `1ee3ef70a8a2ea2bf767e5c4c35f7f8f1bfa6765a3d69725f9a246fc2809d74b` |
| Parser/projection | `parse_b2`; exact then case/quote-normalised contiguous location; 40-token excerpt cap; max severity; difference = severity/5 |
| Output bound | 1,024 new tokens |
| Failure policy | one attempt, no retries; call failure or unparseable response makes the run incomplete; no prediction files and no silent fill |
| Output | one JSONL per DE/FR/IT, records in contract order, exact `{id,text_a,text_b,labels_a,labels_b}` fields |

`python -m uzh_rsd.final --verify RUN_DIR` now checks committed status, exact
file set, record counts and order, SHA-256 hashes, exact record schema, vector
lengths against the carried official-token text, finite [0,1] values, and the
complete input ID set.

## Owner-gated final command

Do not execute this until the owner explicitly opens the final-test gate and
supplies an authorised, gold-free input plus a confirmed or explicitly
owner-approved provisional contract. The unresolved template is intentionally
refused.

```bash
export LLM_NAME=Apertus-v1.5-8B-Q8_0
export LLM_BASE_URL=http://127.0.0.1:11436/v1
export LLM_API_KEY=local-only

make run MODE=final \
  FINAL_CONTRACT=/ABSOLUTE/PRIVATE/contract.json \
  FINAL_INPUT=/ABSOLUTE/PRIVATE/final_input.jsonl \
  FINAL_OUT_DIR=/ABSOLUTE/PRIVATE/final-runs \
  FINAL_RUN_ID=final-20261016-owner-approved \
  FINAL_ARGS='--timeout-s 600 --model-revision a411d838600baf0e3635a3daf66fb7c55fc97bb6'

PYTHONPATH=track_2a/src python -m uzh_rsd.final \
  --verify /ABSOLUTE/PRIVATE/final-runs/final-20261016-owner-approved
```

The service itself must be started only after rechecking exclusive ownership of
11436 and the hashes above. Morrow on 11435 must not be stopped or changed.
The final command makes exactly one request per contract record and has no
automatic retries. An uncertain delivery is a failed run, not permission to
retry.

## Bounded estimate

- Historical exact-revision GPU run: 168/168 calls in 71 minutes including
  model load; 88/168 parseable.
- Current local Q8 measurement: 18 generator calls in 503.472 seconds. Linear
  168-call estimate: 78.3 minutes of request latency. The observed long inputs
  frequently consume the full output cap, so runtime does not imply success.
- Reserve before launch: **2 hours inference + 30 minutes verification + 45
  minutes packaging + 75 minutes contingency = 4.5 hours**. The delivery plan's
  larger 4 h + 1 h + 45 min reservation is conservative and remains valid.

## Completed checks

- 337 Python tests pass, zero failures/skips, using the repository's pinned
  evaluator-capable environment.
- Synthetic Docker final path passes all 13 checks: unresolved-contract refusal,
  root entry point, one request per document, exact order/lengths/hashes,
  verifier acceptance, overwrite refusal, provenance and no key/label leakage.
- B2 projection evidence, B7 and B8 checksum packages verify. The historical
  final review snapshot remains `incomplete`; its metadata, diagnostics and
  run-summary hashes are recorded in the execution ledger.
- Existing B0 freeze checksums are not valid against this later branch's changed
  source files, and its private-ledger checksum entry cannot be resolved from
  this checkout. The PR #40 independent review remains the authority for the
  exact baseline commit; no baseline output was modified here.

## Remaining blockers

1. The official 12:00 CEST deadline has passed and official evidence says no
   extensions. No eligibility or extension is claimed.
2. No complete test prediction set exists; unchanged B2 has a measured
   completeness failure.
3. Full-set order, dropped-ID policy and final output-layout confirmation remain
   unresolved unless the owner accepts the provisional basis.
4. Team name/members and repository licensing require owner input.
5. No portal receipt or verified timely submission snapshot is present.

The smallest next decision is therefore not “which experiment?” It is whether
the owner has authoritative extension/timely-submission evidence and, if so,
whether to authorize one fail-closed final-test run under the exact package
above despite the known completeness risk.
