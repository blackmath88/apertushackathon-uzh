# Full-dev B0 execution — descriptive result with protocol deviation

Status: **RUN FINISHED; INCOMPLETE MODEL PREDICTIONS; NOT a strict
frozen-protocol execution.** The completed descriptive results below are
preserved unchanged. Independent review found that the execution commit also
changed the frozen runner, so this run is explicitly classified as a
post-freeze protocol deviation; see `AMENDED_EXECUTION_CONTRACT.md`.

Intended 489; attempted 334; returned 333; unstarted 0.
Parseable 59; strictly valid 1; fallback documents 430; fallback tokens 378364.

## Official Spearman

| View | EN-DE | EN-FR | EN-IT | Macro |
|---|---:|---:|---:|---:|
| All manifest | -0.001041 | 0.031078 | 0.000610 | 0.010216 |
| Available only | 0.116453 | 0.105002 | 0.041192 | 0.087549 |

Available-only denominators: EN-DE 18, EN-FR 18, EN-IT 23.

## Accounting

Known endpoint-reported usage for the 333 returned requests: prompt tokens
889752; completion tokens 936390; combined 1826142. Usage is unavailable for
the one transport/runtime failure, so these totals are not a complete bound on
all 334 attempted endpoint calls.
Endpoint latency total 28563.873 s; median 84.008 s; generation wall 28565.194 s.

Missing or unparseable documents use the frozen upstream similarity-5 (zero-difference) fallback only in the all-manifest view. Raw prompts, responses, and gold-bearing scoring inputs remain private; committed predictions contain no source text.

The host restart replaced the observed Morrow process: the pre-restart snapshot
records PID 1240/start tick 8199, while the post-restart snapshot records PID
1224/start tick 11150. The same command/configuration was observed after the
restart, Morrow remained on port 11435, and the baseline's port 11436 was
verified closed afterward. This establishes port separation and matching
observed configuration, not process continuity or mutation-free continuity
across the restart; no Morrow change is claimed.

Private runtime evidence is hash-anchored, without publishing its contents, in
`runtime-evidence-checksums.sha256`; non-sensitive counts and identities are in
`runtime-evidence-summary.json`.
