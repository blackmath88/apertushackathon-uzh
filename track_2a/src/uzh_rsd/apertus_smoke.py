"""Opt-in single-request Apertus readiness check.

Reads the Hack Apertus standard variables ``LLM_NAME``, ``LLM_BASE_URL`` and
``LLM_API_KEY`` (OpenAI-compatible chat completions). Sends exactly one
request, no automatic retry, and writes a record that never contains the key,
the authorization header or URL credentials/query strings.

Outcomes:
  PASS              the endpoint answered and the returned model id names Apertus
                    and matches LLM_NAME
  BLOCKED           configuration missing or --confirm-live not given; no request sent
  IDENTITY_MISMATCH the endpoint answered with a different / non-Apertus model id
  FAILED            HTTP error, timeout, transport failure or malformed response

A mocked endpoint can exercise this code, but the record's ``endpoint_kind``
is then ``mock`` and it never counts as live readiness evidence.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from .data_adapter import TRACK_ROOT

REQUIRED_ENV = ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY")
SMOKE_PROMPT = (
    'Reply with a JSON object only: {"model_family": "<your model family>", '
    '"language_check": "<the German word for \'difference\'>"}'
)
DEFAULT_SETTINGS = {"max_tokens": 64, "temperature": 0.0, "timeout_s": 60.0, "max_attempts": 1}
DEFAULT_RUNS_DIR = TRACK_ROOT / "runs"
EXIT_CODES = {"PASS": 0, "FAILED": 1, "BLOCKED": 3, "IDENTITY_MISMATCH": 4}


def safe_endpoint(base_url: str) -> str:
    """scheme://host[:port]/path with userinfo, query and fragment removed."""
    parts = urllib.parse.urlsplit(base_url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urllib.parse.urlunsplit((parts.scheme, host, parts.path.rstrip("/"), "", ""))


def _chat_url(base_url: str) -> str:
    """Request URL; URL userinfo is dropped (auth goes only in the Bearer header)."""
    parts = urllib.parse.urlsplit(base_url)
    netloc = parts.netloc.rsplit("@", 1)[-1]
    path = parts.path.rstrip("/") + "/chat/completions"
    return urllib.parse.urlunsplit((parts.scheme, netloc, path, parts.query, ""))


def _base_record(env: Mapping[str, str], settings: Mapping[str, object], endpoint_kind: str) -> dict:
    return {
        "schema": "uzh-rsd.apertus-smoke/v1",
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "endpoint_kind": endpoint_kind,
        "endpoint": safe_endpoint(env["LLM_BASE_URL"]) if env.get("LLM_BASE_URL") else None,
        "model_requested": env.get("LLM_NAME") or None,
        "settings": dict(settings),
        "attempts": 0,
        "prompt_sha256": hashlib.sha256(SMOKE_PROMPT.encode()).hexdigest(),
    }


def identity_ok(requested: str, returned: str | None) -> bool:
    if not returned or "apertus" not in returned.lower():
        return False
    return returned == requested or returned.rsplit("/", 1)[-1] == requested.rsplit("/", 1)[-1]


def run_smoke(
    env: Mapping[str, str] | None = None,
    *,
    confirm_live: bool = False,
    endpoint_kind: str = "live",
    settings: Mapping[str, object] | None = None,
    opener: Callable[..., object] = urllib.request.urlopen,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    env = dict(os.environ if env is None else env)
    settings = {**DEFAULT_SETTINGS, **(settings or {})}
    if settings["max_attempts"] != 1:
        raise ValueError("S1 smoke allows exactly one attempt; retries need approved runtime configuration")
    record = _base_record(env, settings, endpoint_kind)
    missing = [name for name in REQUIRED_ENV if not env.get(name)]
    if missing:
        record.update(status="BLOCKED", reason=f"missing environment variables: {missing}")
        return record
    if not confirm_live:
        record.update(status="BLOCKED", reason="live request not confirmed; pass --confirm-live")
        return record

    body = json.dumps(
        {
            "model": env["LLM_NAME"],
            "messages": [{"role": "user", "content": SMOKE_PROMPT}],
            "max_tokens": settings["max_tokens"],
            "temperature": settings["temperature"],
        }
    ).encode()
    request = urllib.request.Request(
        _chat_url(env["LLM_BASE_URL"]),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {env['LLM_API_KEY']}"},
    )
    record["attempts"] = 1
    started = clock()
    try:
        with opener(request, timeout=float(settings["timeout_s"])) as response:  # type: ignore[operator]
            status_code = getattr(response, "status", None)
            raw = response.read()
    except urllib.error.HTTPError as error:
        record.update(status="FAILED", reason=f"HTTP {error.code}", http_status=error.code, latency_s=round(clock() - started, 3))
        return record
    except (TimeoutError, socket.timeout):
        record.update(status="FAILED", reason="timeout", latency_s=round(clock() - started, 3))
        return record
    except (urllib.error.URLError, OSError) as error:
        reason = getattr(error, "reason", error)
        record.update(status="FAILED", reason=f"transport error: {type(reason).__name__}", latency_s=round(clock() - started, 3))
        return record
    record["latency_s"] = round(clock() - started, 3)
    record["http_status"] = status_code
    record["response_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw)
        choice = payload["choices"][0]
        content = choice["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        record.update(status="FAILED", reason="malformed chat completion response")
        return record
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else None
    record.update(
        model_returned=payload.get("model"),
        system_fingerprint=payload.get("system_fingerprint"),
        finish_reason=choice.get("finish_reason"),
        usage={k: usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")} if usage else "unavailable",
        completion_text=str(content)[:500],
    )
    if identity_ok(env["LLM_NAME"], payload.get("model")):
        record["status"] = "PASS" if endpoint_kind == "live" else "MOCK_PASS"
    else:
        record.update(status="IDENTITY_MISMATCH", reason="returned model id does not name Apertus or differs from LLM_NAME")
    return record


def write_record(record: Mapping[str, object], runs_dir: Path = DEFAULT_RUNS_DIR) -> Path:
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = str(record["timestamp_utc"]).replace(":", "").replace("+0000", "Z")
    path = runs_dir / f"s1-apertus-smoke-{stamp}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    return path
