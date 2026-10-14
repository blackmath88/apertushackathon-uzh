# Start here: project branches and review queue

Updated 14 October 2026. This is repository organisation, not scientific acceptance or permission to launch work.

## Four review entry points

| Area | Entry point | Purpose |
| --- | --- | --- |
| Foundation | PR #12 — `feat/b0-b2-mvp` | B0/B2 implementation, judge workflow and original evidence; targets main. |
| Experiments and research | `integration/experiments-research-20261014` | B2 projection through B8, baseline handoff, prompting, translation issue #30, adaptation and preserved research reports; targets PR #12's branch. |
| Federal application | PR #32 — `feat/federal-evidence-desk-20261014` | Scout, federal capture and polished review demo; targets PR #12's branch. Primary app direction. |
| Optional Zürich workflow | PR #22 — `feat/zurich-evidence-workflow` | Separate richer city review implementation; targets PR #12's branch. Keep for explicit migration/reuse, not the default app. |

There is not yet one integrated application-and-experiments checkout. These are distinct review units. Do not assume main contains the latest work.

## What the cleanup preserves

The research integration tree starts from B8 at `4cb217650d3b4b45bc56f6d040851ccd346b19d5`. It adds only 16 existing documentation blobs, unchanged, from #31, #18 and #23, plus this index. Its additional commit parents preserve all three source histories. No source code, model output, frozen manifest or experimental result is edited.

App #32 already contains all commits from #13, #20 and #21. Its PR base can move to the foundation without changing its branch. Those three predecessor PRs can close as superseded; their branches stay available.

The research integration contains #14–#19 (excluding unrelated app work), #23–#29 (excluding no content; #27/#29 enter through #31), and #31. Exact source heads are listed below. Closing the older PRs records consolidation, not approval of their results.

The running baseline's branch #27 and all original branches remain unchanged. No branch is deleted or force-pushed. No Weavr Mission/Need, runtime, model process, deployment or main branch is changed.

## Integration order and remaining work

1. Resolve the foundation #12's documented submission/reproducibility and review gates before merging to main. Its current head contains one later commit absent from the other stacks. Do not drop it or overwrite its audit history.
2. Review the federal app and research integration independently against that foundation. The consolidation itself is checked by commit ancestry and blob identity; it is not a fresh execution of all experiments.
3. When combining app and research code, reconcile their separate edits to `track_2a/Makefile`, then run combined offline gates. Preserve baseline prompts, predictions and frozen experimental evidence.
4. Keep #22 separate until the federal/Zürich bundle-contract migration is explicitly implemented and tested. Retargeting does not resolve that product/schema difference.
5. After approved integration and after active local work has settled, obsolete remote branches can be deleted in a separate cleanup. Retain tags or commits needed by provenance and reproduction.

The user requested queue cleanup, not production acceptance. Main merge, deployment and branch deletion are not performed by this cleanup.

## Active research order

Finish and inspect the running baseline; then controlled prompt experiments; then the queued translation-assisted experiment (#30); then the bounded representation/adaptation pilot if earlier evidence still supports it. Plans are pending experiments, not results. Re-read current evidence and local process ownership before running anything.

B8 remains inconclusive; the Apertus verifier is not established. Preserve the reported limitations of each experiment. Protect the held-out test set from development.

## Original PR heads (recovery and provenance)

| PR | Branch | Preserved head |
| --- | --- | --- |
| #12 | `feat/b0-b2-mvp` | `68675a75113111c49864e9eb017d2e5415410682` |
| #13 | `feat/zurich-semantic-observatory-pilot` | `e023bff764d3c9626d5f2e30a4317a5ddbe7ae77` |
| #14 | `blackmath88/b2-projection-evidence` | `8f4e31dccd27c54ff5dba99088a09bd1557ee7ff` |
| #15 | `feat/b3-semantic-decision-middleware` | `5892e5060b80623a253ce648d9317ced0567a582` |
| #16 | `blackmath88/b3-sdm-implementation` | `a2433d463d490bc860095908db5bf502883f9e0a` |
| #17 | `blackmath88/b4-alignment-first-sdm` | `25380bf280bf6639c71ebbff0a927ceef6e2fffc` |
| #18 | `research/denkraum-b5-decision-gates-20261013` | `b6ab132dfe129ae77f1119afc6f297ebce687650` |
| #19 | `blackmath88/b5-competitive-semantic-alignment` | `25a9813507b6d0ab541ed10a7f9fce379c42148a` |
| #20 | `docs/federal-first-observatory-plan-20261013` | `01c70b1a765587f70acf19d9e2a2de25e7798410` |
| #21 | `blackmath88/lost-in-switzerland-federal-pilot` | `fe11baea4d5c30ceb36e6b87e3d249b09321cedd` |
| #22 | `feat/zurich-evidence-workflow` | `98a4c585fe8a3eea0d67661315e7b0f9a68424a1` |
| #23 | `research/semantic-risk-and-multipass-literature-20261013` | `f0d777a3095220f49854bc8d1039872ce7d7baff` |
| #24 | `blackmath88/b6-semantic-risk-atlas` | `39f710194f29260a931d1e5fad1890617b7970d2` |
| #25 | `blackmath88/b7-structural-semantic-verification` | `95c625109bcbe0f7f960a6f2aca3fcba96a7509f` |
| #26 | `docs/b7-next-day-handoff-20261014` | `2a83afdc3e6238cd6d37da395b80e212a62bbb13` |
| #27 | `docs/nebu-full-dev-baseline-20261014` | `d6f14191b673925752b97ca06572ee1b626a7848` |
| #28 | `blackmath88/b8-frontier-apertus-transfer` | `4cb217650d3b4b45bc56f6d040851ccd346b19d5` |
| #29 | `research/alternative-prompts-20261014` | `24dbac1f4f06ac287052bd350f3797ee418595c6` |
| #31 | `research/apertus-adaptation-20261014` | `72cea19debb4cdb8d0bc96b7bca73bb7b106f622` |
| #32 | `feat/federal-evidence-desk-20261014` | `98d97dff022e885098a37c1a4350fa1a0b4646e3` |

All superseded PR bodies retain their historical reports with a pointer to the replacement. Closure does not mean their acceptance gates passed.
