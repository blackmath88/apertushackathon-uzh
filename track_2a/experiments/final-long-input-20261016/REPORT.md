# Final long-input delivery result

## Decision

**Rejected; no final prediction run.** `b2-windowed-v2` removed full-document
context overflow, preserved exact token maps, and kept every request within the
actual 8,192-token context. It did not demonstrate reliable completion. The
frozen acceptance therefore failed and the authorized conditional final run
was not started.

This is an engineering completion result, not an accuracy improvement claim.
The earlier B0/B2/C1/verifier/B4/B7 experiments were not repeated.

## Measured development result

The fixed gold-blind acceptance set contains the longest complete source group
and one long asymmetric source group: six documents, 2/2/2 DE/FR/IT. All 39
planned requests returned in 952.878 seconds with no transport failure.

| Check | Result |
|---|---:|
| Strict complete documents | 0/6 |
| Strict valid requests | 0/39 |
| Truncated at 1,024 output tokens | 5/39 |
| Non-truncated but invalid evidence | 34/39 |
| Largest prompt | 1,320 tokens |
| Largest prompt + reserved output | 2,344 / 8,192 tokens |
| Median / maximum request latency | 24.535 / 31.783 s |
| Prompt / completion tokens | 44,252 / 31,128 |

The input/context bound passed comfortably. The output/evidence contract failed:
the 160 reported difference items contained 146 over-40-token sides, 17
unlocated sides, and one unknown kind; only 80 items projected under the legacy
permissive parser. Every strict request was therefore either truncated or
invalid. No candidate prediction record was emitted and no failure was replaced
with zero.

## Semantic diagnostic

Gold was opened only by a separate offline command after generation finished.
Under the legacy permissive B2 parser, only 2/6 documents had all windows
parseable (DE `-0.498767`, FR `0.184649`; IT absent, macro undefined). A clearly
labelled sensitivity view that zero-fills failed windows scored DE `-0.018194`,
FR `0.079973`, IT `-0.048357`, macro `0.004474`. These are diagnostics, not
candidate predictions and not evidence of improvement.

## Full-run estimate

Planning all 489 gold-free dev inputs yields 959 deterministic requests (mean
1.961/document, median 2, p95 5, maximum 10). Scaling that distribution to the
historical 168-document final count gives approximately **330 requests** without
opening final inputs. At measured acceptance throughput this is 134.73 minutes
on median latency or 174.53 minutes using the slowest observed request. Adding
the mandatory 30-minute verification reserve gives 164.73–204.53 minutes.

The final run was prohibited for two independent reasons: acceptance failed,
and the conservative estimate plus verification exceeded the remaining
three-hour delivery envelope.

## Artifacts and preservation

- Frozen implementation commit: `70fc85ef973f9fa82f6b15207a4b4f4cb038ed29`.
- Fixed manifest digest: `a961d3def7b1cfa66558884b2477aa2a630a29cc8fd20e1a417466010bb8cfe3`.
- Private run ID: `final-long-input-dev-v1-70fc85e`.
- Private ledger SHA-256: `a14bbd6b25303fa5e217af2dfe9b7ee4220d0dc2c6744d1d7603254f9e4c3435`.
- Private diagnostic-score SHA-256:
  `405978b48f2dd0a9efb9056bc8c02ed0ef0e006045002dadae32685e36642dde`.

Raw prompts/responses, source text, predictions and gold remain ignored and
private. Existing experiments and scores were not overwritten. Apertus PID
91570 was stopped and 11436 verified closed; Morrow remains PID 1477 on 11435.

## Smallest next engineering change

Do not raise the output cap alone. The largest evidenced bottleneck is the
model's failure to keep excerpts short enough for reliable exact projection.
The next candidate should replace free-form copied excerpts with a bounded
per-window evidence representation that the model cannot expand beyond the
window map (for example, enumerated sentence IDs plus short within-sentence
anchors), while retaining strict failed-region semantics. It requires a new,
unexposed dev acceptance set and a separate runtime budget; it is not executed
here.
