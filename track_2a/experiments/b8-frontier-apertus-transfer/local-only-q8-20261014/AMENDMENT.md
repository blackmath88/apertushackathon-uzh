# B8 append-only local execution erratum

The frozen protocol remains unchanged. Coordinator message
`msg_bec0a50ab33b` authorizes a deterministic local-only derivative because no
teacher provider or immutable teacher revision exists and frontier/cloud calls
remain forbidden.

Before inference, the committed 504-row schedule was regenerated and filtered
without altering any selected row, prompt, case, label map, configuration, or
expected relation. The derivative contains 234 rows: 72 student matched-direct
R0-R3 calls, 144 student control calls, and 18 deterministic/no-teacher
transfer calls. All 252 teacher-role rows and 18 teacher-generic transfer rows
are excluded. Their status is **NOT RUN — AUTHORIZATION/PROVIDER**.

The derivative's canonical SHA-256 is
`61bea1f9c939a07b114dbfe8fdf11197cc47d62a3be61f1b7725b4e9b44bf45d`.
It estimates 31,122 prompt tokens and 936 seconds, within the original ceilings.
No local call may begin unless the exact GGUF, llama.cpp commit, loopback
endpoint, SYCL0 device, 99 GPU layers, process ownership, and unchanged Morrow
process have been attested.
