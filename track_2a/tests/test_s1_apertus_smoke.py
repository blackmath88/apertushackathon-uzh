"""S1-RUNTIME plumbing tests against a local MOCK endpoint.

These prove request shape, redaction, single-attempt and failure accounting.
They do NOT establish live Apertus readiness: mock results are labelled
``endpoint_kind="mock"`` and can only reach status ``MOCK_PASS``.
"""

import http.server
import json
import threading
import unittest
import urllib.request

from uzh_rsd.apertus_smoke import identity_ok, run_smoke, safe_endpoint

SECRET = "sk-test-SECRET-should-never-appear"
NO_PROXY_OPEN = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


class MockEndpoint(http.server.BaseHTTPRequestHandler):
    behaviour = {}
    requests = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        MockEndpoint.requests.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(length))})
        mode = MockEndpoint.behaviour.get("mode", "ok")
        if mode == "error":
            self.send_response(500)
            self.end_headers()
            return
        if mode == "slow":
            threading.Event().wait(1.5)
        body = MockEndpoint.behaviour.get("body") or {
            "model": MockEndpoint.behaviour.get("model", "swiss-ai/Apertus-v1.5-8B"),
            "choices": [{"message": {"role": "assistant", "content": '{"model_family": "Apertus"}'}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 40, "completion_tokens": 9, "total_tokens": 49},
        }
        payload = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            pass

    def log_message(self, *args):
        pass


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockEndpoint)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://user:pw@127.0.0.1:{cls.server.server_port}/v1?token=leak"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        MockEndpoint.behaviour = {}
        MockEndpoint.requests = []
        self.env = {"LLM_NAME": "swiss-ai/Apertus-v1.5-8B", "LLM_BASE_URL": self.base, "LLM_API_KEY": SECRET}

    def run_mock(self, **kwargs):
        record = run_smoke(self.env, confirm_live=True, endpoint_kind="mock", opener=NO_PROXY_OPEN, **kwargs)
        self.assertNotIn(SECRET, json.dumps(record))
        self.assertNotIn("pw", record.get("endpoint") or "")
        self.assertNotIn("token=leak", json.dumps(record))
        return record

    def test_mock_success_records_identity_usage_latency_but_is_not_live(self):
        record = self.run_mock()
        self.assertEqual(record["status"], "MOCK_PASS")
        self.assertEqual(record["endpoint_kind"], "mock")
        self.assertEqual(record["model_returned"], "swiss-ai/Apertus-v1.5-8B")
        self.assertEqual(record["usage"]["total_tokens"], 49)
        self.assertEqual(record["attempts"], 1)
        self.assertIn("latency_s", record)
        self.assertEqual(len(MockEndpoint.requests), 1)
        sent = MockEndpoint.requests[0]
        self.assertEqual(sent["path"], "/v1/chat/completions?token=leak")
        self.assertEqual(sent["auth"], f"Bearer {SECRET}")
        self.assertEqual(sent["body"]["temperature"], 0.0)

    def test_missing_configuration_blocks_without_request(self):
        for name in ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY"):
            env = dict(self.env)
            env.pop(name)
            record = run_smoke(env, confirm_live=True, opener=NO_PROXY_OPEN)
            self.assertEqual(record["status"], "BLOCKED")
            self.assertIn(name, record["reason"])
            self.assertEqual(record["attempts"], 0)
        self.assertEqual(MockEndpoint.requests, [])

    def test_without_confirmation_no_request_is_sent(self):
        record = run_smoke(self.env, confirm_live=False, opener=NO_PROXY_OPEN)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertEqual(MockEndpoint.requests, [])

    def test_identity_mismatch(self):
        MockEndpoint.behaviour = {"model": "meta-llama/Llama-3.1-8B-Instruct"}
        self.assertEqual(self.run_mock()["status"], "IDENTITY_MISMATCH")

    def test_http_error_is_single_attempt_failure(self):
        MockEndpoint.behaviour = {"mode": "error"}
        record = self.run_mock()
        self.assertEqual((record["status"], record["http_status"], record["attempts"]), ("FAILED", 500, 1))
        self.assertEqual(len(MockEndpoint.requests), 1)

    def test_timeout_is_explicit_failure(self):
        MockEndpoint.behaviour = {"mode": "slow"}
        record = self.run_mock(settings={"timeout_s": 0.3})
        self.assertEqual((record["status"], record["reason"]), ("FAILED", "timeout"))
        self.assertEqual(record["attempts"], 1)

    def test_malformed_response(self):
        MockEndpoint.behaviour = {"body": b"not json"}
        self.assertEqual(self.run_mock()["reason"], "malformed chat completion response")

    def test_missing_usage_is_recorded_as_unavailable(self):
        MockEndpoint.behaviour = {"body": {"model": "swiss-ai/Apertus-v1.5-8B", "choices": [{"message": {"content": "{}"}}]}}
        self.assertEqual(self.run_mock()["usage"], "unavailable")

    def test_retries_require_approved_configuration(self):
        with self.assertRaises(ValueError):
            run_smoke(self.env, confirm_live=True, settings={"max_attempts": 3}, opener=NO_PROXY_OPEN)


class HelperTests(unittest.TestCase):
    def test_safe_endpoint_strips_credentials_and_query(self):
        self.assertEqual(safe_endpoint("https://u:p@api.example.ch:8443/v1/?key=x#frag"), "https://api.example.ch:8443/v1")

    def test_identity_rules(self):
        self.assertTrue(identity_ok("swiss-ai/Apertus-v1.5-70B", "swiss-ai/Apertus-v1.5-70B"))
        self.assertTrue(identity_ok("swiss-ai/Apertus-v1.5-8B", "Apertus-v1.5-8B"))
        self.assertFalse(identity_ok("swiss-ai/Apertus-v1.5-8B", "swiss-ai/Apertus-v1.5-70B"))
        self.assertFalse(identity_ok("my-alias", "gpt-4o"))
        self.assertFalse(identity_ok("swiss-ai/Apertus-v1.5-8B", None))


if __name__ == "__main__":
    unittest.main()
