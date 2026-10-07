"""S1 adapter and S1-MANIFEST tests.

Unit tests use the SYNTHETIC fixture in tests/fixtures/s1. The real-data
tests at the bottom run only when the pinned dev files have been fetched
(`make s1-fetch`); they skip with an explicit reason otherwise.
"""

import dataclasses
import io
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from uzh_rsd import data_adapter
from uzh_rsd.data_adapter import (
    DATASET_REVISION,
    GoldLabels,
    InferenceInput,
    IntegrityError,
    PinnedFile,
    build_manifest,
    fetch_split,
    git_blob_sha1,
    load_split,
    local_path,
    manifest_digest,
    select_manifest_docs,
)
from uzh_rsd.tokens import tokenize

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "s1" / "synthetic_dev_de.jsonl"
TRACK = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = TRACK / "manifests" / "s1-dev.json"


def _pin_fixture(data: bytes):
    pinned = {"dev": {**data_adapter._SPLIT_FILES["dev"], "de": PinnedFile("data/de/dev_de.jsonl", git_blob_sha1(data), len(data))}}
    return mock.patch.dict(data_adapter._SPLIT_FILES, pinned)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.data = FIXTURE.read_bytes()

    def test_fetch_downloads_one_pinned_dev_url_and_verifies(self):
        opener = mock.Mock(return_value=FakeResponse(self.data))
        with _pin_fixture(self.data):
            path = fetch_split("dev", "de", data_dir=self.tmp, opener=opener)
            self.assertEqual(path.read_bytes(), self.data)
            fetch_split("dev", "de", data_dir=self.tmp, opener=opener)  # cached: no second request
        self.assertEqual(opener.call_count, 1)
        url = opener.call_args.args[0]
        self.assertIn(f"/resolve/{DATASET_REVISION}/data/de/dev_de.jsonl", url)
        self.assertNotIn("test", url)

    def test_tampered_download_is_rejected_and_not_written(self):
        opener = mock.Mock(return_value=FakeResponse(self.data + b"\n"))
        with _pin_fixture(self.data), self.assertRaises(IntegrityError):
            fetch_split("dev", "de", data_dir=self.tmp, opener=opener)
        with _pin_fixture(self.data):
            self.assertFalse(local_path("dev", "de", self.tmp).exists())

    def test_load_separates_inference_inputs_from_gold(self):
        with _pin_fixture(self.data):
            target = local_path("dev", "de", self.tmp)
            target.parent.mkdir(parents=True)
            target.write_bytes(self.data)
            records = load_split("dev", "de", data_dir=self.tmp)
        self.assertEqual(len(records), 4)
        inference_fields = {field.name for field in dataclasses.fields(InferenceInput)}
        self.assertFalse({"labels_a", "labels_b", "labels"} & inference_fields)
        for inference, gold in records:
            self.assertIsInstance(gold, GoldLabels)
            self.assertEqual(len(gold.labels_a), len(inference.text_a))
            self.assertEqual(len(gold.labels_b), len(inference.text_b))
        unicode_record = records[3][0]
        self.assertEqual(unicode_record.text_a.tokens[3], "„Art.")

    def test_load_without_fetch_fails_clearly(self):
        with self.assertRaises(FileNotFoundError):
            load_split("dev", "de", data_dir=self.tmp)

    def test_label_length_mismatch_in_source_fails(self):
        broken = json.loads(self.data.decode().splitlines()[0])
        broken["labels_a"] = broken["labels_a"][:-1]
        data = (json.dumps(broken) + "\n").encode()
        with _pin_fixture(data):
            target = local_path("dev", "de", self.tmp)
            target.parent.mkdir(parents=True)
            target.write_bytes(data)
            with self.assertRaises(ValueError):
                load_split("dev", "de", data_dir=self.tmp)


def _synthetic_inputs(lengths):
    inputs = {}
    for language in data_adapter.LANGUAGES:
        items = []
        for index, (len_a, len_b) in lengths.items():
            items.append(
                InferenceInput(
                    id=f"admin_{language}_{index}",
                    language=language,
                    text_a=tokenize(" ".join(["w"] * len_a)),
                    text_b=tokenize(" ".join(["v"] * len_b)),
                    page_en="SYNTHETIC",
                    page_other="SYNTHETIC",
                )
            )
        inputs[language] = items
    return inputs


class ManifestSelectionTests(unittest.TestCase):
    def test_selection_is_deterministic_bounded_and_respects_exclusions(self):
        lengths = {index: (100, 120) for index in range(20)}
        lengths[5] = (1000, 900)  # too long
        lengths[6] = (10, 10)  # too short
        inputs = _synthetic_inputs(lengths)
        chosen = select_manifest_docs(inputs, excluded_ids=["admin_fr_7"])
        self.assertEqual(chosen, select_manifest_docs(inputs, excluded_ids=["admin_fr_7"]))
        self.assertEqual(len(chosen), data_adapter.MANIFEST_DOCS)
        self.assertFalse({5, 6, 7} & set(chosen))

    def test_selection_is_gold_blind(self):
        # build_manifest receives gold, but changing gold must not change the chosen documents.
        inputs = _synthetic_inputs({index: (100, 100) for index in range(12)})

        def records(fill):
            return {
                language: [(item, GoldLabels(item.id, (fill,) * len(item.text_a), (fill,) * len(item.text_b))) for item in items]
                for language, items in inputs.items()
            }

        first = build_manifest(records(0.0), [], "x")
        second = build_manifest(records(1.0), [], "x")
        self.assertEqual([e["id"] for e in first["entries"]], [e["id"] for e in second["entries"]])
        self.assertNotEqual(first["manifest_sha256"], second["manifest_sha256"])  # gold hash still binds evaluation

    def test_shortfall_is_an_error_not_invented_data(self):
        with self.assertRaises(ValueError):
            select_manifest_docs(_synthetic_inputs({0: (100, 100), 1: (100, 100)}), [])


@unittest.skipUnless(all(local_path("dev", language).exists() for language in data_adapter.LANGUAGES), "pinned dev files not fetched (run `make s1-fetch`)")
class RealDevDataTests(unittest.TestCase):
    """Runs against the pinned SwissGov-RSD dev files (train/dev only)."""

    @classmethod
    def setUpClass(cls):
        cls.records = {language: load_split("dev", language) for language in data_adapter.LANGUAGES}

    def test_counts_and_exact_label_lengths(self):
        for language, records in self.records.items():
            self.assertEqual(len(records), 168, language)
            for inference, gold in records:
                self.assertEqual(len(gold.labels_a), len(inference.text_a))
                self.assertEqual(len(gold.labels_b), len(inference.text_b))

    def test_tracked_manifest_matches_rule_and_contains_no_labels(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertEqual(manifest["manifest_sha256"], manifest_digest(manifest))
        self.assertEqual(manifest["dataset"]["revision"], DATASET_REVISION)
        self.assertEqual(manifest["counts"], {"en-de": 3, "en-fr": 3, "en-it": 3})
        self.assertTrue(5 <= len(manifest["entries"]) <= 10)
        text = MANIFEST.read_text()
        self.assertNotIn("labels_a", text)
        self.assertNotIn("labels_b", text)
        lookup = {inference.id: inference for records in self.records.values() for inference, _ in records}
        for entry in manifest["entries"]:
            inference = lookup[entry["id"]]
            self.assertEqual(entry["text_a_sha256"], inference.text_a.sha256)
            self.assertEqual(entry["text_b_sha256"], inference.text_b.sha256)
            self.assertEqual(entry["tokens_a"], len(inference.text_a))
            self.assertEqual(entry["tokens_b"], len(inference.text_b))


if __name__ == "__main__":
    unittest.main()
