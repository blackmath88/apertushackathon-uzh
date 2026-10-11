import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from uzh_rsd import cli, hf_launch
from uzh_rsd.backends import Generation, OpenAICompatibleBackend
from uzh_rsd.data_adapter import LANGUAGES, local_path
from uzh_rsd.evaluation import DEFAULT_OFFICIAL_DIR, OFFICIAL_FILES
from uzh_rsd.hf_job import print_bundle
from uzh_rsd.prompts import DEFAULT_PROMPT_DIR, OFFICIAL_PROMPTS
from uzh_rsd.runner import load_manifest, manifest_records, read_raw, run_inference

TRACK = Path(__file__).resolve().parents[1]
MANIFEST = TRACK / "manifests" / "s1-dev.json"
FETCHED = all(local_path("dev", language).exists() for language in LANGUAGES) and all(
    (DEFAULT_PROMPT_DIR / relative).exists() for relative, _ in OFFICIAL_PROMPTS.values()
) and all((DEFAULT_OFFICIAL_DIR / relative).exists() for relative in OFFICIAL_FILES)


class EchoBackend:
    """Deterministic stand-in: B0 echoes tokens with similarity 5 except every
    third token; B2 marks the first three English tokens. Fails on request."""

    def __init__(self, fail_ids=(), garbage_ids=()):
        self.fail_ids, self.garbage_ids, self.prompts = set(fail_ids), set(garbage_ids), []

    def generate(self, prompt, max_new_tokens):
        self.prompts.append(prompt)
        doc = next((i for i in self.fail_ids | self.garbage_ids if self.current == i), None)
        if doc in self.fail_ids:
            return Generation(None, "timeout", latency_s=1.0)
        if doc in self.garbage_ids:
            return Generation('{"sentence1": [["truncated"', finish_reason="length", latency_s=1.0, completion_tokens=max_new_tokens)
        if prompt.startswith("Annotate"):
            block = prompt.split("## Input to Annotate")[1]
            a = json.loads(block.split("Sentence 1: ")[1].split("\n")[0])
            b = json.loads(block.split("Sentence 2: ")[1].split("\n")[0])
            body = {"sentence1": [[t, 5 if i % 3 else 1] for i, t in enumerate(a)], "sentence2": [[t, 5] for t in b]}
        else:
            a = prompt.split("Version A (English):\n")[1].split("\n")[0].split()
            body = {"differences": [{"a": " ".join(a[:3]), "b": "", "kind": "OMISSION", "severity": 4}]}
        return Generation(json.dumps(body), prompt_tokens=100, completion_tokens=50, finish_reason="stop", latency_s=0.5,
                          token_count_source="fake")


class TrackingItems:
    def __init__(self, items, backend):
        self.items, self.backend = items, backend

    def __iter__(self):
        for item in self.items:
            self.backend.current = item.id
            yield item


@unittest.skipUnless(FETCHED, "run `make s1-fetch` first (dev data, evaluator and prompts)")
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest = load_manifest(MANIFEST)
        self.records = manifest_records(self.manifest)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_fake(self, backend, deadline=None, clock=None):
        items = TrackingItems([inference for inference, _ in self.records], backend)
        kwargs = {"deadline": deadline, "clock": clock} if clock else {}
        return run_inference(backend, items, ("b0", "b2"), self.tmp / "run" / "raw.jsonl", run_id="t", **kwargs)

    def test_prompts_never_contain_gold_vectors(self):
        backend = EchoBackend()
        self.run_fake(backend)
        self.assertEqual(len(backend.prompts), 18)
        for (inference, gold), b0_prompt in zip(self.records, backend.prompts[0::2]):
            self.assertNotIn(json.dumps(list(gold.labels_a)), b0_prompt)
            self.assertIn(json.dumps(list(inference.text_a.tokens), ensure_ascii=False), b0_prompt)

    def test_failures_are_recorded_and_never_scored_as_valid(self):
        from uzh_rsd.scoring import evaluate_run

        failing, garbage = self.records[0][0].id, self.records[4][0].id
        counts = self.run_fake(EchoBackend(fail_ids=[failing], garbage_ids=[garbage]))
        self.assertEqual(counts["call_failed"], 2)
        raw = read_raw(self.tmp / "run" / "raw.jsonl")
        self.assertEqual(len(raw), 18)
        results = evaluate_run(self.tmp / "run", self.manifest)
        self.assertEqual(results["matched_documents"], 7)
        self.assertEqual(results["coverage"]["b0"]["status"], {"ok": 7, "call_failed": 1, "unparseable": 1})
        self.assertEqual(results["coverage"]["b2"]["status"], {"ok": 7, "call_failed": 1, "unparseable": 1})
        self.assertEqual(results["views"]["paper_protocol"]["b0"]["documents_scored_as_zero"], 2)
        self.assertEqual(results["coverage"]["b0"]["usage"]["finish_length"], 1)
        exported = [json.loads(line)["id"] for line in (self.tmp / "run" / "predictions" / "b0" / "predictions_de.jsonl").read_text().splitlines()]
        self.assertNotIn(failing, exported)
        for view in ("matched", "available"):
            for method in ("b0", "b2"):
                score = results["views"][view][method]
                self.assertIsNotNone(score["macro"])
                for entry in score["per_language"].values():
                    self.assertAlmostEqual(entry["spearman"], entry["official_spearman"], places=10)
        self.assertIn("Matched documents", (self.tmp / "run" / "results.md").read_text())

    def test_deadline_skips_are_explicit(self):
        ticks = iter(range(100))
        counts = self.run_fake(EchoBackend(), deadline=4, clock=lambda: next(ticks))
        self.assertEqual(counts, {"attempted": 4, "call_failed": 0, "skipped_deadline": 14})
        raw = read_raw(self.tmp / "run" / "raw.jsonl")
        self.assertEqual(sum(1 for r in raw if r["status"] == "skipped_deadline"), 14)

    def test_interleaving_covers_every_language_first(self):
        from uzh_rsd.runner import interleave_languages

        ordered = interleave_languages([inference for inference, _ in self.records])
        self.assertEqual([item.language for item in ordered[:3]], ["de", "fr", "it"])
        self.assertEqual(sorted(item.id for item in ordered), sorted(inference.id for inference, _ in self.records))

    def test_manifest_text_hash_is_verified(self):
        tampered = json.loads(json.dumps(self.manifest))
        tampered["entries"][0]["text_a_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            manifest_records(tampered)


class OpenAIBackendTests(unittest.TestCase):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def backend(self, opener):
        return OpenAICompatibleBackend("https://user:pw@example.org/v1?k=1", "swiss-ai/Apertus-v1.5-8B", "SECRET", opener=opener)

    def test_success_records_usage_and_never_exposes_key(self):
        payload = {"model": "x", "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 7, "completion_tokens": 2}}
        captured = {}

        def opener(request, timeout):
            captured["auth"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data)
            return self.Response(json.dumps(payload).encode())

        backend = self.backend(opener)
        generation = backend.generate("hi", 10)
        self.assertEqual((generation.text, generation.prompt_tokens, generation.finish_reason), ("{}", 7, "stop"))
        self.assertEqual(captured["body"]["temperature"], 0.0)
        self.assertEqual(captured["auth"], "Bearer SECRET")
        self.assertNotIn("SECRET", json.dumps(backend.describe()))
        self.assertNotIn("pw", json.dumps(backend.describe()))

    def test_errors_become_failed_generations(self):
        def http_error(request, timeout):
            raise urllib.error.HTTPError("u", 503, "x", {}, None)

        self.assertEqual(self.backend(http_error).generate("hi", 10).error, "HTTP 503")
        self.assertEqual(self.backend(lambda r, timeout: self.Response(b"not json")).generate("hi", 10).error, "malformed chat completion response")


class CliEndpointTests(unittest.TestCase):
    def test_infer_without_endpoint_is_blocked_before_any_io(self):
        env = {k: v for k, v in os.environ.items() if k not in cli.ENDPOINT_ENV}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(cli, "_fetch", side_effect=AssertionError("fetch")):
            for command in ("infer", "run"):
                with self.subTest(command=command), redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(cli.main([command]), cli.EXIT_BLOCKED)
                self.assertIn("BLOCKED", out.getvalue())


class LaunchTests(unittest.TestCase):
    def test_bundle_is_deterministic_and_holds_no_data(self):
        import tarfile

        first, second = hf_launch.build_bundle(), hf_launch.build_bundle()
        self.assertEqual(first, second)
        names = tarfile.open(fileobj=io.BytesIO(first)).getnames()
        self.assertIn("src/uzh_rsd/hf_job.py", names)
        self.assertIn("manifests/s1-dev.json", names)
        self.assertFalse(any(name.startswith("data") or name.endswith(".jsonl") for name in names))

    def test_budget_uses_actual_cost_or_ceiling(self):
        entries = [{"max_usd": 1.35, "actual_usd": 0.6}, {"max_usd": 1.35, "actual_usd": None}]
        self.assertAlmostEqual(hf_launch.committed_usd(entries), 1.95)
        self.assertEqual(hf_launch.check_budget(entries, 1.05, 3.0), (True, 1.95))
        self.assertFalse(hf_launch.check_budget(entries, 1.35, 3.0)[0])

    def test_log_bundle_round_trip(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            source, target = tmp / "src", tmp / "dst"
            source.mkdir(), target.mkdir()
            (source / "raw.jsonl").write_text('{"x": "ü"}\n')
            (source / "run_meta.json").write_text("{}\n")
            with redirect_stdout(io.StringIO()) as out:
                print_bundle(source)
            lines = ["2026-10-11 log noise"] + out.getvalue().splitlines()
            self.assertTrue(hf_launch._decode_log_bundle(lines, target))
            self.assertEqual((target / "raw.jsonl").read_text(), '{"x": "ü"}\n')
            self.assertFalse(hf_launch._decode_log_bundle(["no bundle"], target))
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
