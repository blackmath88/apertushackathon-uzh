"""HF Jobs final-mode integration, synthetic only: fake backend, fake uploader, fake HF API. No model load, no spend."""

import io
import json
import shutil
import tarfile
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from uzh_rsd import data_adapter, evaluation, final, hf_job, hf_launch, prompts, runner
from uzh_rsd.backends import Generation

DOCS = [
    {"id": "admin_it_9", "language": "it", "text_a": "Office opens at nine .", "text_b": "L' ufficio apre alle dieci ."},
    {"id": "admin_de_2", "language": "de", "text_a": "The fee is 30 francs .", "text_b": "Die Gebühr beträgt 60 Franken ."},
    {"id": "admin_fr_5", "language": "fr", "text_a": "Contact us .", "text_b": "Contactez-nous ."},
]
RESPONSES = {"admin_it_9": [{"a": "nine", "b": "dieci", "kind": "CHANGE", "severity": 4}],
             "admin_de_2": [{"a": "30 francs", "b": "60 Franken", "kind": "CHANGE", "severity": 5}],
             "admin_fr_5": []}


def provisional_contract():
    return {
        "schema": final.CONTRACT_SCHEMA, "status": "owner_approved_provisional",
        "evidence": "synthetic test", "decisions": {"full_set_order": "test-file order", "dropped_ids": "none dropped",
                                                     "output_layout": "per_language_jsonl"},
        "decision_basis": {"full_set_order": "synthetic", "dropped_ids": "synthetic", "output_layout": "synthetic"},
        "owner_approval": {"approved_by": "test", "approved_utc": "2026-10-13T00:00:00Z", "scope": "synthetic"},
        "order": [{"id": d["id"], "language": d["language"]} for d in DOCS],
    }


class PinnedFakeBackend:
    def __init__(self, interrupt_after=None):
        self.prompts, self.interrupt_after = [], interrupt_after

    def describe(self):
        return {"backend": "transformers", "model": "swiss-ai/Apertus-v1.5-8B", "revision": hf_launch.MODEL_REVISION, "device": "fake"}

    def generate(self, prompt, max_new_tokens):
        if self.interrupt_after is not None and len(self.prompts) == self.interrupt_after:
            raise KeyboardInterrupt
        self.prompts.append(prompt)
        doc = next(d for d in DOCS if d["text_b"] in prompt)
        return Generation(json.dumps({"differences": RESPONSES[doc["id"]]}), finish_reason="stop", completion_tokens=9, latency_s=0.1)


class RecordingUploader:
    instances = []

    def __init__(self, repo, run_id):
        self.repo, self.prefix, self.failures, self.pushed = repo, f"runs/{run_id}", 0, []
        RecordingUploader.instances.append(self)

    def push(self, path, relative=None):
        self.pushed.append(relative or Path(path).name)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.contract = self.tmp / "contract.json"
        self.contract.write_text(json.dumps(provisional_contract()))
        self.input = self.tmp / "input.jsonl"
        self.input.write_text("".join(json.dumps(d) + "\n" for d in DOCS))
        forbidden = mock.Mock(side_effect=AssertionError("forbidden call in final mode"))
        self.patches = [mock.patch.object(data_adapter, "fetch_split", forbidden), mock.patch.object(data_adapter, "load_split", forbidden),
                        mock.patch.object(hf_job, "fetch_split", forbidden), mock.patch.object(hf_job, "fetch_prompts", forbidden),
                        mock.patch.object(hf_job, "manifest_records", forbidden), mock.patch.object(runner, "manifest_records", forbidden),
                        mock.patch.object(prompts, "fetch_prompts", forbidden),
                        mock.patch.object(evaluation, "load_official_compute_correlations", forbidden),
                        mock.patch.object(evaluation, "load_official_function", forbidden),
                        mock.patch.object(hf_job, "Uploader", RecordingUploader)]
        for patch in self.patches:
            patch.start()
        RecordingUploader.instances = []

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        shutil.rmtree(self.tmp)

    def job(self, backend, *extra):
        argv = ["--run-id", "final-test", "--model", "swiss-ai/Apertus-v1.5-8B", "--revision", hf_launch.MODEL_REVISION,
                "--final-contract", str(self.contract), "--final-input", str(self.input), "--out", str(self.tmp / "runs"),
                "--output-repo", "someone/private-repo", *extra]
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = hf_job.main(argv, backend_factory=lambda timeout: backend)
        return code, buffer.getvalue()


class JobFinalModeTests(Base):
    def test_final_job_completes_verifies_and_uploads_all_files(self):
        code, log = self.job(PinnedFakeBackend())
        self.assertEqual(code, 0)
        out = self.tmp / "runs" / "final-test" / "final"
        self.assertEqual(final.verify_run(out), (True, []))
        meta = json.loads((out / "final_meta.json").read_text())
        self.assertEqual(meta["model"]["revision"], hf_launch.MODEL_REVISION)
        self.assertIn("exact revision", meta["model"]["note"])
        self.assertEqual(meta["contract"]["status"], "owner_approved_provisional")
        self.assertIn("job", meta)
        pushed = RecordingUploader.instances[0].pushed
        self.assertEqual(pushed.count("final/raw.jsonl"), len(DOCS) + 1)  # after each call + final sweep
        for name in ("final/final_meta.json", "final/diagnostics.json", "final/predictions/predictions_de.jsonl"):
            self.assertIn(name, pushed)
        for doc in DOCS:  # log lines carry ids, never document text
            self.assertNotIn(doc["text_b"], log.split("UZH-RSD-BUNDLE-BEGIN")[0])

    def test_interrupt_keeps_partial_raw_uploaded_and_marks_incomplete(self):
        code, _ = self.job(PinnedFakeBackend(interrupt_after=2))
        self.assertNotEqual(code, 0)
        out = self.tmp / "runs" / "final-test" / "final"
        meta = json.loads((out / "final_meta.json").read_text())
        self.assertEqual(meta["status"], "incomplete")
        self.assertEqual(len((out / "raw.jsonl").read_text().splitlines()), 2)
        self.assertIn("final/raw.jsonl", RecordingUploader.instances[0].pushed)
        self.assertIn("final/final_meta.json", RecordingUploader.instances[0].pushed)
        self.assertFalse(final.verify_run(out)[0])

    def test_unresolved_contract_blocks_before_backend(self):
        contract = provisional_contract()
        contract["status"] = "unresolved"
        self.contract.write_text(json.dumps(contract))
        built = mock.Mock(side_effect=AssertionError("backend built"))
        argv = ["--run-id", "x", "--model", "m", "--revision", "r", "--final-contract", str(self.contract), "--final-input", str(self.input),
                "--out", str(self.tmp / "runs")]
        with redirect_stdout(io.StringIO()):
            code = hf_job.main(argv, backend_factory=built)
        self.assertEqual(code, final.EXIT_BLOCKED)

    def test_mode_arguments_are_exclusive(self):
        for argv in (["--run-id", "x", "--model", "m", "--revision", "r", "--final-contract", "c"],
                     ["--run-id", "x", "--model", "m", "--revision", "r", "--final-contract", "c", "--final-input", "i", "--manifest", "m.json"],
                     ["--run-id", "x", "--model", "m", "--revision", "r"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), mock.patch("sys.stderr", io.StringIO()):
                hf_job.main(argv)

    def test_log_bundle_flattens_and_round_trips(self):
        self.job(PinnedFakeBackend())
        out = self.tmp / "runs" / "final-test" / "final"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            hf_job.print_bundle(out, flatten_subdirs=True)
        restored = self.tmp / "restored"
        restored.mkdir()
        self.assertTrue(hf_launch._decode_log_bundle(buffer.getvalue().splitlines(), restored))
        self.assertTrue((restored / "predictions__predictions_de.jsonl").exists())
        self.assertEqual((restored / "final_meta.json").read_bytes(), (out / "final_meta.json").read_bytes())


class FakeApi:
    def __init__(self, active=(), price=0.03):
        self.active, self.price, self.run_job = list(active), price, mock.Mock(side_effect=AssertionError("run_job called"))

    def whoami(self):
        return {"name": "tester"}

    def list_jobs_hardware(self):
        return [types.SimpleNamespace(name=hf_launch.FLAVOR, unit_cost_usd=self.price * 60, unit_label="hour")]

    def list_jobs(self):
        return [types.SimpleNamespace(id=j, status=types.SimpleNamespace(stage="RUNNING")) for j in self.active]


class LauncherTests(Base):
    def args(self, **overrides):
        values = dict(contract=self.contract, input=self.input, timeout_min=108, max_job_usd=3.30, budget_usd=4.50,
                      prior_committed_floor_usd=0.75, confirm_spend=False, output_repo=None)
        values.update(overrides)
        return types.SimpleNamespace(**values)

    def test_ceiling_includes_starting_allowance(self):
        self.assertEqual(hf_launch.final_job_ceiling(108, 0.03), 3.30)
        self.assertGreater(hf_launch.final_job_ceiling(110, 0.03), 3.30)

    def test_preflight_gates(self):
        ledger = self.tmp / "ledger.jsonl"
        ledger.write_text(json.dumps({"job_id": "a", "max_usd": 0.5, "actual_usd": 0.5}) + "\n")
        with mock.patch.object(hf_launch, "LEDGER", ledger), mock.patch.object(hf_launch, "_git_commit", return_value="abc123"):
            code, report = hf_launch.final_preflight(self.args(), FakeApi())
            self.assertEqual((code, report["problems"]), (0, []))
            self.assertEqual(report["documents"], 3)
            self.assertEqual(report["committed_usd"], 0.75)  # conservative floor above the ledger's 0.5
            self.assertEqual(hf_launch.final_preflight(self.args(timeout_min=110), FakeApi())[0], 4)
            self.assertEqual(hf_launch.final_preflight(self.args(budget_usd=3.9), FakeApi())[0], 4)
            self.assertEqual(hf_launch.final_preflight(self.args(), FakeApi(active=["job-1"]))[0], 4)
            self.assertEqual(hf_launch.final_preflight(self.args(), FakeApi(price=0.05))[0], 4)
        with mock.patch.object(hf_launch, "LEDGER", ledger), mock.patch.object(hf_launch, "_git_commit", return_value="abc123-dirty"):
            self.assertEqual(hf_launch.final_preflight(self.args(), FakeApi())[0], 4)

    def test_preflight_rejects_unresolved_contract_and_contaminated_input(self):
        contract = provisional_contract()
        del contract["owner_approval"]
        self.contract.write_text(json.dumps(contract))
        with self.assertRaises(final.FinalBlocked):
            hf_launch.final_preflight(self.args())
        self.contract.write_text(json.dumps(provisional_contract()))
        self.input.write_text("".join(json.dumps(dict(d, labels_a=[0.5])) + "\n" for d in DOCS))
        with self.assertRaises(final.InvalidFinalInput):
            hf_launch.final_preflight(self.args())

    def test_launch_without_confirm_spend_never_starts_a_job(self):
        api = FakeApi()
        with mock.patch("huggingface_hub.HfApi", return_value=api), mock.patch("huggingface_hub.get_token", return_value="tok"), \
             mock.patch.object(hf_launch, "LEDGER", self.tmp / "ledger.jsonl"), mock.patch.object(hf_launch, "RUNS_DIR", self.tmp / "runs"), \
             mock.patch.object(hf_launch, "_git_commit", return_value="abc123"), redirect_stdout(io.StringIO()):
            self.assertEqual(hf_launch.launch_final(self.args()), 0)
        api.run_job.assert_not_called()
        launch = json.loads(next((self.tmp / "runs").glob("final-*/launch.json")).read_text())
        self.assertFalse(launch["launched"])
        self.assertEqual(launch["max_usd"], 3.30)

    def test_bundle_carries_contract_and_input_deterministically(self):
        extra = {hf_launch.FINAL_BUNDLE_CONTRACT: self.contract.read_bytes(), hf_launch.FINAL_BUNDLE_INPUT: self.input.read_bytes()}
        first, second = hf_launch.build_bundle(extra), hf_launch.build_bundle(extra)
        self.assertEqual(first, second)
        with tarfile.open(fileobj=io.BytesIO(first)) as tar:
            names = tar.getnames()
        self.assertIn("final/input.jsonl", names)
        self.assertIn("src/uzh_rsd/final.py", names)
        self.assertFalse(any(name.startswith(("data/", "results/")) for name in names))


if __name__ == "__main__":
    unittest.main()
