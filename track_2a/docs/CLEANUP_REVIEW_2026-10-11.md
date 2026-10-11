# Repository cleanup review — 11 October 2026

## Scope and authority

Owner explicitly requested cleanup and merge to main while arranging Apertus access. Reviewed Claude's PR #11 at `d98566f54eb0eaa5459de55e1103104c93548587`, targeting main `a4e1f01c072e7ec2c4b1167dbd2a0457e52108c4`. Source was materialized through the authenticated GitHub connector; repository code and tests were inspected directly. No Observatory snapshot exists in the inspected tree. No live Weavr read connector is available. No inbox command, Mission acceptance, dispatch or Need waiver was performed.

## Findings and repair

- Python 3.12 argparse looks up locale catalogs during parser construction. The CLI I/O spy test trapped that system lookup and failed before testing split rejection. The repair stubs only argparse's translation function inside that test. Application filesystem/network traps and the official-fetch trap remain active. Assertions now stay inside each subtest, avoiding a secondary unbound-variable error.
- The original lock installed successfully, but SciPy 1.18.1 native imports terminated this host with SIGBUS. A diagnostic attempt using upstream NumPy 2.0.2 / SciPy 1.13.1 also SIGBUSed. No package-pin change was retained: this does not establish a repository dependency defect.
- Full validation succeeded in a separate review environment using the runtime's NumPy 2.3.5 / SciPy 1.17.0 and nlpstats 0.0.1 on Python 3.12.14. This is not a fresh success with the repository lock; rerun that lock on the target host before submission.

## Observed checks

| Check | Result |
|---|---|
| Pinned dev fetch and integrity verification | PASS; only DE/FR/IT dev and three pinned evaluator/list files |
| Dev validation | PASS; 168 documents per language |
| Split suite after repair | PASS; 7 tests |
| Full `s1-check` with review Python | PASS; 56 tests, zero skips |
| Official evaluator parity | PASS, including synthetic predictions against dev gold |
| Fixed manifest rebuild | PASS; 61e0e98b7a9347716f4a71bc002364a600993c7346d6046e4f8d65899059a835 |
| CLI test-split rejection | PASS |
| Smoke with explicitly empty configuration | BLOCKED; zero requests, as expected |
| Real Apertus inference | NOT RUN; access pending |

Command: `make -C track_2a s1-check PYTHON=/workspace/scratch/42807ba8f996/review-env/bin/python`.
Review log SHA-256: `fd3bc37fc2b00667de2b592a70273fff91bdd9a17aa7b28e5fbe17849d0501ea`. A copy of the output is tracked as `review/s1-check-2026-10-11.log`.

Codex inspected Claude's implementation separately from its builder and reran checks. The small test repair and documentation cleanup are Codex-authored and self-reviewed; no separate review of those edits is claimed. This is repository integration evidence, not formal Faictory/Weavr S1-REVIEW acceptance. No live model result or completed submission is claimed.

## Integration disposition

Merge the reusable PR #11 foundation with this repair and current MVP documentation under the owner's explicit merge instruction. Close the unmerged PR #10 factory-preparation proposal as deferred/superseded for this submission, retaining its branch and history. Leave incomplete runtime/submission issues open. Publication and portal submission remain owner decisions.
