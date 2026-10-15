"""Loopback-only HTTP adapter for the approved B8 local execution erratum."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .b8 import (
    REQUIRED_STUDENT,
    _jsonl,
    _read_json,
    _write_json,
    run_bounded_local_only,
)


def _post_loopback(endpoint: str, request: dict) -> dict:
    parsed = urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port != 11436:
        raise PermissionError("B8 HTTP adapter is restricted to http://127.0.0.1:11436")
    payload = {
        "model": "Apertus-v1.5-8B-Q8_0",
        "messages": [
            {"role": "system", "content": request["prompt"]["system"]},
            {"role": "user", "content": request["prompt"]["user"]},
        ],
        "temperature": request["configuration"]["temperature"],
        "seed": request["configuration"]["seed"],
        "max_tokens": request["configuration"]["max_output_tokens"],
        "stream": False,
    }
    http_request = urllib.request.Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(http_request, timeout=120) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"raw_body": raw}
        return {
            "raw_output": "",
            "usage": {},
            "backend_response": body,
            "http_status": exc.code,
            "error": f"HTTPError: {exc.code} {exc.reason}",
        }
    choices = body.get("choices", [])
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    return {
        "raw_output": content,
        "usage": body.get("usage", {}),
        "backend_response": body,
        "http_status": status,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--student-identity", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    protocol = _read_json(args.package / "protocol.json")
    schedule = _jsonl(args.schedule)
    authorization = _read_json(args.authorization)
    student_identity = _read_json(args.student_identity)
    for key, expected in REQUIRED_STUDENT.items():
        if student_identity.get(key) != expected:
            raise PermissionError(f"student identity mismatch: {key}")
    result = run_bounded_local_only(
        protocol,
        schedule,
        args.ledger,
        lambda request: _post_loopback(REQUIRED_STUDENT["endpoint"], request),
        authorization=authorization,
        student_identity=student_identity,
    )
    result.update({"schema": "uzh-rsd.b8-local-execution/v1", "status": "complete"})
    _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
