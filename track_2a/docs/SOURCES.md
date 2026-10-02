# Sources and Provenance

## Hack Apertus

- Event: https://hackapertus.ch/
- Submission portal: http://hackapertus.ch/online-hack/submissions
- Devpost: https://hackapertus.devpost.com/
- Official project template: https://github.com/HackApertus/project-template
- Resources/tools: https://hackapertus.notion.site/resources-tools

## UZH / SwissGov-RSD

- Official repository: https://github.com/ZurichNLP/SwissGov-RSD
- ACL 2026 paper: https://aclanthology.org/2026.acl-long.1437/
- Hugging Face dataset: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD
- Multi-parallel translation subset: https://github.com/miwytt/multi-parallel-swissgov
- Evaluation: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/scripts/evaluate_predictions_admin.py
- Prediction parsing: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/evaluation/predictions.py
- Evaluation utilities: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/evaluation/utils.py
- Published prompts: https://github.com/ZurichNLP/SwissGov-RSD/tree/master/prompt_templates

## Architectural parent

- accessibility-red-team: https://github.com/blackmath88/accessibility-red-team
- semantic compiler: https://github.com/blackmath88/accessibility-red-team/blob/main/docs/SEMANTIC_COMPILER.md

The parent is prior architectural work, not the Hack Apertus project. Reuse is selective and conceptual unless generic implementation is deliberately transplanted with provenance.

## Benchmark observations to pin in M1

- Gold/prediction representations contain two texts and per-token labels.
- Official evaluation filters gold label `-1` and computes global Spearman over concatenated token labels per language.
- Published LLM prompts ask for semantic similarity on a 0–5 scale and repository code maps this to difference severity.
- Development uses train/dev only; test remains untouched until final evaluation.

When M1 begins, record the exact SwissGov-RSD commit/revision and provenance/license of any copied evaluation code.
