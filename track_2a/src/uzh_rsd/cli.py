from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import DifferenceKind, SemanticDifference, TokenSpan
from .projection import project_differences
from .splits import SplitNotAllowedError, assert_development_split

S1_COMMANDS = ("fetch", "validate", "manifest", "smoke")
DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / "manifests" / "s1-dev.json"


def _dry_run(split: str) -> dict:
    example = SemanticDifference(source=TokenSpan(1, 2), target=TokenSpan(1, 2), kind=DifferenceKind.CHANGE, severity=4.0, confidence=0.9)
    source_scores, target_scores = project_differences(3, 3, [example])
    return {"status": "scaffold-ok", "split": split, "strategy": "dry-run", "source_scores": source_scores, "target_scores": target_scores}


def _fetch(split: str) -> dict:
    from .data_adapter import LANGUAGES, fetch_split
    from .evaluation import fetch_official

    files = {language: str(fetch_split(split, language)) for language in LANGUAGES}
    return {"status": "ok", "split": split, "files": files, "official": str(fetch_official())}


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwissGov-RSD experiment CLI (S1: contract, data and runtime readiness)")
    parser.add_argument("command", nargs="?", default="dry-run", choices=("dry-run", *S1_COMMANDS))
    parser.add_argument("--strategy", default="dry-run")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--check", action="store_true", help="manifest: verify the tracked file instead of writing it")
    parser.add_argument("--confirm-live", action="store_true", help="smoke: allow exactly one real endpoint request")
    args = parser.parse_args(argv)

    # Split policy is enforced before any command touches files or the network.
    try:
        split = assert_development_split(args.split)
    except SplitNotAllowedError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.strategy != "dry-run":
        print("error: only the dry-run strategy exists in S1; B0 is S2 scope.", file=sys.stderr)
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
    else:
        result, exit_code = _smoke(args.confirm_live)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
