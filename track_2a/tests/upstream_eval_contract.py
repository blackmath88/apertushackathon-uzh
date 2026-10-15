"""Establish the pinned upstream evaluator's prediction contract with SYNTHETIC data only.

Runs the real `scripts/evaluate_predictions_admin.py`, `evaluation/utils.py` and
`evaluation/predictions.py` from ZurichNLP/SwissGov-RSD@1807a42 in a scratch tree whose
gold files, drop list and predictions are all synthetic. Two minimal stand-ins: a
`jsonlines` reader (not installed here) and `rsd/recognizers/utils.py` reduced to the
upstream `DifferenceSample` dataclass (the real module imports torch). No real gold
labels are read. Not part of unittest discovery (it fetches one pinned upstream file).

Run from track_2a/: PYTHONPATH=src .venv/bin/python tests/upstream_eval_contract.py
"""

import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from uzh_rsd.evaluation import DEFAULT_OFFICIAL_DIR

COMMIT = "1807a42100e742ed03d337c54c4b9ea86995f565"
PREDICTIONS_URL = f"https://raw.githubusercontent.com/ZurichNLP/SwissGov-RSD/{COMMIT}/evaluation/predictions.py"
JSONLINES_SHIM = '''import builtins, json
class _Reader:
    def __init__(self, path): self._f = builtins.open(path, encoding="utf-8")
    def __enter__(self): return self
    def __exit__(self, *a): self._f.close()
    def __iter__(self): return (json.loads(l) for l in self._f if l.strip())
def open(path, mode="r"):
    return _Reader(path)
'''
DIFFERENCE_SAMPLE = '''from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class DifferenceSample:  # verbatim fields of upstream rsd/recognizers/utils.py@1807a42
    tokens_a: Tuple[str, ...]
    tokens_b: Tuple[str, ...]
    labels_a: Tuple[float, ...]
    labels_b: Optional[Tuple[float, ...]]
    annotator_tag: Optional[int] = None
'''


def build_tree(root: Path) -> str:
    official = Path(DEFAULT_OFFICIAL_DIR)
    (root / "scripts").mkdir(parents=True)
    shutil.copy(official / "scripts" / "evaluate_predictions_admin.py", root / "scripts")
    (root / "evaluation").mkdir()
    (root / "evaluation" / "__init__.py").write_text("")
    shutil.copy(official / "evaluation" / "utils.py", root / "evaluation")
    data = urllib.request.urlopen(PREDICTIONS_URL, timeout=30).read()
    (root / "evaluation" / "predictions.py").write_bytes(data)
    (root / "rsd" / "recognizers").mkdir(parents=True)
    (root / "rsd" / "__init__.py").write_text("")
    (root / "rsd" / "recognizers" / "__init__.py").write_text("")
    (root / "rsd" / "recognizers" / "utils.py").write_text(DIFFERENCE_SAMPLE)
    (root / "jsonlines.py").write_text(JSONLINES_SHIM)
    return hashlib.sha256(data).hexdigest()


def synthetic_gold(root: Path, rng: random.Random):
    """6 synthetic full documents per language; test = positions 1, 3, 4 in full order; id 'X_3' on the drop list."""
    full, test = {}, {}
    for lang in ("de", "fr", "it"):
        docs = []
        for i in range(6):
            n_a, n_b = rng.randint(5, 9), rng.randint(5, 9)
            labels_a = [round(rng.random(), 3) for _ in range(n_a)]
            labels_b = [round(rng.random(), 3) for _ in range(n_b)] if i != 4 else [-1] * n_b  # doc 4: side b fully masked
            labels_a[-1] = -1  # punctuation mask
            docs.append({"id": f"admin_{lang}_{i}", "text_a": " ".join(f"a{j}" for j in range(n_a)), "text_b": " ".join(f"b{j}" for j in range(n_b)),
                         "labels_a": labels_a, "labels_b": labels_b, "annotator_tag": 1})
        full[lang], test[lang] = docs, [docs[i] for i in (1, 3, 4)]
        for split, rows in (("full", docs), ("test", test[lang])):
            path = root / "data" / "evaluation" / "gold_labels" / split / f"gold_admin_{lang}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (root / "list_to_drop.txt").write_text("admin_de_3\nadmin_fr_3\nadmin_it_3\n")
    return full, test


def as_prediction(doc, noise=None):
    clean = lambda labels: [0.0 if l == -1 else l for l in labels]  # predictions lie in [0,1]
    return {"id": doc["id"], "text_a": doc["text_a"], "text_b": doc["text_b"], "labels_a": clean(doc["labels_a"]), "labels_b": clean(doc["labels_b"])}


def write_predictions(root: Path, folder: str, rows_by_lang):
    prefix = root / folder / "pred_admin_"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    suffix = ".jsonl" if "llm_predictions" in folder else ".jsonl.jsonl"
    for lang, rows in rows_by_lang.items():
        Path(f"{prefix}{lang}{suffix}").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return prefix


def evaluate(root: Path, prefix: Path, split="test"):
    proc = subprocess.run([sys.executable, "scripts/evaluate_predictions_admin.py", str(prefix), "--split", split],
                          cwd=root, capture_output=True, text=True, env={"PYTHONPATH": str(root), "PATH": "/usr/bin:/bin"})
    spearman = None
    lines = proc.stdout.splitlines()
    if "Spearman:" in lines:
        values = lines[lines.index("Spearman:") + 2].split("\t")
        spearman = [float(v.replace(",", ".")) for v in values]
    return {"exit": proc.returncode, "spearman": spearman, "error": (proc.stderr.strip().splitlines() or [""])[-1][:160]}


def main() -> int:
    rng = random.Random(7)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        predictions_sha = build_tree(root)
        full, test = synthetic_gold(root, rng)
        cases = {
            "test_only_in_test_order": {l: [as_prediction(d) for d in test[l]] for l in full},
            "test_only_sorted_by_id_desc": {l: [as_prediction(d) for d in sorted(test[l], key=lambda d: d["id"], reverse=True)] for l in full},
            "full_set_in_full_order": {l: [as_prediction(d) for d in full[l]] for l in full},
            "full_set_reversed": {l: [as_prediction(d) for d in reversed(full[l])] for l in full},
            "test_only_ids_rewritten": {l: [dict(as_prediction(d), id="WRONG") for d in test[l]] for l in full},
            "count_neither_test_nor_full": {l: [as_prediction(d) for d in full[l][:4]] for l in full},
        }
        results = {name: evaluate(root, write_predictions(root, f"encoder_predictions/{name}", rows)) for name, rows in cases.items()}
        # path-dependent drop: a folder containing "llm" drops LIST_TO_DROP ids from predictions first
        results["llm_path_full_set_with_dropped_id"] = evaluate(root, write_predictions(root, "llm_predictions_x/full", cases["full_set_in_full_order"]))
        results["llm_path_test_only_with_dropped_id"] = evaluate(root, write_predictions(root, "llm_predictions_x/test", cases["test_only_in_test_order"]))
        summary = {"upstream_commit": COMMIT, "predictions_py_sha256": predictions_sha,
                   "synthetic_setup": "6 full docs/lang; test = full positions 1,3,4 (same relative order); admin_*_3 on drop list and in test; "
                                      "predictions equal to gold (punctuation -1 -> 0), so a correctly aligned evaluation gives Spearman 1.0",
                   "results": results}
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
