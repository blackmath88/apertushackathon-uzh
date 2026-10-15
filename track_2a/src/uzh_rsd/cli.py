from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from .contracts import DifferenceKind, SemanticDifference, TokenSpan
from .projection import project_differences
from .splits import SplitNotAllowedError, assert_development_split

S1_COMMANDS = ("fetch", "validate", "manifest", "smoke")
MVP_COMMANDS = ("infer", "evaluate", "run", "audit")
TRACK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = TRACK_ROOT / "manifests" / "s1-dev.json"
RUNS_DIR = TRACK_ROOT / "runs"
ENDPOINT_ENV = ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY")
EXIT_BLOCKED = 3


def _dry_run(split: str) -> dict:
    example = SemanticDifference(source=TokenSpan(1, 2), target=TokenSpan(1, 2), kind=DifferenceKind.CHANGE, severity=4.0, confidence=0.9)
    source_scores, target_scores = project_differences(3, 3, [example])
    return {"status": "scaffold-ok", "split": split, "strategy": "dry-run", "source_scores": source_scores, "target_scores": target_scores}


def _fetch(split: str) -> dict:
    from .data_adapter import LANGUAGES, fetch_split
    from .evaluation import fetch_official
    from .prompts import fetch_prompts

    files = {language: str(fetch_split(split, language)) for language in LANGUAGES}
    return {"status": "ok", "split": split, "files": files, "official": str(fetch_official()), "prompts": str(fetch_prompts())}


def _load_all(split: str) -> dict:
    from .data_adapter import LANGUAGES, load_split

    return {language: load_split(split, language) for language in LANGUAGES}


def _validate(split: str) -> dict:
    from .data_adapter import DATASET_REVISION

    records = _load_all(split)
    summary = {}
    for language, items in records.items():
        summary[f"en-{language}"] = {
            "documents": len(items),
            "tokens_a": sum(len(inference.text_a) for inference, _ in items),
            "tokens_b": sum(len(inference.text_b) for inference, _ in items),
            "side_b_fully_masked": sum(1 for _, gold in items if all(label == -1 for label in gold.labels_b)),
        }
    return {"status": "ok", "split": split, "revision": DATASET_REVISION, "pairs": summary}


def _manifest(split: str, output: Path, check: bool) -> dict:
    from .data_adapter import build_manifest
    from .evaluation import official_excluded_ids

    if split != "dev":
        raise SystemExit("The S1 manifest is defined on the dev split only.")
    excluded, excluded_sha = official_excluded_ids()
    manifest = build_manifest(_load_all(split), excluded, excluded_sha)
    if check:
        stored = json.loads(output.read_text())
        if stored != manifest:
            raise SystemExit(f"{output} differs from the deterministic rebuild")
        return {"status": "ok", "check": "manifest reproduces", "manifest_sha256": manifest["manifest_sha256"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {"status": "ok", "written": str(output), "counts": manifest["counts"], "manifest_sha256": manifest["manifest_sha256"]}


def _smoke(confirm_live: bool) -> tuple[dict, int]:
    from .apertus_smoke import EXIT_CODES, run_smoke, write_record

    record = run_smoke(confirm_live=confirm_live)
    record["record_path"] = str(write_record(record))
    return record, EXIT_CODES.get(record["status"], 1)


def _infer(args) -> tuple[dict, int]:
    """Endpoint path (judges): LLM_NAME / LLM_BASE_URL / LLM_API_KEY."""
    from .backends import OpenAICompatibleBackend
    from .runner import MAX_NEW_TOKENS, PROMPT_VERSIONS, load_manifest, manifest_records, run_inference, interleave_languages

    missing = [name for name in ENDPOINT_ENV if not os.environ.get(name)]
    if missing:
        return {"status": "BLOCKED", "reason": f"missing environment variables: {missing}",
                "help": "Set an OpenAI-compatible Apertus endpoint, or reproduce the committed results with `make reproduce`."}, EXIT_BLOCKED
    manifest = load_manifest(args.manifest)
    run_id = args.run_id or "endpoint-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.runs_dir / run_id
    if (run_dir / "raw.jsonl").exists():
        raise SystemExit(f"{run_dir}/raw.jsonl exists; choose a new --run-id")
    backend = OpenAICompatibleBackend(os.environ["LLM_BASE_URL"], os.environ["LLM_NAME"], os.environ["LLM_API_KEY"])
    items = interleave_languages([inference for inference, _gold in manifest_records(manifest, limit=args.limit)])
    meta = {"schema": "uzh-rsd.run-meta/v1", "run_id": run_id, "backend": backend.describe(), "manifest_sha256": manifest["manifest_sha256"],
            "methods": args.methods.split(","), "prompt_versions": PROMPT_VERSIONS, "max_new_tokens": MAX_NEW_TOKENS,
            "limit": args.limit, "documents": [item.id for item in items],
            "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    run_dir.mkdir(parents=True, exist_ok=True)
    counts = run_inference(backend, items, args.methods.split(","), run_dir / "raw.jsonl", run_id=run_id)
    meta.update(status="finished", counts=counts, finished_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return {"status": "ok", "run_dir": str(run_dir), "counts": counts}, 0


def _resolve_run(value: str, runs_dir: Path) -> Path:
    path = Path(value)
    if (path / "raw.jsonl").exists():
        return path
    if (runs_dir / value / "raw.jsonl").exists():
        return runs_dir / value
    raise SystemExit(f"no raw.jsonl found for run {value!r}")


def _evaluate(args) -> dict:
    from .runner import load_manifest
    from .scoring import evaluate_run

    run_dir = _resolve_run(args.run, args.runs_dir)
    results = evaluate_run(run_dir, load_manifest(args.manifest))
    print((run_dir / "results.md").read_text(), file=sys.stderr)
    return {"status": "ok", "run_dir": str(run_dir), "matched_documents": results["matched_documents"],
            "macro_matched": {m: v["macro"] for m, v in results["views"]["matched"].items()}}


def _audit(args, argv) -> dict:
    from .audit import write_audit
    from .runner import load_manifest

    run_dir = _resolve_run(args.run, args.runs_dir)
    out_dir = args.out or TRACK_ROOT / "diagnostics" / run_dir.name
    invocation = "python -m uzh_rsd.cli " + " ".join(argv if argv is not None else sys.argv[1:])
    audit = write_audit(run_dir, out_dir, load_manifest(args.manifest), invocation)
    return {"status": "ok", "out_dir": str(out_dir), "run_directory_unchanged": audit["inputs"]["run_directory_unchanged"],
            "b0": audit["summary"]["b0"], "b2_items": audit["summary"]["b2"]["items"], "b2_excerpts": audit["summary"]["b2"]["excerpts"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwissGov-RSD experiment CLI (dev split only)")
    parser.add_argument("command", nargs="?", default="dry-run", choices=("dry-run", *S1_COMMANDS, *MVP_COMMANDS))
    parser.add_argument("--strategy", default="dry-run")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true", help="manifest: verify the tracked file instead of writing it")
    parser.add_argument("--confirm-live", action="store_true", help="smoke: allow exactly one real endpoint request")
    parser.add_argument("--methods", default="b0,b2", help="infer/run: comma-separated methods")
    parser.add_argument("--run-id", default=None, help="infer/run: run directory name under runs/")
    parser.add_argument("--run", default=None, help="evaluate/audit: run id or run directory")
    parser.add_argument("--out", type=Path, default=None, help="audit: output directory (default diagnostics/<run id>)")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    parser.add_argument("--limit", type=int, default=None, help="infer/run: first N manifest entries only")
    args = parser.parse_args(argv)

    # Split policy is enforced before any command touches files or the network.
    try:
        split = assert_development_split(args.split)
    except SplitNotAllowedError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.strategy != "dry-run":
        print("error: --strategy is the scaffold switch; use --methods b0,b2 with infer/run.", file=sys.stderr)
        return 2

    exit_code = 0
    if args.command == "dry-run":
        result = _dry_run(split)
    elif args.command == "fetch":
        result = _fetch(split)
    elif args.command == "validate":
        result = _validate(split)
    elif args.command == "manifest":
        result = _manifest(split, args.manifest, args.check)
    elif args.command == "smoke":
        result, exit_code = _smoke(args.confirm_live)
    elif args.command == "infer":
        result, exit_code = _infer(args)
    elif args.command == "evaluate":
        if not args.run:
            print("error: evaluate needs --run", file=sys.stderr)
            return 2
        result = _evaluate(args)
    elif args.command == "audit":
        if not args.run:
            print("error: audit needs --run", file=sys.stderr)
            return 2
        result = _audit(args, argv)
    else:  # run: fetch, endpoint inference, evaluation (endpoint checked first)
        if all(os.environ.get(name) for name in ENDPOINT_ENV):
            _fetch(split)
        result, exit_code = _infer(args)
        if exit_code == 0:
            args.run = result["run_dir"]
            result = {**result, "evaluation": _evaluate(args)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
