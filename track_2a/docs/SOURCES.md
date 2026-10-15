# Sources and Provenance

Pinned in S1 on 7 October 2026. "Verified" means read or hashed in this
session; everything else is a link only.

## Pinned revisions

| Artefact | Pin | Licence | How it is used |
|---|---|---|---|
| HF dataset `ZurichNLP/SwissGov-RSD` | revision `f16aa0536811b8c0cf975fede21eec5996e4b3c1` (lastModified 2026-07-30) | Labels CC BY 4.0; text © Swiss federal authorities ([terms](https://www.admin.ch/gov/en/start/terms-and-conditions.html)) per dataset `LICENSE.md` | Only `data/{de,fr,it}/dev_*.jsonl` are downloaded, into ignored `data/raw/`; git blob SHA-1 and size verified (see `data_adapter.py`). Test files are never requested. |
| GitHub `ZurichNLP/SwissGov-RSD` | commit `1807a42100e742ed03d337c54c4b9ea86995f565` (2026-07-30) | **No top-level licence file.** Only `rsd/LICENSE` (MIT, © 2023 University of Zurich) covers the `rsd/` package. | `scripts/evaluate_predictions_admin.py` (sha256 `3e8101…83fa`), `evaluation/utils.py` (`8da64a…0b`), `list_to_drop.txt` (`3bd489…57a`) fetched into ignored `data/official/` and hash-checked; executed only by parity tests. Not vendored because of the missing licence. |
| HackApertus `project-template` | commit `7f2382275461baf3fa6c8855d157d86abffe9f0e` (2026-10-01) | Apache-2.0 (template); projects CC BY 4.0 per its `technical_report.md` | Layout, `make run` via Docker, `LLM_NAME`/`LLM_BASE_URL`/`LLM_API_KEY`, `data/` ≤ 100 MB. |
| UZH challenge brief | Notion page `hackapertus.notion.site/track-2a-uzh`, rendered 2026-10-07 | — | Rules summarised in [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md). |
| Apertus v1.5 8B | HF `swiss-ai/Apertus-v1.5-8B` @ `a411d838600baf0e3635a3daf66fb7c55fc97bb6` | Apache-2.0, gated (`auto`) | Model card states context up to 262,144 tokens. Config/tokenizer not readable without an HF token. |
| Apertus v1.5 70B | HF `swiss-ai/Apertus-v1.5-70B` @ `59e744e313e967811aefabde3732609b64201acc` | Apache-2.0, gated (`auto`) | Same. |

The `dev` gold directory in the GitHub repo is further split by
`scripts/split_admin.py --train` into `dev/train` (134 docs) and `dev/val`
(34 docs). The HF dataset publishes only `dev` (168 docs per language) and
`test` (56). There is no separate official `train` split.

## Hack Apertus

- Event: https://hackapertus.ch/
- Getting started guide: https://hackapertus.notion.site/getting-started-guide-onlinehack
- UZH challenge: https://hackapertus.notion.site/track-2a-uzh
- Resources and compute: https://hackapertus.notion.site/resources-tools
- How to submit: https://hackapertus.notion.site/how-to-submit-a-project
- Submission portal: https://hackapertus.ch/online-hack/submissions (not Devpost)
- Official project template: https://github.com/HackApertus/project-template
- Terms (open-source requirement): https://hackapertus.ch/terms-and-conditions

## UZH / SwissGov-RSD

- Official repository: https://github.com/ZurichNLP/SwissGov-RSD
- ACL 2026 paper: https://aclanthology.org/2026.acl-long.1437/
- Hugging Face dataset: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD
- Multi-parallel translation subset: https://github.com/miwytt/multi-parallel-swissgov
- Published prompts: https://github.com/ZurichNLP/SwissGov-RSD/tree/master/prompt_templates. B0 uses `template_{de,fr,it}_admin.txt` at commit `1807a42`, fetched at run time and sha256-verified (`ace9e0f8…`, `3d65ebd9…`, `79e6cd0c…`; see `prompts.py`). They are not vendored, because of the missing licence.
- HF Jobs image for measured runs: `ghcr.io/swiss-ai/vllm_apertus_1.5_release:latest-amd64` (Swiss AI release image). `latest` is a moving tag, so each run records the transformers/torch/CUDA versions it actually used.

## Architectural parent

- accessibility-red-team: https://github.com/blackmath88/accessibility-red-team
- semantic compiler: https://github.com/blackmath88/accessibility-red-team/blob/main/docs/SEMANTIC_COMPILER.md

The parent is prior architectural work, not the Hack Apertus project. Reuse is selective and conceptual.
