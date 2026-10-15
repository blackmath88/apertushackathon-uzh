"""Launch and collect the B0/B2 run on Hugging Face batch GPU compute.

Runs on the owner's machine, where ``hf auth login`` already stored a token.
The token is read with ``huggingface_hub.get_token()``, passed only as the
``HF_TOKEN`` job secret, and never printed or written.

Spend control: every launch appends to ``runs/compute_ledger.jsonl``. A launch
is refused when the ledger's committed spend (actual cost where known, else
the timeout ceiling) plus this job's timeout ceiling exceeds ``--budget-usd``.
Nothing is ever retried automatically (``attempts=1``).

    python -m uzh_rsd.hf_launch launch --dry-run          # bundle + private repo upload, no GPU
    python -m uzh_rsd.hf_launch launch --confirm-spend    # one GPU job
    python -m uzh_rsd.hf_launch collect --run-id <id> --wait
    python -m uzh_rsd.hf_launch spend
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from .data_adapter import TRACK_ROOT
from .hf_job import BUNDLE_BEGIN, BUNDLE_END

MODEL_ID = "swiss-ai/Apertus-v1.5-8B"
MODEL_REVISION = "a411d838600baf0e3635a3daf66fb7c55fc97bb6"
IMAGE = "ghcr.io/swiss-ai/vllm_apertus_1.5_release:latest-amd64"
FLAVOR = "l40sx1"
DOCUMENTED_USD_PER_MIN = 0.03  # HF Jobs docs, l40sx1 $1.80/h (checked 2026-10-11)
DEFAULT_REPO_NAME = "uzh-rsd-runs"
RUNS_DIR = TRACK_ROOT / "runs"
LEDGER = RUNS_DIR / "compute_ledger.jsonl"
MANIFEST = TRACK_ROOT / "manifests" / "s1-dev.json"

BOOT = """\
import hashlib, os, sys, tarfile
from huggingface_hub import hf_hub_download
path = hf_hub_download(os.environ["UZH_RSD_REPO"], os.environ["UZH_RSD_BUNDLE_PATH"], repo_type="dataset")
if hashlib.sha256(open(path, "rb").read()).hexdigest() != os.environ["UZH_RSD_BUNDLE_SHA256"]:
    sys.exit("bundle sha256 mismatch")
with tarfile.open(path) as tar:
    try:
        tar.extractall("/tmp/uzh", filter="data")
    except TypeError:
        tar.extractall("/tmp/uzh")
sys.path.insert(0, "/tmp/uzh/src")
os.chdir("/tmp/uzh")
from uzh_rsd.hf_job import main
sys.exit(main(sys.argv[1:]))
"""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def build_bundle(extra: dict[str, bytes] | None = None) -> bytes:
    """Deterministic tar.gz of the package and the manifest (no data, no gold).

    ``extra`` maps bundle paths to bytes (final mode: the contract and the gold-blind input)."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
        files = sorted((TRACK_ROOT / "src" / "uzh_rsd").glob("*.py")) + [MANIFEST]
        entries = [(str(path.relative_to(TRACK_ROOT)), path.read_bytes()) for path in files] + sorted((extra or {}).items())
        for name, data in entries:
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def read_ledger(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def committed_usd(entries: list[dict]) -> float:
    """Actual cost where collected, otherwise the job's timeout ceiling."""
    total = 0.0
    for entry in entries:
        actual = entry.get("actual_usd")
        total += float(actual) if actual is not None else float(entry["max_usd"])
    return round(total, 4)


def check_budget(entries: list[dict], new_max_usd: float, budget_usd: float) -> tuple[bool, float]:
    committed = committed_usd(entries)
    return committed + new_max_usd <= budget_usd + 1e-9, committed


def _append_ledger(entry: dict, path: Path = LEDGER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def _rewrite_ledger(entries: list[dict], path: Path = LEDGER) -> None:
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries))


def _price_per_min(api) -> tuple[float, str]:
    try:
        for hardware in api.list_jobs_hardware():
            if hardware.name == FLAVOR:
                unit = float(hardware.unit_cost_usd)
                label = str(hardware.unit_label or "").lower()
                per_min = unit if "min" in label else unit / 60 if "hour" in label else unit
                return round(per_min, 6), f"hf api ({hardware.unit_cost_usd} per {hardware.unit_label})"
    except Exception as error:
        return DOCUMENTED_USD_PER_MIN, f"documented price (api unavailable: {type(error).__name__})"
    return DOCUMENTED_USD_PER_MIN, "documented price (flavor not listed)"


def _git_commit() -> str | None:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=TRACK_ROOT, capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "src", "manifests"], cwd=TRACK_ROOT, capture_output=True, text=True).stdout.strip()
        return commit + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def launch(args) -> int:
    from huggingface_hub import HfApi, get_token

    token = get_token()
    if not token:
        print("No saved Hugging Face token; run `hf auth login` first.", file=sys.stderr)
        return 3
    api = HfApi()
    user = api.whoami()["name"]
    repo = args.output_repo or f"{user}/{DEFAULT_REPO_NAME}"
    per_min, price_source = _price_per_min(api)
    max_usd = round(args.timeout_min * per_min, 4)
    entries = read_ledger()
    allowed, committed = check_budget(entries, max_usd, args.budget_usd)
    print(f"account: {user}; flavor {FLAVOR} at ${per_min}/min ({price_source}); this job's ceiling ${max_usd} "
          f"({args.timeout_min} min); committed so far ${committed}; budget ${args.budget_usd}")
    if not allowed:
        print("REFUSED: budget ceiling would be exceeded.", file=sys.stderr)
        return 4

    bundle = build_bundle()
    digest = hashlib.sha256(bundle).hexdigest()
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{digest[:8]}"
    bundle_path = f"runs/{run_id}/input/bundle.tar.gz"
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    if not api.repo_info(repo, repo_type="dataset").private:
        print(f"REFUSED: {repo} exists and is not private.", file=sys.stderr)
        return 5
    api.upload_file(path_or_fileobj=bundle, path_in_repo=bundle_path, repo_id=repo, repo_type="dataset",
                    commit_message=f"{run_id}: input bundle")
    print(f"uploaded bundle {digest[:12]} to private dataset {repo}/{bundle_path}")

    job_args = ["--run-id", run_id, "--model", MODEL_ID, "--revision", MODEL_REVISION, "--manifest", "manifests/s1-dev.json",
                "--output-repo", repo, "--methods", args.methods, "--deadline-min", str(args.deadline_min)]
    if args.limit is not None:
        job_args += ["--limit", str(args.limit)]
    env = {"UZH_RSD_REPO": repo, "UZH_RSD_BUNDLE_PATH": bundle_path, "UZH_RSD_BUNDLE_SHA256": digest,
           "UZH_RSD_SOURCE_COMMIT": _git_commit() or "unknown", "PYTHONUNBUFFERED": "1"}
    record = {"run_id": run_id, "repo": repo, "bundle_sha256": digest, "image": IMAGE, "flavor": FLAVOR, "timeout_min": args.timeout_min,
              "deadline_min": args.deadline_min, "model": MODEL_ID, "revision": MODEL_REVISION, "job_args": job_args,
              "source_commit": env["UZH_RSD_SOURCE_COMMIT"], "usd_per_min": per_min, "price_source": price_source, "max_usd": max_usd}
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    if args.dry_run or not args.confirm_spend:
        (run_dir / "launch.json").write_text(json.dumps({**record, "launched": False}, indent=2) + "\n")
        print("Dry run: no GPU job started." if args.dry_run else "Not launched: pass --confirm-spend to start the GPU job.")
        return 0

    job = api.run_job(image=IMAGE, command=["python3", "-c", BOOT, *job_args], env=env, secrets={"HF_TOKEN": token},
                      flavor=FLAVOR, timeout=f"{args.timeout_min}m", attempts=1, name=f"uzh-rsd-{run_id[:15].lower()}")
    record.update(launched=True, job_id=job.id, job_url=job.url, launched_utc=_now())
    (run_dir / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
    _append_ledger({"run_id": run_id, "job_id": job.id, "flavor": FLAVOR, "usd_per_min": per_min, "max_usd": max_usd,
                    "launched_utc": record["launched_utc"], "actual_usd": None})
    print(f"launched job {job.id}: {job.url}\nnext: python -m uzh_rsd.hf_launch collect --run-id {run_id} --wait")
    return 0


STARTING_ALLOWANCE_MIN = 2  # billed Starting time before the timeout clock; largest observed pre-start 101 s
FINAL_BUNDLE_CONTRACT = "final/contract.json"
FINAL_BUNDLE_INPUT = "final/input.jsonl"


def final_job_ceiling(timeout_min: int, per_min: float) -> float:
    """Conservative billed bound: Starting allowance plus the full timeout."""
    return round((timeout_min + STARTING_ALLOWANCE_MIN) * per_min, 4)


def final_preflight(args, api=None) -> tuple[int, dict]:
    """Every gate before a final launch; spends nothing. Prints no input text."""
    from . import final

    contract = final.load_contract(args.contract)               # gate: confirmed / owner_approved_provisional
    items = final.load_final_input(args.input, contract)        # gate: gold-blind fields, ids and order
    report = {"documents": len(items), "per_language": {}, "contract_status": contract["status"],
              "contract_sha256": hashlib.sha256(Path(args.contract).read_bytes()).hexdigest(),
              "input_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest(),
              "model": MODEL_ID, "revision": MODEL_REVISION, "flavor": FLAVOR, "timeout_min": args.timeout_min,
              "source_commit": _git_commit()}
    for item in items:
        report["per_language"][item.language] = report["per_language"].get(item.language, 0) + 1
    if api is None:
        return 0, report
    report["account"] = api.whoami()["name"]
    per_min, source = _price_per_min(api)
    report.update(usd_per_min=per_min, price_source=source, job_ceiling_usd=final_job_ceiling(args.timeout_min, per_min))
    entries = read_ledger()
    report["committed_usd"] = max(committed_usd(entries), args.prior_committed_floor_usd)
    active = [job for job in api.list_jobs() if job.status.stage not in {"COMPLETED", "ERROR", "CANCELED", "DELETED"}]
    report["active_jobs"] = [job.id for job in active]
    problems = []
    if report["source_commit"] is None or report["source_commit"].endswith("-dirty"):
        problems.append("source tree is dirty or not a git checkout")
    if report["job_ceiling_usd"] > args.max_job_usd + 1e-9:
        problems.append(f"job ceiling ${report['job_ceiling_usd']} exceeds approved ${args.max_job_usd}")
    if report["committed_usd"] + report["job_ceiling_usd"] > args.budget_usd + 1e-9:
        problems.append(f"cumulative ${report['committed_usd']} + ${report['job_ceiling_usd']} exceeds cap ${args.budget_usd}")
    if active:
        problems.append(f"active jobs on the account: {report['active_jobs']}")
    report["problems"] = problems
    return (0 if not problems else 4), report


def launch_final(args) -> int:
    from huggingface_hub import HfApi, get_token

    token = get_token()
    if not token:
        print("No saved Hugging Face token; run `hf auth login` first.", file=sys.stderr)
        return 3
    api = HfApi()
    code, report = final_preflight(args, api)
    print(json.dumps(report, indent=2))
    if code != 0:
        print("REFUSED: preflight failed.", file=sys.stderr)
        return code
    repo = args.output_repo or f"{report['account']}/{DEFAULT_REPO_NAME}"
    bundle = build_bundle({FINAL_BUNDLE_CONTRACT: Path(args.contract).read_bytes(), FINAL_BUNDLE_INPUT: Path(args.input).read_bytes()})
    digest = hashlib.sha256(bundle).hexdigest()
    run_id = "final-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{digest[:8]}"
    record = {"kind": "final_b2", "run_id": run_id, "repo": repo, "bundle_sha256": digest, "image": IMAGE, "flavor": FLAVOR,
              "timeout_min": args.timeout_min, "model": MODEL_ID, "revision": MODEL_REVISION, **{k: report[k] for k in (
                  "documents", "per_language", "contract_status", "contract_sha256", "input_sha256", "source_commit",
                  "usd_per_min", "price_source", "committed_usd")}, "max_usd": report["job_ceiling_usd"],
              "max_job_usd_approved": args.max_job_usd, "budget_usd": args.budget_usd}
    run_dir = RUNS_DIR / run_id
    if not args.confirm_spend:
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "launch.json").write_text(json.dumps({**record, "launched": False}, indent=2) + "\n")
        print("Preflight passed. Not launched: pass --confirm-spend to start exactly one GPU job.")
        return 0
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    if not api.repo_info(repo, repo_type="dataset").private:
        print(f"REFUSED: {repo} exists and is not private.", file=sys.stderr)
        return 5
    bundle_path = f"runs/{run_id}/input/bundle.tar.gz"
    api.upload_file(path_or_fileobj=bundle, path_in_repo=bundle_path, repo_id=repo, repo_type="dataset", commit_message=f"{run_id}: input bundle")
    job_args = ["--run-id", run_id, "--model", MODEL_ID, "--revision", MODEL_REVISION, "--final-contract", FINAL_BUNDLE_CONTRACT,
                "--final-input", FINAL_BUNDLE_INPUT, "--output-repo", repo]
    env = {"UZH_RSD_REPO": repo, "UZH_RSD_BUNDLE_PATH": bundle_path, "UZH_RSD_BUNDLE_SHA256": digest,
           "UZH_RSD_SOURCE_COMMIT": report["source_commit"], "PYTHONUNBUFFERED": "1"}
    run_dir.mkdir(parents=True, exist_ok=False)
    job = api.run_job(image=IMAGE, command=["python3", "-c", BOOT, *job_args], env=env, secrets={"HF_TOKEN": token},
                      flavor=FLAVOR, timeout=f"{args.timeout_min}m", attempts=1, name=f"uzh-final-{digest[:8]}")
    record.update(launched=True, job_id=job.id, job_url=job.url, launched_utc=_now(), job_args=job_args)
    (run_dir / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
    _append_ledger({"kind": "final_b2", "run_id": run_id, "job_id": job.id, "flavor": FLAVOR, "usd_per_min": report["usd_per_min"],
                    "max_usd": report["job_ceiling_usd"], "launched_utc": record["launched_utc"], "actual_usd": None,
                    "basis": f"ceiling = (timeout {args.timeout_min} + starting allowance {STARTING_ALLOWANCE_MIN}) min x price"})
    print(f"launched job {job.id}: {job.url}\nnext: python -m uzh_rsd.hf_launch collect-final --run-id {run_id} --wait")
    return 0


def collect_final(args) -> int:
    """Wait for terminal state, download runs/<id>/final/** (else the log bundle), update the ledger, verify."""
    from huggingface_hub import HfApi, snapshot_download
    from . import final

    run_dir = RUNS_DIR / args.run_id
    record = json.loads((run_dir / "launch.json").read_text())
    api = HfApi()
    job_id = record["job_id"]
    terminal = {"COMPLETED", "ERROR", "CANCELED", "DELETED"}
    info = api.inspect_job(job_id=job_id)
    while args.wait and info.status.stage not in terminal:
        print(f"job {job_id}: {info.status.stage}; waiting…", flush=True)
        time.sleep(60)
        info = api.inspect_job(job_id=job_id)
    print(f"job {job_id}: {info.status.stage} {info.status.message or ''}".strip())
    out_dir = run_dir / "final"
    source = "none"
    try:
        local = snapshot_download(record["repo"], repo_type="dataset", allow_patterns=[f"runs/{args.run_id}/final/**"])
        remote = Path(local, "runs", args.run_id, "final")
        for path in remote.rglob("*"):
            if path.is_file():
                target = out_dir / path.relative_to(remote)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        source = "private dataset repo" if (out_dir / "final_meta.json").exists() else source
    except Exception as error:
        print(f"repo download failed ({type(error).__name__}); trying the job log", file=sys.stderr)
    if source == "none" and info.status.stage in terminal:
        lines = [str(line).rstrip("\n") for line in api.fetch_job_logs(job_id=job_id)]
        flat = run_dir / "log_bundle"
        flat.mkdir(exist_ok=True)
        if _decode_log_bundle(lines, flat):
            for path in flat.iterdir():
                target = out_dir.joinpath(*path.name.split("__"))
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
            source = "job log bundle"
    running = info.durations.running_secs if getattr(info, "durations", None) else None
    if running is None and getattr(info, "started_at", None) and getattr(info, "finished_at", None):
        running = (info.finished_at - info.started_at).total_seconds()
    entries = read_ledger()
    for entry in entries:
        if entry["job_id"] == job_id:
            entry["stage"] = info.status.stage
            if running is not None and info.status.stage in terminal:
                entry["running_secs"] = running
                entry["actual_usd"] = round((running / 60 + STARTING_ALLOWANCE_MIN) * entry["usd_per_min"], 4)
                entry["actual_basis"] = "running time + starting allowance (upper bound, not an invoice)"
    _rewrite_ledger(entries)
    accepted, reasons = final.verify_run(out_dir) if out_dir.exists() else (False, ["no final output collected"])
    print(json.dumps({"stage": info.status.stage, "source": source, "accepted": accepted, "reasons": reasons,
                      "ledger_committed_usd": committed_usd(entries)}, indent=2))
    return 0 if accepted else 1


def _decode_log_bundle(lines: list[str], run_dir: Path) -> bool:
    try:
        start, end = lines.index(BUNDLE_BEGIN), lines.index(BUNDLE_END)
    except ValueError:
        return False
    data = base64.b64decode("".join(line.strip() for line in lines[start + 1:end]))
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or "/" in member.name or member.name.startswith("."):
                raise ValueError(f"unexpected member {member.name!r} in log bundle")
            (run_dir / member.name).write_bytes(tar.extractfile(member).read())
    return True


def collect(args) -> int:
    from huggingface_hub import HfApi, snapshot_download

    run_dir = RUNS_DIR / args.run_id
    launch_record = json.loads((run_dir / "launch.json").read_text())
    api = HfApi()
    job_id = launch_record["job_id"]
    terminal = {"COMPLETED", "ERROR", "CANCELED", "DELETED"}
    info = api.inspect_job(job_id=job_id)
    while args.wait and info.status.stage not in terminal:
        print(f"job {job_id}: {info.status.stage}; waiting…", flush=True)
        time.sleep(30)
        info = api.inspect_job(job_id=job_id)
    print(f"job {job_id}: {info.status.stage} {info.status.message or ''}".strip())

    source = "none"
    if not args.from_log:
        try:
            local = snapshot_download(launch_record["repo"], repo_type="dataset", allow_patterns=[f"runs/{args.run_id}/*.json*"])
            for path in Path(local, "runs", args.run_id).glob("*.json*"):
                (run_dir / path.name).write_bytes(path.read_bytes())
            source = "private dataset repo" if (run_dir / "raw.jsonl").exists() else source
        except Exception as error:
            print(f"repo download failed ({type(error).__name__}); trying the job log", file=sys.stderr)
    if source == "none" and info.status.stage in terminal:
        lines = [str(line).rstrip("\n") for line in api.fetch_job_logs(job_id=job_id)]
        (run_dir / "job.log").write_text("\n".join(lines) + "\n")
        source = "job log bundle" if _decode_log_bundle(lines, run_dir) else source

    running = info.durations.running_secs if getattr(info, "durations", None) else None
    if running is None and getattr(info, "started_at", None) and getattr(info, "finished_at", None):
        running = (info.finished_at - info.started_at).total_seconds()
    entries = read_ledger()
    for entry in entries:
        if entry["job_id"] == job_id:
            entry["stage"] = info.status.stage
            if running is not None and info.status.stage in terminal:
                entry["running_secs"] = running
                entry["actual_usd"] = round(running / 60 * entry["usd_per_min"], 4)
    _rewrite_ledger(entries)
    print(f"results source: {source}; ledger committed spend ${committed_usd(entries)}")
    if (run_dir / "raw.jsonl").exists():
        print(f"next: make -C track_2a evaluate RUN_ID={args.run_id}")
        return 0
    return 1


def spend(_args) -> int:
    entries = read_ledger()
    for entry in entries:
        print(json.dumps(entry))
    print(f"committed spend (actual where collected, else ceiling): ${committed_usd(entries)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HF Jobs launcher for the UZH B0/B2 run")
    sub = parser.add_subparsers(dest="command", required=True)
    p_launch = sub.add_parser("launch")
    p_launch.add_argument("--dry-run", action="store_true")
    p_launch.add_argument("--confirm-spend", action="store_true")
    p_launch.add_argument("--timeout-min", type=int, default=45)
    p_launch.add_argument("--deadline-min", type=float, default=33.0)
    p_launch.add_argument("--budget-usd", type=float, default=3.0)
    p_launch.add_argument("--limit", type=int, default=None)
    p_launch.add_argument("--methods", default="b0,b2")
    p_launch.add_argument("--output-repo", default=None)
    p_collect = sub.add_parser("collect")
    p_collect.add_argument("--run-id", required=True)
    p_collect.add_argument("--wait", action="store_true")
    p_collect.add_argument("--from-log", action="store_true")
    p_final = sub.add_parser("final", help="final B2 inference: preflight, then exactly one job with --confirm-spend")
    p_final.add_argument("--contract", type=Path, required=True)
    p_final.add_argument("--input", type=Path, required=True)
    p_final.add_argument("--timeout-min", type=int, required=True)
    p_final.add_argument("--max-job-usd", type=float, required=True, help="approved ceiling for this job")
    p_final.add_argument("--budget-usd", type=float, required=True, help="approved cumulative project cap")
    p_final.add_argument("--prior-committed-floor-usd", type=float, default=0.0,
                         help="conservative floor for prior spend if the ledger understates it")
    p_final.add_argument("--confirm-spend", action="store_true")
    p_final.add_argument("--output-repo", default=None)
    p_cfinal = sub.add_parser("collect-final")
    p_cfinal.add_argument("--run-id", required=True)
    p_cfinal.add_argument("--wait", action="store_true")
    sub.add_parser("spend")
    args = parser.parse_args(argv)
    return {"launch": launch, "collect": collect, "spend": spend, "final": launch_final, "collect-final": collect_final}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
