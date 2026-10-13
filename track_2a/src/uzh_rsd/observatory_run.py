"""Single-command local execution with observable preflight and saved attempts.

No service is started automatically and no fallback route is chosen. Model
listing confirms an endpoint's reported ID, not attestation of served weights.
"""
from __future__ import annotations

import copy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

from .observatory import analyze_pair, check_bundle, now, seal
from .observatory_capture import digest, write_new
from .zurich_pilot import NoRedirects


def validate_endpoint(endpoint):
    p = urlsplit(endpoint)
    if (p.scheme != "http" or p.hostname != "127.0.0.1" or p.port != 11436 or
            p.username or p.password or p.query or p.fragment or p.path not in ("", "/v1", "/v1/")):
        raise ValueError("only loopback Apertus on 127.0.0.1:11436 is eligible")
    return "http://127.0.0.1:11436/v1"


def validate_runtime(runtime, gguf=None):
    if (not isinstance(runtime, dict) or runtime.get("model_family") != "Apertus" or
            not re.fullmatch("[0-9a-f]{64}", runtime.get("model_sha256", "")) or
            not isinstance(runtime.get("runtime_revision"), str) or not runtime["runtime_revision"].strip()):
        raise ValueError("runtime pin needs Apertus model SHA-256 and runtime revision")
    result = {**runtime, "weight_identity_assurance": "operator_supplied_not_server_attested"}
    if gguf is not None:
        h = sha256()
        with Path(gguf).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != runtime["model_sha256"]:
            raise ValueError("local GGUF does not match pinned model hash")
        result["local_file_hash_verified"] = True
    return result


def preflight(endpoint, model, runtime, *, opener=None):
    endpoint = validate_endpoint(endpoint)
    validate_runtime(runtime)
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model ID required")
    request = Request(endpoint + "/models", headers={"Accept": "application/json"})
    result = {"schema": "lost-in-switzerland/endpoint-preflight/v1", "checked_at_utc": now(),
              "endpoint": endpoint, "expected_model_id": model,
              "model_calls": 0, "weight_identity_assurance": "operator_supplied_not_server_attested"}
    try:
        with (opener or build_opener(ProxyHandler({}), NoRedirects())).open(request, timeout=5) as response:
            if response.status != 200 or not response.headers.get("Content-Type", "").lower().startswith("application/json"):
                raise ValueError("model-list response is not HTTP 200 JSON")
            raw = response.read(128001)
            if len(raw) > 128000:
                raise ValueError("model-list response too large")
        payload = json.loads(raw)
        result.update(response_sha256=sha256(raw).hexdigest(), response_bytes=len(raw))
        models = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(models, list) or len(models) > 20:
            raise ValueError("invalid model-list shape")
        ids = [m["id"] for m in models if isinstance(m, dict) and isinstance(m.get("id"), str)]
        if model not in ids:
            result.update(status="blocked", reason="expected_model_not_reported", observed_model_ids=ids)
        else:
            result.update(status="ready", reported_model_id=model,
                          scope="endpoint reports requested ID; served GGUF not attested")
    except (OSError, ValueError, TypeError) as exc:
        result.update(status="blocked", reason="endpoint_unavailable_or_invalid", error_type=type(exc).__name__)
    result["record_digest"] = digest(result)
    return result


def checkpoint(root, name, meta):
    """Separate immutable sequence entries; interruption never erases attempts."""
    write_new(root / "events" / name, meta)


def run_local(bundle, root, endpoint, model, runtime, *, probe=preflight, backend_factory=None, gguf=None):
    check_bundle(bundle)
    validate_endpoint(endpoint)
    runtime = validate_runtime(runtime, gguf)
    if not 1 <= len(bundle["pairs"]) <= 5:
        raise ValueError("local-run budget: 1..5 reviewed pairs")
    if any(p["analysis"]["status"] != "not_run" for p in bundle["pairs"]):
        raise ValueError("local-run refuses an already-attempted bundle; no implicit retry")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    bundle = copy.deepcopy(bundle)
    meta = {"schema": "lost-in-switzerland/local-run/v1", "source_bundle_digest": bundle["bundle_digest"],
            "started_at_utc": now(), "state": "preflight", "model_calls": 0,
            "total_pairs": len(bundle["pairs"]), "processed_pairs": 0,
            "budget": {"max_pairs": 5, "max_attempts_per_pair": 1, "timeout_per_call_s": 90,
                       "max_completion_tokens": 1024, "max_input_whitespace_tokens": 2500},
            "runtime": runtime, "endpoint": endpoint, "requested_model": model,
            "model_output_coverage": "not_run", "semantic_coverage": "not_established",
            "human_confirmed_discrepancies": 0}
    checkpoint(root, "000-started.json", meta)
    try:
        observed = probe(endpoint, model, runtime)
    except Exception as exc:
        observed = {"status": "blocked", "reason": "preflight_exception", "error_type": type(exc).__name__}
    write_new(root / "preflight.json", observed)
    if observed["status"] != "ready":
        meta.update(state="blocked", reason=observed.get("reason"), completed_at_utc=now())
        write_new(root / "run.json", meta)
        write_new(root / "bundle.json", bundle)
        _viewer(root, bundle, meta)
        return meta
    if backend_factory is None:
        from .backends import OpenAICompatibleBackend
        backend_factory = OpenAICompatibleBackend
    base_backend = backend_factory(endpoint, model, "local", timeout_s=90,
                                   opener=build_opener(ProxyHandler({}), NoRedirects()).open)
    class TrackedBackend:
        calls = 0
        last_generation = None
        def describe(self): return base_backend.describe()
        def generate(self, prompt, cap):
            self.calls += 1
            self.last_generation = base_backend.generate(prompt, cap)
            return self.last_generation
    backend = TrackedBackend()
    meta["state"] = "running"
    checkpoint(root, "001-preflight-ready.json", meta)
    interrupted = None
    try:
        for index, pair in enumerate(bundle["pairs"]):
            before_calls = backend.calls
            backend.last_generation = None
            intent = {"pair_id": pair["pair_id"], "revision": pair["revision"],
                      "recorded_at_utc": now(), "status": "possibly_attempted_until_settled"}
            checkpoint(root, f"{index+2:03d}-intent.json", intent)
            try:
                pair["analysis"] = analyze_pair(pair, backend, runtime)
            except Exception as exc:
                # Unknown callback failures are unresolved, never repaired/retried.
                pair["analysis"] = {"status": "unresolved", "reason": "attempt_exception",
                                    "error_type": type(exc).__name__, "candidates": [], "model_calls": backend.calls-before_calls,
                                    "attempt_settlement": "returned_exception"}
                generated = backend.last_generation
                if generated is not None and isinstance(getattr(generated, "text", None), str):
                    pair["analysis"].update(raw_text=generated.text, raw_sha256=sha256(generated.text.encode()).hexdigest())
            write_new(root / "attempts" / (pair["pair_id"] + ".json"), pair["analysis"])
            meta["processed_pairs"] += 1
            meta["model_calls"] += pair["analysis"].get("model_calls", 0)
            if pair["analysis"]["status"] == "call_failed" or pair["analysis"].get("reason") == "attempt_exception":
                meta.update(state="incomplete", reason="failed_generation_stop_without_retry")
                break
    except BaseException as exc:
        interrupted = exc
        meta.update(state="incomplete", reason=type(exc).__name__,
                    possibly_attempted_pair=pair["pair_id"])
        if pair["analysis"]["status"] == "not_run":
            pair["analysis"] = {"status": "unresolved", "reason": "interrupted_attempt", "candidates": [],
                                "model_calls": backend.calls-before_calls, "attempt_settlement": "unknown"}
        meta["model_calls"] = backend.calls
    else:
        if meta["state"] != "incomplete":
            meta["state"] = "attempts_completed"
    usable = sum(p["analysis"]["status"] == "ok" and p["analysis"].get("finish_reason") != "length" for p in bundle["pairs"])
    meta.update(model_output_coverage="all_pairs_parseable" if usable == len(bundle["pairs"]) else "partial_or_unresolved",
                parseable_untruncated_pairs=usable, completed_at_utc=now())
    seal(bundle)
    # Incomplete snapshots are inspectable, but never labelled complete acceptance.
    write_new(root / "bundle.json", bundle)
    write_new(root / "run.json", meta)
    _viewer(root, bundle, meta)
    if interrupted is not None:
        raise interrupted
    return meta


def _viewer(root, bundle, meta):
    from .observatory_viewer import render
    with (root / "index.html").open("x", encoding="utf-8") as stream:
        stream.write(render(bundle, run_status=meta))


def serve_viewer(path, port=8765):
    """Read-only loopback view. No model routes, directory listing or mutations."""
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("viewer port must be 1024..65535")
    html = Path(path).read_bytes()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
                self.send_error(403)
                return
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(html)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Evidence desk: http://127.0.0.1:{port}/ (Ctrl-C stops it)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
