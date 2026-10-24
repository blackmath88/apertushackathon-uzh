"""Final-inference path, synthetic fixtures only: no dataset, no real model, no network beyond 127.0.0.1."""

import http.server
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from uzh_rsd import cli, data_adapter, evaluation, final
from uzh_rsd.backends import Generation

TRACK = Path(__file__).resolve().parents[1]
SENTINEL = "SENTINEL-GOLD-7f3a9c"
SENTINEL_NUMBER = 0.7777777777

DOCS = [  # deliberately not sorted by id or language: order must come from the contract
    {"id": "syn_it_9", "language": "it", "text_a": "The office opens at nine .", "text_b": "L' ufficio apre alle dieci ."},
    {"id": "syn_de_2", "language": "de", "text_a": "The fee is 30 francs .", "text_b": "Die Gebühr beträgt 60 Franken ."},
    {"id": "syn_fr_5", "language": "fr", "text_a": "Contact us by email .", "text_b": "Contactez-nous par courriel ou par téléphone ."},
    {"id": "syn_de_1", "language": "de", "text_a": "Forms are online .", "text_b": "Formulare sind online ."},
]
B2_RESPONSES = {
    "syn_it_9": {"differences": [{"a": "nine", "b": "dieci", "kind": "CHANGE", "severity": 4}]},
    "syn_de_2": {"differences": [{"a": "30 francs", "b": "60 Franken", "kind": "CHANGE", "severity": 5}]},
    "syn_fr_5": {"differences": [{"a": "", "b": "ou par téléphone", "kind": "ADDITION", "severity": 3}]},
    "syn_de_1": {"differences": []},  # documented B2 behaviour: valid, all-zero vector
}


def contract(**overrides):
    body = {
        "schema": final.CONTRACT_SCHEMA,
        "status": "confirmed",
        "evidence": "synthetic test contract; not an organiser decision",
        "decisions": {"full_set_order": "synthetic", "dropped_ids": "synthetic: none", "output_layout": "per_language_jsonl"},
        "order": [{"id": d["id"], "language": d["language"]} for d in DOCS],
    }
    body.update(overrides)
    return body


class FakeBackend:
    """Deterministic: answers each B2 prompt from B2_RESPONSES by matching the document text."""

    def __init__(self, fail=(), garbage=()):
        self.prompts, self.fail, self.garbage = [], set(fail), set(garbage)

    def describe(self):
        return {"backend": "fake", "model": "fake-model", "max_attempts": 1}

    def generate(self, prompt, max_new_tokens):
        self.prompts.append(prompt)
        doc = next(d for d in DOCS if d["text_b"] in prompt)
        if doc["id"] in self.fail:
            return Generation(None, "timeout", latency_s=1.0)
        if doc["id"] in self.garbage:
            return Generation('{"differences": [{"a": "nine"', finish_reason="length", latency_s=1.0)
        return Generation(json.dumps(B2_RESPONSES[doc["id"]]), finish_reason="stop", latency_s=0.5, completion_tokens=20)


class FinalTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.contract_path = self.write("contract.json", json.dumps(contract()))
        self.input_path = self.write("input.jsonl", "".join(json.dumps(d) + "\n" for d in DOCS))
        self.out = self.tmp / "final_run"
        # Forbidden paths: dataset access, downloads and the official evaluator must never be touched.
        forbidden = mock.Mock(side_effect=AssertionError("forbidden call"))
        self.patches = [mock.patch.object(data_adapter, name, forbidden) for name in ("load_split", "fetch_split")]
        self.patches += [mock.patch.object(evaluation, name, forbidden) for name in ("load_official_compute_correlations", "load_official_function")]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        import shutil
        shutil.rmtree(self.tmp)

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def run_main(self, *extra, backend=None, contract_path=None, input_path=None, out=None):
        argv = ["--contract", str(contract_path or self.contract_path), "--input", str(input_path or self.input_path),
                "--out", str(out or self.out), *extra]
        buffer = io.StringIO()
        factory = (lambda timeout: backend) if backend is not None else None
        with redirect_stdout(buffer):
            code = final.main(argv, backend_factory=factory)
        return code, json.loads(buffer.getvalue())


class ConfigurationTests(FinalTestCase):
    def test_template_contract_in_repo_is_refused_before_io(self):
        backend = FakeBackend()
        code, result = self.run_main(backend=backend, contract_path=TRACK / "final" / "contract.template.json")
        self.assertEqual((code, result["status"]), (final.EXIT_BLOCKED, "BLOCKED"))
        self.assertIn("unresolved", result["reason"])
        self.assertEqual(backend.prompts, [])
        self.assertFalse(self.out.exists())

    def test_unresolved_decision_or_missing_evidence_blocks(self):
        cases = [contract(status="unresolved"), contract(evidence=" "),
                 contract(decisions={"full_set_order": "unresolved", "dropped_ids": "x", "output_layout": "per_language_jsonl"}),
                 contract(decisions={"full_set_order": "x", "dropped_ids": "x", "output_layout": "one_big_csv"}),
                 contract(order=[{"id": "a", "language": "de"}, {"id": "a", "language": "de"}]),
                 contract(schema="other")]
        for body in cases:
            with self.subTest(body=body):
                path = self.write("c.json", json.dumps(body))
                with mock.patch.object(final, "load_final_input", side_effect=AssertionError("input read")):
                    code, result = self.run_main(backend=FakeBackend(), contract_path=path)
                self.assertEqual(code, final.EXIT_BLOCKED)
                self.assertFalse(self.out.exists())

    def test_missing_endpoint_blocks_before_input_or_backend(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(final, "load_final_input", side_effect=AssertionError("input read")):
            code, result = self.run_main()
        self.assertEqual(code, final.EXIT_BLOCKED)
        self.assertIn("LLM_NAME", result["reason"])

    def test_existing_output_or_protected_dir_is_refused(self):
        self.out.mkdir()
        (self.out / "keep.txt").write_text("evidence")
        code, _ = self.run_main(backend=FakeBackend())
        self.assertEqual(code, final.EXIT_BLOCKED)
        self.assertEqual((self.out / "keep.txt").read_text(), "evidence")
        for protected in ("results/new_final", "diagnostics/x", "results"):
            with self.subTest(protected=protected):
                code, result = self.run_main(backend=FakeBackend(), out=TRACK / protected)
                self.assertEqual(code, final.EXIT_BLOCKED)
                self.assertFalse((TRACK / "results" / "new_final").exists())


class InputBoundaryTests(FinalTestCase):
    def test_bundled_gold_fields_are_rejected_without_echoing_values(self):
        for key in ("labels_a", "gold", "annotations", "page_en"):
            with self.subTest(key=key):
                contaminated = [dict(d, **{key: [SENTINEL_NUMBER, SENTINEL]}) if i == 1 else d for i, d in enumerate(DOCS)]
                path = self.write("bad.jsonl", "".join(json.dumps(d) + "\n" for d in contaminated))
                backend = FakeBackend()
                code, result = self.run_main(backend=backend, input_path=path)
                self.assertEqual((code, result["status"]), (final.EXIT_INVALID, "invalid_input"))
                self.assertIn(key, result["reason"])
                self.assertNotIn(SENTINEL, json.dumps(result))
                self.assertEqual(backend.prompts, [])
                self.assertFalse(self.out.exists())

    def test_duplicate_missing_unexpected_and_language_mismatch_are_rejected(self):
        variants = {
            "duplicate": DOCS + [DOCS[0]],
            "missing": DOCS[:-1],
            "unexpected": DOCS + [{"id": "syn_de_99", "language": "de", "text_a": "x", "text_b": "y"}],
            "language": [dict(DOCS[0], language="fr")] + DOCS[1:],
            "empty_text": [dict(DOCS[0], text_b="   ")] + DOCS[1:],
        }
        for name, docs in variants.items():
            with self.subTest(name=name):
                path = self.write("v.jsonl", "".join(json.dumps(d) + "\n" for d in docs))
                backend = FakeBackend()
                code, _ = self.run_main(backend=backend, input_path=path)
                self.assertEqual(code, final.EXIT_INVALID)
                self.assertEqual(backend.prompts, [])

    def test_smoke_clean_run_artifacts_contain_no_sentinel(self):
        # Smoke check only: the gold-blindness guarantees are the field-rejection tests and the
        # patched load_split/fetch_split above. A stray labels file next to the input must stay unused.
        self.write("labels.json", json.dumps({d["id"]: [SENTINEL_NUMBER] for d in DOCS}))
        backend = FakeBackend()
        code, _ = self.run_main(backend=backend)
        self.assertEqual(code, final.EXIT_OK)
        blob = "\n".join(backend.prompts) + "".join(p.read_text() for p in self.out.rglob("*") if p.is_file())
        self.assertNotIn(SENTINEL, blob)
        self.assertNotIn(str(SENTINEL_NUMBER), blob)
        self.assertNotIn("label", "\n".join(backend.prompts).lower())


class ExecutionTests(FinalTestCase):
    def test_windowed_v2_runs_through_final_contract_and_records_completion_policy(self):
        backend = FakeBackend()
        code, result = self.run_main("--method", "b2-windowed-v2", backend=backend)
        self.assertEqual((code, result["status"]), (final.EXIT_OK, "complete"))
        meta = json.loads((self.out / "final_meta.json").read_text())
        self.assertEqual(meta["strategy"]["method"], "b2-windowed-v2")
        self.assertIn("explicit empty differences", meta["strategy"]["completion"])
        self.assertEqual(meta["counts"]["complete_documents"], len(DOCS))
        self.assertTrue((self.out / "window-ledger.jsonl").exists())

    def test_valid_run_preserves_contract_order_and_records_provenance(self):
        backend = FakeBackend()
        code, result = self.run_main(backend=backend)
        self.assertEqual((code, result["status"]), (final.EXIT_OK, "complete"))
        meta = json.loads((self.out / "final_meta.json").read_text())
        self.assertEqual(meta["status"], "complete")
        self.assertEqual(meta["strategy"]["prompt_version"], "b2-spans-v1")
        self.assertEqual(meta["strategy"]["excerpt_cap_tokens"], 40)
        self.assertEqual(meta["input"]["sha256"], final._sha256(self.input_path.read_bytes()))
        self.assertEqual(meta["contract"]["sha256"], final._sha256(self.contract_path.read_bytes()))
        self.assertIn("does not pin weights", meta["model"]["note"])
        self.assertEqual(meta["output_schema"], final.PREDICTION_SCHEMA)
        self.assertIn("commit", meta["source"])
        de = [json.loads(l) for l in (self.out / "predictions" / "predictions_de.jsonl").read_text().splitlines()]
        self.assertEqual([r["id"] for r in de], ["syn_de_2", "syn_de_1"])  # contract order, not id order
        self.assertEqual(de[0]["labels_b"], [0.0, 0.0, 0.0, 1.0, 1.0, 0.0])
        self.assertEqual(de[1]["labels_a"], [0.0] * 4)  # empty difference list: documented all-zero B2 output
        fr = json.loads((self.out / "predictions" / "predictions_fr.jsonl").read_text())
        self.assertEqual(fr["labels_a"], [0.0] * 5)
        self.assertEqual(fr["labels_b"][-4:], [0.6, 0.6, 0.6, 0.0])
        raw_ids = [json.loads(l)["id"] for l in (self.out / "raw.jsonl").read_text().splitlines()]
        self.assertEqual(raw_ids, [d["id"] for d in DOCS])
        self.assertEqual(sum(f["records"] for f in meta["prediction_files"].values()), len(DOCS))

    def test_failed_call_leaves_incomplete_run_without_predictions(self):
        code, result = self.run_main(backend=FakeBackend(fail={"syn_fr_5"}))
        self.assertEqual((code, result["status"]), (final.EXIT_INCOMPLETE, "incomplete"))
        meta = json.loads((self.out / "final_meta.json").read_text())
        self.assertEqual(meta["status"], "incomplete")
        self.assertFalse((self.out / "predictions").exists())
        diag = {d["id"]: d for d in json.loads((self.out / "diagnostics.json").read_text())["documents"]}
        self.assertEqual(diag["syn_fr_5"]["status"], "call_failed")
        self.assertEqual(diag["syn_fr_5"]["error"], "timeout")

    def test_unparseable_response_is_not_zero_filled(self):
        code, result = self.run_main(backend=FakeBackend(garbage={"syn_it_9"}))
        self.assertEqual(code, final.EXIT_INCOMPLETE)
        self.assertIn("syn_it_9: unparseable", result["problems"])
        self.assertFalse((self.out / "predictions").exists())

    def meta(self):
        return json.loads((self.out / "final_meta.json").read_text())

    def test_keyboard_interrupt_marks_incomplete_and_exits_130(self):
        class Crash(FakeBackend):
            def generate(self, prompt, max_new_tokens):
                if len(self.prompts) == 2:
                    raise KeyboardInterrupt
                return super().generate(prompt, max_new_tokens)
        code, result = self.run_main(backend=Crash())
        self.assertEqual((code, result["status"]), (final.EXIT_INTERRUPTED, "interrupted"))
        self.assertEqual(self.meta()["status"], "incomplete")
        self.assertEqual(self.meta()["interrupted"]["type"], "KeyboardInterrupt")
        self.assertFalse((self.out / "predictions").exists())
        self.assertEqual(len((self.out / "raw.jsonl").read_text().splitlines()), 2)  # evidence kept

    def test_ordinary_exception_marks_incomplete_and_exits_4(self):
        class Boom(FakeBackend):
            def generate(self, prompt, max_new_tokens):
                raise RuntimeError("backend bug")
        code, result = self.run_main(backend=Boom())
        self.assertEqual((code, result["status"]), (final.EXIT_INCOMPLETE, "incomplete"))
        self.assertEqual(self.meta()["interrupted"]["type"], "RuntimeError")
        self.assertFalse(final.verify_run(self.out)[0])

    def test_interruption_while_writing_predictions_leaves_no_predictions_dir(self):
        real_sha = final._sha256
        def crash_while_writing_predictions(data):
            if (self.out / "predictions.partial").exists():
                raise KeyboardInterrupt
            return real_sha(data)
        with mock.patch.object(final, "_sha256", crash_while_writing_predictions):
            code, _ = self.run_main(backend=FakeBackend())
        self.assertEqual(code, final.EXIT_INTERRUPTED)
        self.assertEqual(self.meta()["status"], "incomplete")
        self.assertFalse((self.out / "predictions").exists())
        self.assertTrue((self.out / "predictions.partial").exists())  # kept for diagnosis
        self.assertFalse(final.verify_run(self.out)[0])

    def test_window_after_rename_before_commit_is_rejected_by_verify(self):
        real_write = final._write_meta
        def crash_on_commit(out_dir, meta):
            if meta.get("status") == "complete":
                raise KeyboardInterrupt
            real_write(out_dir, meta)
        with mock.patch.object(final, "_write_meta", crash_on_commit):
            code, _ = self.run_main(backend=FakeBackend())
        self.assertEqual(code, final.EXIT_INTERRUPTED)
        self.assertTrue((self.out / "predictions" / "predictions_de.jsonl").exists())  # files exist ...
        self.assertEqual(self.meta()["status"], "incomplete")                          # ... but not committed
        accepted, reasons = final.verify_run(self.out)
        self.assertFalse(accepted)
        self.assertTrue(any("not 'complete'" in reason for reason in reasons))
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            self.assertEqual(final.main(["--verify", str(self.out)]), final.EXIT_INCOMPLETE)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "rejected")

    def test_verify_accepts_complete_run_and_rejects_tampering(self):
        self.assertEqual(self.run_main(backend=FakeBackend())[0], final.EXIT_OK)
        self.assertEqual(final.verify_run(self.out), (True, []))
        path = self.out / "predictions" / "predictions_de.jsonl"
        lines = path.read_text().splitlines()
        path.write_text("\n".join(reversed(lines)) + "\n")
        accepted, reasons = final.verify_run(self.out)
        self.assertFalse(accepted)
        self.assertTrue(any("sha256" in reason for reason in reasons))
        self.assertTrue(any("order" in reason for reason in reasons))
        path.write_text("{not json\n")
        accepted, reasons = final.verify_run(self.out)
        self.assertFalse(accepted)
        self.assertTrue(any("malformed" in reason for reason in reasons))

    def test_malformed_prediction_vectors_are_rejected(self):
        item = final.load_final_input(self.input_path, contract())[0]
        good = [0.0] * len(item.text_a)
        for labels in ([0.0] * (len(item.text_a) - 1), good[:-1] + [float("nan")], good[:-1] + [1.5], good[:-1] + [True]):
            with self.subTest(labels=labels), self.assertRaises(final.InvalidFinalInput):
                final.validate_prediction(item, labels, [0.0] * len(item.text_b))

    def test_verify_checks_vectors_even_when_hash_metadata_is_updated(self):
        self.assertEqual(self.run_main(backend=FakeBackend())[0], final.EXIT_OK)
        path = self.out / "predictions" / "predictions_de.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records[0]["labels_a"].pop()
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        meta = self.meta()
        meta["prediction_files"][path.name]["sha256"] = final._sha256(path.read_bytes())
        (self.out / "final_meta.json").write_text(json.dumps(meta))
        accepted, reasons = final.verify_run(self.out)
        self.assertFalse(accepted)
        self.assertTrue(any("values for" in reason for reason in reasons))


class MockEndpoint(http.server.BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = body["messages"][-1]["content"]
        MockEndpoint.requests.append(prompt)
        doc = next(d for d in DOCS if d["text_b"] in prompt)
        payload = {"choices": [{"message": {"content": json.dumps(B2_RESPONSES[doc["id"]])}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class LocalEndpointTests(FinalTestCase):
    def test_cli_against_local_mock_endpoint(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockEndpoint)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            env = {"LLM_NAME": "mock-apertus", "LLM_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1", "LLM_API_KEY": "test-key-not-secret"}
            with mock.patch.dict(os.environ, env):
                code, result = self.run_main("--timeout-s", "10", "--model-revision", "declared-abc")
        finally:
            server.shutdown()
        self.assertEqual((code, result["status"]), (final.EXIT_OK, "complete"))
        meta = json.loads((self.out / "final_meta.json").read_text())
        self.assertEqual(meta["backend"]["timeout_s"], 10.0)
        self.assertEqual(meta["backend"]["max_attempts"], 1)
        self.assertEqual(meta["model"]["declared_revision"], "declared-abc")
        self.assertNotIn("test-key-not-secret", "".join(p.read_text() for p in self.out.rglob("*") if p.is_file()))


class IsolationTests(unittest.TestCase):
    def test_final_module_does_not_load_scorer(self):
        code = "import sys, uzh_rsd.final; print('uzh_rsd.scoring' in sys.modules, 'uzh_rsd.audit' in sys.modules)"
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                             env={**os.environ, "PYTHONPATH": str(TRACK / "src")}).stdout.split()
        self.assertEqual(out, ["False", "False"])

    def test_development_cli_still_refuses_test_split_before_io(self):
        forbidden = mock.Mock(side_effect=AssertionError("I/O before split guard"))
        with mock.patch.object(data_adapter, "fetch_split", forbidden), mock.patch.object(data_adapter, "load_split", forbidden):
            for command in ("fetch", "infer", "evaluate", "run", "audit"):
                with self.subTest(command=command), redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main([command, "--split", "test"]), 2)

    def test_final_is_explicit_mode_only(self):
        self.assertNotIn("final", cli.MVP_COMMANDS + cli.S1_COMMANDS)
        makefile = (TRACK / "Makefile").read_text()
        self.assertIn("MODE ?= pilot", makefile)  # default stays the dev pilot
        self.assertEqual(makefile.count("$(IMAGE) -m uzh_rsd.final"), 1)
        self.assertLess(makefile.index("ifeq ($(MODE),pilot)"), makefile.index("else ifeq ($(MODE),final)"))
        self.assertLess(makefile.index("else ifeq ($(MODE),final)"), makefile.index("$(IMAGE) -m uzh_rsd.final"))

    def test_make_final_mode_blocks_before_build_without_configuration(self):
        for extra, expected in (([], "needs FINAL_CONTRACT FINAL_INPUT FINAL_OUT_DIR FINAL_RUN_ID"),
                                (["FINAL_CONTRACT=/nonexistent", "FINAL_INPUT=/x", "FINAL_OUT_DIR=/tmp", "FINAL_RUN_ID=r"], "not found")):
            with self.subTest(extra=extra):
                proc = subprocess.run(["make", "-s", "-C", str(TRACK), "run", "MODE=final", *extra], capture_output=True, text=True,
                                      env={k: v for k, v in os.environ.items() if not k.startswith("FINAL_")})
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn(expected, proc.stdout)
                self.assertNotIn("docker build", proc.stdout + proc.stderr)
        proc = subprocess.run(["make", "-s", "-C", str(TRACK), "run", "MODE=bogus"], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("unknown MODE", proc.stdout)


if __name__ == "__main__":
    unittest.main()
