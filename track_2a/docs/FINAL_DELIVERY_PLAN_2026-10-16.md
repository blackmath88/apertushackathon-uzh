# Final delivery plan — 2026-10-16

## Authority and timing

This document switches Track 2A from research iteration to final-delivery preparation. Delivery completeness, reproducibility, verification, and honest reporting take priority over further experiments or cosmetic work.

The documented official deadline is **16 October 2026 at 12:00 CEST**. At plan creation (13:55 CEST), that time had passed. No extension or continuing eligibility is assumed. Official extension evidence must be recorded in the adjacent execution ledger before any eligibility claim. The owner's working cutoff is described as “tonight”; until an exact time is supplied, this plan uses **23:59 CEST on 16 October 2026** as an explicit scheduling assumption.

No merge, deployment, portal submission, external message, Weavr dispatch, test-input access, or final-test inference is authorized by this plan. Existing submitted or frozen snapshots remain immutable. Work after a submission freeze is labelled post-submission or final-delivery preparation.

**15:29 CEST owner update.** The owner subsequently authorized implementation,
bounded development inference, and one gold-blind final prediction run only if
the frozen development acceptance and runtime-feasibility checks pass. Portal
submission, merge, deployment, external messages, Weavr dispatch and Need
waivers remain forbidden. The official 12:00 deadline discrepancy remains
unresolved; the 23:59 time is an owner working cutoff, not organiser evidence.

The newly frozen candidate is `b2-windowed-v2`; its exact protocol and fixed
six-document development acceptance manifest are under
`experiments/final-long-input-20261016/`. This does not reopen the 489-document
Gate A run.

## Critical-path order

1. Inspect current PR #44 state, applicable instructions, current `main`, fresh Observatory evidence, PR #40 baseline evidence, B7/B8 results, judge contract, submission checklist, technical report, private artifact integrity, runtime ownership, and available compute.
2. Reserve final execution time before optional research. Under the 23:59 assumption, hold at least 4 hours for final inference, 1 hour for verification/repair-free failure accounting, and 45 minutes for packaging and owner handoff.
3. Preflight the only optional experiment: the already committed paired-evidence keep/drop verifier, maximum 36 local calls. Run it only if its generator, verifier, fixed development holdout, metrics, acceptance rule, runtime identity, and hard stop are frozen and the delivery reserve remains intact.
4. Freeze one delivery method from measured development evidence and operational readiness. C1 is not preferred merely for speed; its semantic improvement is unsupported. No new fallback may be invented, and missing predictions must remain visible.
5. Implement only bounded delivery fixes needed for a clean, reproducible official-format run. Verify them synthetically and offline without modifying prior experiment artifacts.
6. Produce an owner-gated final execution package: exact command, immutable inputs, code/model/runtime identity, ordering/schema checks, request and timeout bounds, completion checks, failure handling, verification command, runtime estimate, and buffer.
7. Finish the technical report, submission checklist, and source-to-evidence human-review demo in parallel where ownership does not conflict.

## Provisional schedule under the 23:59 CEST assumption

This schedule becomes concrete only after readiness inspection. Times are upper bounds, not authorization to access test inputs.

| CEST | Block | Exit condition |
|---|---|---|
| 13:55–15:15 | Evidence and readiness audit; durable freeze documents | Candidate choices, blockers, runtime ownership, extension evidence, and artifact integrity recorded |
| 15:15–16:15 | Optional verifier preflight and, only if safe, bounded execution | Maximum 36 calls settled or experiment skipped/stopped; acceptance decision recorded |
| 16:15–18:15 | Delivery code/package, synthetic checks, clean-checkout rehearsal | One method frozen; entry point and validators reproducible without test access |
| 18:15–19:00 | Owner authorization window and final-run staging | Exact command and smallest owner decision presented |
| 19:00–23:00 | Reserved final inference window | Used only after explicit owner authorization; one request in flight, no paid/cloud compute |
| 23:00–23:59 | Reserved verification, packaging, and handoff | Counts/order/lengths/hashes checked; failures visible; final evidence packaged |

If actual final inference is estimated above four hours, or the owner cutoff is earlier, the optional experiment is skipped first. The 489-case full-development Gate A run is prohibited and is never allowed to consume the final reserve.

## Candidate decision rule

Choose the simplest method that can produce complete official-format predictions with a clean-checkout path and explicit failure semantics. Rank evidence in this order:

1. operational completeness and contract compliance;
2. matched development official score and coverage;
3. robustness to malformed/truncated responses;
4. measured runtime within the owner cutoff;
5. implementation simplicity and auditability.

The verifier may replace its unchanged control only if the frozen acceptance rule passes. If evidence is inconclusive, retain the simpler supported candidate.

## Completion definition

Final-delivery preparation is complete when the adjacent ledger names the exact candidate commit and PR, the frozen method and command, successful clean-checkout/synthetic/integrity checks, all remaining blockers, the optional-experiment decision, a bounded runtime estimate, the smallest required owner decision, and settled worker/model-service state. Gate A stays closed unless separately and explicitly authorized.
