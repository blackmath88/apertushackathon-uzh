"""Entrypoint inside the Hugging Face batch-GPU job.

Loads Apertus once, runs B0 and B2 on the identical manifest documents and
stores raw responses only (scoring happens offline). Durable retrieval:

1. after every call, ``raw.jsonl`` and ``run_meta.json`` are uploaded to the
   private dataset repo ``--output-repo`` under ``runs/<run_id>/``;
2. at the end, the run directory is also printed to the job log as a
   gzip+base64 tar between ``UZH-RSD-BUNDLE-BEGIN/END`` markers, as a fallback
   if uploads fail (recover with ``hf_launch collect --from-log``).

The HF token arrives as the ``HF_TOKEN`` job secret and is never printed.
Gold labels are discarded right after loading; prompts see inference inputs only.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import io
import json
import os
import sys
import tarfile
import time
import traceback
from pathlib import Path

from .data_adapter import fetch_split
from .prompts import fetch_prompts
from .runner import MAX_NEW_TOKENS, METHODS, PROMPT_VERSIONS, load_manifest, manifest_records, run_inference, interleave_languages

BUNDLE_BEGIN = "UZH-RSD-BUNDLE-BEGIN"
BUNDLE_END = "UZH-RSD-BUNDLE-END"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class Uploader:
    def __init__(self, repo: str | None, run_id: str):
        self.repo, self.prefix, self.failures = repo, f"runs/{run_id}", 0
        self.api = None
        if repo:
            from huggingface_hub import HfApi

            self.api = HfApi()

    def push(self, path: Path) -> None:
        if self.api is None:
            return
        try:
            self.api.upload_file(path_or_fileobj=str(path), path_in_repo=f"{self.prefix}/{path.name}", repo_id=self.repo,
                                 repo_type="dataset", commit_message=f"{self.prefix}: {path.name}")
        except Exception as error:  # keep running; the log bundle is the fallback
            self.failures += 1
            print(f"upload failed ({type(error).__name__}); continuing", flush=True)


def print_bundle(run_dir: Path) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted(run_dir.iterdir()):
            if path.is_file():
                tar.add(path, arcname=path.name)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    print(BUNDLE_BEGIN, flush=True)
    for start in range(0, len(encoded), 100):
        print(encoded[start:start + 100])
    print(BUNDLE_END, flush=True)


def main(argv: list[str] | None = None) -> int:
    started = time.monotonic()
    parser = argparse.ArgumentParser(description="B0/B2 Apertus run inside an HF GPU job")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("/tmp/uzh-rsd-runs"))
    parser.add_argument("--output-repo", default=None, help="private HF dataset repo for durable results")
    parser.add_argument("--methods", default="b0,b2")
    parser.add_argument("--limit", type=int, default=None, help="first N manifest entries only")
    parser.add_argument("--deadline-min", type=float, default=35.0, help="start no new call after this many minutes")
    parser.add_argument("--device", default="cuda", help="cpu only for local pipeline checks with a tiny model")
    args = parser.parse_args(argv)

    run_dir = args.out / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    uploader = Uploader(args.output_repo, args.run_id)
    meta = {
        "schema": "uzh-rsd.run-meta/v1",
        "run_id": args.run_id,
        "job_id": os.environ.get("JOB_ID"),
        "accelerator": os.environ.get("ACCELERATOR"),
        "source_commit": os.environ.get("UZH_RSD_SOURCE_COMMIT"),
        "bundle_sha256": os.environ.get("UZH_RSD_BUNDLE_SHA256"),
        "started_utc": _now(),
        "methods": args.methods.split(","),
        "prompt_versions": PROMPT_VERSIONS,
        "max_new_tokens": MAX_NEW_TOKENS,
        "limit": args.limit,
        "deadline_min": args.deadline_min,
        "python": sys.version.split()[0],
        "status": "starting",
    }
    meta_path = run_dir / "run_meta.json"

    def save_meta() -> None:
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")
        uploader.push(meta_path)

    try:
        manifest = load_manifest(args.manifest)
        meta["manifest_sha256"] = manifest["manifest_sha256"]
        for language in sorted({entry["pair"].split("-")[1] for entry in manifest["entries"]}):
            fetch_split(manifest["split"], language)
        fetch_prompts()
        items = interleave_languages([inference for inference, _gold in manifest_records(manifest, limit=args.limit)])  # gold dropped here
        meta["documents"] = [item.id for item in items]
        from .backends import TransformersBackend

        backend = TransformersBackend(args.model, args.revision, device=args.device)
        meta["backend"] = backend.describe()
        meta["status"] = "running"
        save_meta()
        raw_path = run_dir / "raw.jsonl"

        def after_call(record: dict) -> None:
            generation = record.get("generation") or {}
            print(f"[{time.monotonic() - started:7.1f}s] {record['method']} {record['id']} {record['status']} "
                  f"tokens={generation.get('completion_tokens')} finish={generation.get('finish_reason')} "
                  f"latency={generation.get('latency_s')}", flush=True)
            uploader.push(raw_path)

        counts = run_inference(backend, items, [m for m in args.methods.split(",") if m in METHODS], raw_path, run_id=args.run_id,
                               deadline=started + args.deadline_min * 60, after_call=after_call)
        meta.update(status="finished", counts=counts)
    except Exception as error:
        meta.update(status="error", error=f"{type(error).__name__}: {str(error)[:500]}")
        traceback.print_exc()
    meta["finished_utc"] = _now()
    meta["elapsed_s"] = round(time.monotonic() - started, 1)
    meta["upload_failures"] = uploader.failures
    save_meta()
    if (run_dir / "raw.jsonl").exists():
        uploader.push(run_dir / "raw.jsonl")
    print_bundle(run_dir)
    print(json.dumps({k: meta.get(k) for k in ("run_id", "status", "counts", "elapsed_s", "upload_failures", "error")}), flush=True)
    return 0 if meta["status"] == "finished" else 1


if __name__ == "__main__":
    sys.exit(main())
