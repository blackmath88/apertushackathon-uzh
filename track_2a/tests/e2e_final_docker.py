"""Synthetic end-to-end check of the final path through Docker (not part of unittest discovery: needs Docker).

official-shaped synthetic JSONL → `python -m uzh_rsd.final_input` → confirmed *synthetic* contract →
root `make run MODE=final` (Docker) → local mock OpenAI-compatible endpoint on the host →
predictions + final_meta.json on the host → `python -m uzh_rsd.final --verify`.

No real data, no real model, no network beyond the host loopback.
Run from track_2a/: PYTHONPATH=src .venv/bin/python tests/e2e_final_docker.py
"""

import datetime as dt
import hashlib
import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

TRACK = Path(__file__).resolve().parents[1]
ROOT = TRACK.parent
SENTINEL_LABEL = 0.27182818284
SENTINEL_TEXT = "E2E-UNTOKENIZED-SENTINEL-beef"
DOCS = [  # (language, index, tokenized text_a, tokenized text_b, mock response)
    ("de", 11, "The fee is 30 francs .", "Die Gebühr beträgt 60 Franken .", [{"a": "30 francs", "b": "60 Franken", "kind": "CHANGE", "severity": 5}]),
    ("de", 4, "Forms are online .", "Formulare sind online .", []),
    ("fr", 11, "Contact us by email .", "Contactez-nous par courriel ou téléphone .", [{"a": "", "b": "ou téléphone", "kind": "ADDITION", "severity": 3}]),
    ("it", 2, "The office opens at nine .", "L' ufficio apre alle dieci .", [{"a": "nine", "b": "dieci", "kind": "CHANGE", "severity": 4}]),
]


def row(language, index, text_a, text_b):
    return {"text_a": text_a, "text_a_untokenized": SENTINEL_TEXT, "text_b": text_b, "text_b_untokenized": SENTINEL_TEXT,
            "labels_a": [SENTINEL_LABEL] * len(text_a.split()), "labels_b": [SENTINEL_LABEL] * len(text_b.split()),
            "page_en": "https://example.invalid/en", "page_other": "https://example.invalid/x", "subset": "synthetic",
            "id": f"admin_{language}_{index}"}


class Mock(http.server.BaseHTTPRequestHandler):
    prompts = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = body["messages"][-1]["content"]
        Mock.prompts.append(prompt)
        doc = next(d for d in DOCS if d[3] in prompt)
        data = json.dumps({"choices": [{"message": {"content": json.dumps({"differences": doc[4]})}, "finish_reason": "stop"}],
                           "usage": {"prompt_tokens": 11, "completion_tokens": 7}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def make_run(env, **final):
    args = ["make", "-s", "-C", str(ROOT), "run", "MODE=final"] + [f"{k}={v}" for k, v in final.items()]
    return subprocess.run(args, capture_output=True, text=True, env=env)


def main() -> int:
    work = TRACK / "final_runs" / ("e2e-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    sources = work / "official_shaped"
    sources.mkdir(parents=True)
    source_args = []
    for language in ("de", "fr", "it"):
        path = sources / f"test_{language}.jsonl"
        path.write_text("".join(json.dumps(row(*d[:4]), ensure_ascii=False) + "\n" for d in DOCS if d[0] == language), encoding="utf-8")
        source_args += ["--source", f"{language}={path}"]
    py = [sys.executable, "-m"]
    env = {**os.environ, "PYTHONPATH": str(TRACK / "src")}
    conv = subprocess.run(py + ["uzh_rsd.final_input", *source_args, "--out", str(work / "prepared")], capture_output=True, text=True, env=env)
    assert conv.returncode == 0, conv.stdout + conv.stderr
    draft = json.loads((work / "prepared" / "contract.draft.json").read_text())
    confirmed = dict(draft, status="confirmed", evidence="SYNTHETIC E2E ONLY - not an organiser decision",
                     decisions={"full_set_order": "synthetic", "dropped_ids": "synthetic", "output_layout": "per_language_jsonl"})
    (work / "contract.synthetic.json").write_text(json.dumps(confirmed, indent=2))

    # Docker Desktop uses host.docker.internal. Linux uses host networking so
    # this loopback-only synthetic server never has to be exposed externally.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    linux = sys.platform.startswith("linux")
    endpoint_host = "127.0.0.1" if linux else "host.docker.internal"
    run_env = {**os.environ, "LLM_NAME": "mock-apertus", "LLM_BASE_URL": f"http://{endpoint_host}:{server.server_port}/v1",
               "LLM_API_KEY": "e2e-dummy-key"}
    docker_args = {"FINAL_DOCKER_ARGS": "--network host"} if linux else {}
    out_dir = work / "out"
    checks = {}
    try:
        blocked = make_run(run_env, FINAL_CONTRACT=work / "prepared" / "contract.draft.json", FINAL_INPUT=work / "prepared" / "final_input.jsonl",
                           FINAL_OUT_DIR=out_dir, FINAL_RUN_ID="should-not-exist", **docker_args)
        checks["unresolved_draft_blocked_in_docker"] = blocked.returncode != 0 and '"BLOCKED"' in blocked.stdout \
            and not (out_dir / "should-not-exist").exists() and not Mock.prompts
        good = make_run(run_env, FINAL_CONTRACT=work / "contract.synthetic.json", FINAL_INPUT=work / "prepared" / "final_input.jsonl",
                        FINAL_OUT_DIR=out_dir, FINAL_RUN_ID="synthetic-1", FINAL_ARGS="--timeout-s 10", **docker_args)
        checks["docker_final_exit_0"] = good.returncode == 0
        again = make_run(run_env, FINAL_CONTRACT=work / "contract.synthetic.json", FINAL_INPUT=work / "prepared" / "final_input.jsonl",
                         FINAL_OUT_DIR=out_dir, FINAL_RUN_ID="synthetic-1", **docker_args)
        checks["rerun_same_id_refused"] = again.returncode != 0 and "never overwrite" in again.stdout
    finally:
        server.shutdown()
        server.server_close()

    run = out_dir / "synthetic-1"
    verify = subprocess.run(py + ["uzh_rsd.final", "--verify", str(run)], capture_output=True, text=True, env=env)
    checks["verify_accepted"] = verify.returncode == 0 and json.loads(verify.stdout)["status"] == "accepted"
    meta = json.loads((run / "final_meta.json").read_text())
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    checks["source_commit_from_host"] = meta["source"]["commit"] == head and meta["source"]["source"].startswith("declared by host") \
        and meta["source"]["src_dirty"] is False
    checks["input_sha256_matches"] = meta["input"]["sha256"] == hashlib.sha256((work / "prepared" / "final_input.jsonl").read_bytes()).hexdigest()
    checks["contract_sha256_matches"] = meta["contract"]["sha256"] == hashlib.sha256((work / "contract.synthetic.json").read_bytes()).hexdigest()
    expected_order = [f"admin_{d[0]}_{d[1]}" for d in DOCS]
    checks["order_recorded"] = meta["input"]["order"] == expected_order
    lengths_ok, ids = True, []
    for language in ("de", "fr", "it"):
        for line in (run / "predictions" / f"predictions_{language}.jsonl").read_text().splitlines():
            record = json.loads(line)
            ids.append(record["id"])
            source = next(d for d in DOCS if f"admin_{d[0]}_{d[1]}" == record["id"])
            lengths_ok &= len(record["labels_a"]) == len(source[2].split()) and len(record["labels_b"]) == len(source[3].split())
    checks["all_ids_in_order"] = ids == expected_order
    checks["vector_lengths_match_official_tokens"] = lengths_ok
    checks["mock_called_once_per_document"] = len(Mock.prompts) == len(DOCS)
    blob = "\n".join(Mock.prompts) + "".join(p.read_text() for p in run.rglob("*") if p.is_file())
    checks["no_sentinel_or_key_leak"] = str(SENTINEL_LABEL) not in blob and SENTINEL_TEXT not in blob and "e2e-dummy-key" not in blob
    checks["host_owned_outputs"] = all(p.stat().st_uid == os.getuid() for p in run.rglob("*"))
    summary = {"work_dir": str(work), "checks": checks, "all_passed": all(checks.values()),
               "prediction_files": meta.get("prediction_files"), "source": meta["source"], "status": meta["status"]}
    print(json.dumps(summary, indent=2))
    if not summary["all_passed"]:
        print(good.stdout[-2000:], good.stderr[-2000:], file=sys.stderr)
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
