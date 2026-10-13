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

    def push(self, path: Path, relative: str | None = None) -> None:
        if self.api is None:
            return
        name = relative or path.name
        try:
            self.api.upload_file(path_or_fileobj=str(path), path_in_repo=f"{self.prefix}/{name}", repo_id=self.repo,
                                 repo_type="dataset", commit_message=f"{self.prefix}: {name}")
        except Exception as error:  # keep running; the log bundle is the fallback
            self.failures += 1
            print(f"upload failed ({type(error).__name__}); continuing", flush=True)


def print_bundle(run_dir: Path, flatten_subdirs: bool = False) -> None:
    """Fallback copy in the (account-private) job log. ``flatten_subdirs`` stores
    ``sub/name`` as ``sub__name`` so the flat-only log decoder accepts it."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        paths = sorted(run_dir.rglob("*")) if flatten_subdirs else sorted(run_dir.iterdir())
        for path in paths:
            if path.is_file():
                tar.add(path, arcname="__".join(path.relative_to(run_dir).parts))
    encoded = base64.b64encode(buffer.getvalue()).decode()
    print(BUNDLE_BEGIN, flush=True)
    for start in range(0, len(encoded), 100):
        print(encoded[start:start + 100])
    print(BUNDLE_END, flush=True)


def final_main(args, started: float, backend_factory=None) -> int:
    """Final B2 inference in the job: no manifest, no dev fetch, no prompts fetch, no scoring.

    Delegates to ``uzh_rsd.final`` (contract gate, gold-blind input, frozen B2,
    completion metadata) with the pinned TransformersBackend. Uploads ``raw.jsonl``
    after every call and every run file at the end to ``runs/<run_id>/final/``.
    """
    from . import final

    run_dir = args.out / args.run_id
    out_dir = run_dir / "final"
    run_dir.mkdir(parents=True, exist_ok=True)
    uploader = Uploader(args.output_repo, args.run_id)

    def factory(timeout_s):
        if backend_factory is not None:
            return backend_factory(timeout_s)
        from .backends import TransformersBackend
        return TransformersBackend(args.model, args.revision, device=args.device)

    def after_call(record: dict) -> None:
        generation = record.get("generation") or {}
        # ids, status and counts only: never prompt or response text in the log line
        print(f"[{time.monotonic() - started:7.1f}s] {record['method']} {record['id']} {record['status']} "
              f"tokens={generation.get('completion_tokens')} finish={generation.get('finish_reason')} "
              f"latency={generation.get('latency_s')}", flush=True)
        uploader.push(out_dir / "raw.jsonl", "final/raw.jsonl")

    extra = {"job": {"job_id": os.environ.get("JOB_ID"), "accelerator": os.environ.get("ACCELERATOR"),
                     "bundle_sha256": os.environ.get("UZH_RSD_BUNDLE_SHA256"), "source_commit": os.environ.get("UZH_RSD_SOURCE_COMMIT"),
                     "python": sys.version.split()[0]}}
    if os.environ.get("UZH_RSD_SOURCE_COMMIT"):
        os.environ.setdefault("UZH_SOURCE_COMMIT", os.environ["UZH_RSD_SOURCE_COMMIT"].removesuffix("-dirty"))
        os.environ.setdefault("UZH_SOURCE_DIRTY", "true" if os.environ["UZH_RSD_SOURCE_COMMIT"].endswith("-dirty") else "false")
    code = 1
    try:
        code = final.main(["--contract", str(args.final_contract), "--input", str(args.final_input), "--out", str(out_dir)],
                          backend_factory=factory, after_call=after_call, extra_meta=extra)
    except BaseException:  # noqa: BLE001 - report, then still upload whatever exists
        traceback.print_exc()
    finally:
        if out_dir.exists():
            for path in sorted(out_dir.rglob("*")):
                if path.is_file():
                    uploader.push(path, "final/" + "/".join(path.relative_to(out_dir).parts))
            print_bundle(out_dir, flatten_subdirs=True)
    print(json.dumps({"run_id": args.run_id, "final_exit": code, "elapsed_s": round(time.monotonic() - started, 1),
                      "upload_failures": uploader.failures}), flush=True)
    return code


def main(argv: list[str] | None = None, *, backend_factory=None) -> int:
    started = time.monotonic()
    parser = argparse.ArgumentParser(description="B0/B2 Apertus run inside an HF GPU job")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--manifest", type=Path, default=None, help="pilot mode: dev manifest")
    parser.add_argument("--final-contract", type=Path, default=None, help="final mode: contract JSON (with --final-input)")
    parser.add_argument("--final-input", type=Path, default=None, help="final mode: gold-blind input JSONL")
    parser.add_argument("--out", type=Path, default=Path("/tmp/uzh-rsd-runs"))
    parser.add_argument("--output-repo", default=None, help="private HF dataset repo for durable results")
    parser.add_argument("--methods", default="b0,b2")
    parser.add_argument("--limit", type=int, default=None, help="first N manifest entries only")
    parser.add_argument("--deadline-min", type=float, default=35.0, help="start no new call after this many minutes")
    parser.add_argument("--device", default="cuda", help="cpu only for local pipeline checks with a tiny model")
    args = parser.parse_args(argv)

    if args.final_contract or args.final_input:
        if not (args.final_contract and args.final_input) or args.manifest:
            parser.error("final mode needs --final-contract and --final-input, and no --manifest")
        return final_main(args, started, backend_factory)
    if args.manifest is None:
        parser.error("pilot mode needs --manifest")

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
