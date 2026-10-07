# S1 evidence — contract, data and runtime readiness

Builder: Claude Code (session-local, direct execution on owner instruction; **no
Weavr Mission was activated or dispatched**). This is builder evidence, not
independent review. Independent review must rerun the commands below on the
exact candidate commit.

- Base: `origin/main` @ `026678009ae98a015833ded2596ec8f713bf0877`
- Implementation commit checked: `e907ad205f131fc613bfd096485f5e1b62eda3c7`. The docs-only evidence commit follows it; see the PR for the final head SHA.
- Branch: `claude/quirky-babbage-wi047n` · Issue: #2
- Recommendation: **BLOCKED on S1-RUNTIME only.** All other criteria are evidenced. See the end of this file.

## Criterion-by-criterion

| ID | Result | Evidence |
|---|---|---|
| S1-RULES | ✅ with open Needs | [SOURCES.md](SOURCES.md) pins dataset `f16aa05…`, evaluator commit `1807a42…`, template `7f23822…`, Apertus model revisions and licences. [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) holds E1–E10, U1–U7 and Needs N-RULES-1…5, N-LIC-1, N-COMPUTE-1. |
| S1-SPLIT | ✅ | `test_s1_splits.py` (7 tests, 14 rejected inputs incl. `Test`, `" dev"`, `full`, `validation`, `None`). An `IOSpy` traps `open`, `io.open`, `os.replace/makedirs/stat/listdir`, `Path.exists/read_*/write_*/mkdir/open`, `urlopen`, `socket.create_connection`, `NamedTemporaryFile`. Zero calls recorded for `local_path`, `source_url`, `fetch_split`, `load_split` and every CLI command. No test URL/path/hash exists in the code. `train` → `SplitUnavailableError` before I/O. |
| S1-TOKENS | ✅ | `test_s1_tokens.py` (8 tests): equality with `str.split()` on 11 cases (NBSP, thin space, ideographic space, U+2028, tabs, CRLF, zero-width space, emoji/combining marks, repeated tokens). Offsets reproduce each token. Mismatched lengths raise `LengthMismatchError`; there is no padding or truncation. NaN/inf/bool/string/out-of-range values are rejected, and `-1` is allowed for gold only. All 504 dev records load with exact label lengths. |
| S1-MANIFEST | ✅ | `manifests/s1-dev.json`, `manifest_sha256` `61e0e98b…9a835` (file sha256 `e837c959…7e6bce`). Rule `s1-dev-manifest-v1`, declared in code before any experiment: docs present in DE/FR/IT dev, not in `list_to_drop.txt`, 40–400 tokens per side, ordered by `sha256(rule|index)`. Selected doc indices 43, 136, 197 → 3 pairs each for EN–DE, EN–FR, EN–IT (9 total, 88–267 tokens per side). The file holds no labels; gold is bound only by `gold_sha256`. `test_selection_is_gold_blind` proves gold changes do not change the selection. `make s1-check` rebuilds and compares the file. |
| S1-EVAL | ✅ | `test_s1_evaluation.py` (10 tests) executes the pinned official `compute_correlations` (sha256-verified bytes, loaders stubbed, nothing vendored). It agrees with ours on a hand fixture with ties and masking (1e-12), 25 seeded random trials with heavy ties (1e-12), and real dev gold for de/fr/it with seeded **synthetic** predictions on 40 docs per language, per language and macro (1e-10). Finding: the official code raises `IndexError` on constant predictions. Ours returns `None` plus a reason. Macro refuses missing or undefined languages. |
| S1-SCALE | ✅ | `severity.py`, `test_s1_severity.py` (6 tests): published table 5→0.0 … 0→1.0, -1→-1; `severity = 5 - similarity`; `difference = severity/5`; matches the pinned official `map_label_from_positive_to_negative` on 52 points; projected IR vectors convert to the 0–1 scale. Schema and contracts are unchanged (already 0–5 severity). |
| S1-RUNTIME | ⛔ **BLOCKED** | `apertus_smoke.py` plus `test_s1_apertus_smoke.py` (11 tests against a local **MOCK** server, which can only reach `MOCK_PASS`): one attempt, no retries; key, URL userinfo and query never serialised; identity check; HTTP 500, timeout, malformed JSON and missing usage handled explicitly. **Live run:** `make s1-smoke` → `BLOCKED: missing environment variables: ['LLM_NAME', 'LLM_BASE_URL', 'LLM_API_KEY']`, `attempts: 0`. No request was sent. |
| S1-REVIEW | ⬜ pending | Needs a separate Codex attempt on the exact head commit. |

## Commands and observed results (fresh clone of `e907ad2`)

| Command (from `track_2a/` unless noted) | Exit | Result |
|---|---|---|
| `make s1-setup` | 0 | venv with `requirements-s1.lock` |
| `make s1-fetch` | 0 | 3 dev files + 3 official files, hashes verified |
| `make s1-validate` | 0 | 168 docs per pair; tokens EN 65,320 / DE 61,101 / FR 77,585 / IT 71,008 |
| `make s1-check` | 0 | `Ran 56 tests … OK`, 0 skipped; manifest reproduces; `--split test` refused |
| `make s1-check PYTHON=<py3.11 venv: numpy 2.0.2, scipy 1.13.1, nlpstats 0.0.1>` | 0 | `Ran 56 tests … OK` under the official evaluator's numpy/scipy pins |
| `make test` / root `make test` | 0 / 0 | 56 tests OK each |
| root: `PYTHONPATH=track_2a/src python -m unittest discover -s track_2a/tests -p 'test_s1_*.py' -v` | 0 | 52 S1 tests OK (+4 scaffold tests in `make test`) |
| root: `PYTHONPATH=track_2a/src python3 -m uzh_rsd.cli --strategy dry-run --split test` | 2 | `error: Split 'test' is not available in development.` |
| `make s1-smoke` | 2 (make) / 3 (cli) | `BLOCKED`, no request |
| `make s1-check PYTHON=python3` (no nlpstats) | 1 | `skipped tests are not accepted`: the gate cannot pass without the parity run |

Builder log digests (logs are local to the builder session and not committed;
reviewers should regenerate them): s1-check `480fdfa8…eb226`, py3.11 s1-check
`7fffbf5f…6bb1`, fetch `466175cd…bb1`, validate `814129bf…481`, smoke
`9e66aea8…a756`.

## What was downloaded

Only `data/{de,fr,it}/dev_*.jsonl` from HF at the pinned revision, plus three
official code/list files from GitHub. Earlier context gathering used a
**blob-less, sparse** clone of the SwissGov-RSD repo containing only README,
`evaluation/`, `scripts/`, `prompt_templates/`, `requirements.txt` and
`rsd/` code. No data blobs were fetched, and no test or `full` gold file was
downloaded or opened at any point. File *names* and *sizes* of the gold
directories were listed from git tree metadata.

## Blockers and limitations

1. **N-COMPUTE-1 / S1-RUNTIME**: no `LLM_*` credentials in this environment. The Hack Apertus CSCS key distribution closed on 6 Oct 18:40 CEST, and the Phoeniqs compute applications closed on 4 Oct. Remaining options belong to the owner: an existing CSCS key, the HF $10 credit (Inference Providers), or a self-hosted vLLM. Apertus v1.5 weights are gated (`auto`), so even config and tokenizer require an HF token. Rerun: `export LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=…; make -C track_2a s1-smoke-live` (exactly one request).
2. **Context fit**: the model card claims a 262,144-token context. The endpoint's real context and output caps, and therefore whether full-document B0 fits, are unverified until the live request succeeds. The manifest bound (≤ 400 tokens/side) keeps the first tiny B0 run conservative.
3. **Evaluator licence (N-LIC-1)**: the SwissGov-RSD repo has no root licence, so the evaluator is fetched at run time, not vendored. Parity tests need network access once.
4. **Rules (N-RULES-1…5)**: final test procedure, `list_to_drop` policy and the prediction file format are unconfirmed. The UZH Q&A is on 8 Oct 12:00.
5. **No `train` split** exists in HF. The GitHub `dev/train` (134) / `dev/val` (34) partition is a candidate for S5 tuning/validation separation and is not wired up.
6. **Canton pilot**: dev metadata contains only federal `admin.ch` sources, so a Basel pilot needs separately collected authoritative pairs (S4).
7. Builder-run evidence only. Weavr/Faictory state was not read or changed. The AGENTS.md and S1 delivery contract proposed in PR #10 are unmerged; this work followed its narrowed allowlist.
