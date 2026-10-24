# Post-hoc amended execution contract

This amendment records the execution actually reported by commit
`a5e50e9483f387153769fe8a4f9a7a62edb205fa`. It does not alter the immutable
freeze at `1384e04642b6be805e9b8baa7560845dda3afb42`, rerun inference, repair model
outputs, or change any metric.

## Protocol-deviation classification

The execution commit changed the runner after the pre-inference freeze. The
frozen runner hash was
`7f257fa8bd5be9e6ae4f4137ef4f20ad1de3c634fbce15712d839f33f178e961`;
the runner committed with the execution is
`7f325235a333113f11dcc748a4ede155a57c891b16fbe3786995aeaa8d1ed29b`.
The corresponding test hashes are respectively
`5519b90c9b697b32d3fd05e29959823857428fef929d95872618a985f0819b4d`
and `1a41b0af84ec2913c9188888e0bf9aecadc92b9091de52341d87f6c440820e76`.
The execution commit also introduced the result builder at hash
`940f959b4b3c493bc0a6b93960e8b290fae1c253778bd0b7589246126b3f7b97`.

The post-freeze runner adds exact-token context-overflow handling, revised
attempt accounting, and reconciliation of one interrupted durable intent
without resend. These changes are narrow and tested, but because code and
results first appear in the same commit, repository history does not
independently prove the byte-exact runner state at each model call. The result
must therefore be cited as a descriptive, deviated run, never as strict
execution of the byte-exact frozen runner. A future confirmatory run must freeze
these behaviors before its first request.

## Preserved result contract

- Intended/resolved: 489/489; endpoint attempts: 334; returned: 333;
  deterministic context overflows: 155; transport/runtime failures: 1;
  unstarted or unresolved: 0.
- Parseable: 59/489; strictly valid: 1/489; fallback: 430 documents and
  378364 token positions.
- Official-evaluator all-manifest macro: `0.01021567996488429`.
- Official-evaluator available-only macro: `0.0875492679378083`, conditional
  on 18 EN-DE, 18 EN-FR, and 23 EN-IT documents.
- Known endpoint-reported usage for the 333 returned requests: 889752 prompt,
  936390 completion, and 1826142 combined tokens. Usage for the failed call is
  unavailable; the totals do not bound all 334 endpoint attempts.

The all-manifest result substitutes the declared zero-difference fallback for
430 documents and mainly characterizes that failure policy. This repeatedly
exposed development set is neither a holdout nor a hidden-test result.

## Runtime and boundary evidence

The private evidence files are retained under the ignored
`track_2a/data/private/nebu-full-dev-b0-v1/run/` directory. Their non-sensitive
digests are committed in `runtime-evidence-checksums.sha256`, and review-safe
counts and runtime identities in `runtime-evidence-summary.json`.

The host restart replaced Morrow's observed process: PID 1240/start tick 8199
before, PID 1224/start tick 11150 after. The same command/configuration was
observed after restart; Morrow listened on port 11435 and the baseline port
11436 was closed after execution. This supports port separation and observed
configuration equivalence only. It does not establish process continuity or
mutation-free continuity, and this amendment makes no claim that Morrow was
unchanged across the restart.

Model and binary hashes attest local artifacts, while endpoint captures attest
advertised identity. Neither proves which process generated each response.
