# B7 scientific report

## Verdict

**PARTIALLY SUPPORTED: retain S2 as a structural comparator; the current
Apertus verifier and R3 router are NOT SUPPORTED.** CTF-restricted DiffAlign is
the one supported B7 mechanism. It raises macro Spearman from regenerated S1
0.188300 to 0.215422 (+0.027122, paired family-bootstrap delta CI95
`[0.008329, 0.046366]`) and from published B4 0.187117 by +0.028305. Every
leave-one-family-out S2–S1 delta remains positive (`[0.020569, 0.031578]`).

The Apertus synthetic capability gate fails without retuning: primary accuracy
is 0.7917 (<0.80), label-permutation stability is 0.5417 (<0.85), and
contrastive-choice accuracy is 0.4792. Passage reversal (0.9583), combined
reversal (0.875), counterpart sensitivity (0.875), valid outputs (1.0), and
equivalent false-positive rate (0.0) pass, but the frozen gate requires every
condition. Synthetic success is therefore not claimed, and benchmark movement
does not promote the verifier.

## Structural control

| Arm | DE | FR | IT | Macro | Delta vs stated comparator | CI95 delta |
|---|---:|---:|---:|---:|---:|---:|
| S0/E0 published B4 | 0.217865 | 0.135347 | 0.208138 | 0.187117 | — | — |
| S1/E1 regenerated M0 | 0.220659 | 0.135098 | 0.209144 | 0.188300 | +0.001184 vs S0 | [0.000127, 0.002300] |
| S2/E2 CTF width 8 | 0.239710 | 0.168364 | 0.238192 | **0.215422** | **+0.027122 vs S1** | **[0.008329, 0.046366]** |

S2 uses the exact B5 matrices and maps, with 30/30 cache hashes verified. No
embedding was regenerated. The coarse-to-fine mask retained a mean 20.91% of
matrix cells (range 5.71–74.93%). All 30 documents and all 18,485 evaluated
official tokens have finite predictions; punctuation masks and vector lengths
are unchanged. S2 has 888/1383/919 ties in DE/FR/IT and zero alignment failures.

## Routing and semantic arms

| Arm | Meaning | Macro | Delta vs B4 |
|---|---|---:|---:|
| E3 | deterministic R3 discrepancy | 0.190245 | +0.003128 |
| E5 | shuffled Apertus, identical R1 candidates | 0.193465 | +0.006348 |
| E6 | actual Apertus, identical R1 candidates | 0.199843 | +0.012726 |
| E7 random | R2 actual Apertus | 0.183570 | −0.003546 |
| E7 routed | R3 actual Apertus | 0.190217 | +0.003100 |

E6 exceeds E5 by +0.006378; the paired family-bootstrap delta CI95 is narrowly
positive `[0.000066, 0.012801]`. It also exceeds the identical non-Apertus
fallback by +0.012726 (`[0.004441, 0.019974]`). This is measured incremental
signal, but it does not override the failed independent capability gate or make
the verifier supported.

R1 recalls 15.46% of B4-missed positives at 3.47% eligible-token coverage. R2
recalls 5.10%; R3 recalls 6.37%. A frozen-manifest accounting defect makes the
E7 routing contrast non-causal: all routes match 734 raw official token IDs,
but they do not match evaluated (non-punctuation) scoring coverage (R1 641, R2
643, R3 734). The discrepancy was found only during gold-aware integrity
accounting and was not repaired or tuned post hoc. E7 is reported but explicitly
**not comparable**; R3 receives no support. E4 was not measured because no
independently pinned compact comparator fit the zero-download dependency ceiling.

## Apertus execution and cost

The existing GGUF SHA-256 is `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`.
Exactly 1,770 calls ran on 127.0.0.1:11436: 1,578 shared benchmark candidates
and 192 synthetic calls. All were valid; none errored or retried. They consumed
132,480 prompt and 3,540 completion tokens, 497.15 seconds summed request
latency, and zero paid/cloud cost. Every prompt, raw output, usage object,
configuration and latency is in the two raw JSONL files. Morrow remained healthy
and unchanged at PID 1240 on port 11435; the B7 server was stopped afterward.

## Blinded audit

The frozen 5/5/5 audit found 0 supported, 6 unsupported, and 9 unresolved
semantic differences. Nine correspondences were invalid, mostly because a
single token or unavailable anchor did not present a reviewable proposition.
Method identity, predictions, category and official labels are absent from the
review packet; the separate key was not consulted during annotation. Official
labels were not modified.

## Integrity, limitations, and decision

The protocol and candidates were committed at `70b1eaf` before S2, inference,
or gold-aware evaluation. The separately titled original Perplexity handoff was
not present; the full supplied B7 contract is archived verbatim with that
limitation. Published B4 remains the operational benchmark and regenerated B5
is not substituted for it. B5 and B6 remain NOT SUPPORTED.

The sample is only 30 documents/27 source families. S2 is a credible supported
comparator, not a submission decision. The current verifier is rejected because
its synthetic presentation sensitivity violates the frozen gate, and the R3
router is rejected because its matched-budget causal comparison is invalid.
No protected test data or metadata, final HF job, paid inference, fine-tuning,
deployment, publication, outreach, submission, or Weavr mutation occurred.

Final verification ran 189 tests with 0 failures and 0 skips, reproduced the
frozen dev manifest, and exercised the expected pre-I/O test-split refusal.
Candidate and S2 reruns were byte-identical to the committed artifacts. Two
earlier environment attempts are retained in the test log history: the borrowed
B5 venv lacked evaluator dependencies, then the minimal evaluator venv lacked
the HF launcher dependency and encountered the pre-existing second-boundary
gzip test flake. Installing the repository's two pinned requirement files in an
ignored task-local venv produced the authoritative clean run; no system Python
or experimental output changed.
