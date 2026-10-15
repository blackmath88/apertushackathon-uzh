"""Official-shaped input converter, synthetic fixtures only (no real test data)."""

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from uzh_rsd import data_adapter, evaluation, final, final_input
from uzh_rsd.backends import Generation

SENTINEL_LABEL = 0.31415926535  # distinctive annotation value
SENTINEL_TEXT = "UNTOKENIZED-SENTINEL-c0ffee"


def official_row(language, index, text_a, text_b):
    """Shaped like the pinned dev rows: same field names and types, synthetic values."""
    tokens_a, tokens_b = text_a.split(), text_b.split()
    return {"text_a": text_a, "text_a_untokenized": SENTINEL_TEXT, "text_b": text_b, "text_b_untokenized": SENTINEL_TEXT,
            "labels_a": [SENTINEL_LABEL] * len(tokens_a), "labels_b": [SENTINEL_LABEL] * len(tokens_b),
            "page_en": "https://example.invalid/en", "page_other": "https://example.invalid/x", "subset": "synthetic", "id": f"admin_{language}_{index}"}


ROWS = {
    "de": [official_row("de", 7, "Fees : 30 CHF .", "Gebühren : 60 CHF ."), official_row("de", 3, "Open daily .", "Täglich offen .")],
    "fr": [official_row("fr", 7, "Fees : 30 CHF .", "Frais : 30 CHF , TVA incluse .")],
    "it": [official_row("it", 5, "Call us .", "Chiamateci oggi .")],
}


class ConverterCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.sources = []
        for language, rows in ROWS.items():
            path = self.tmp / f"test_{language}.jsonl"
            path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            self.sources.append((language, path))
        self.out = self.tmp / "prepared"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_rows(self, rows, name="bad.jsonl"):
        path = self.tmp / name
        path.write_text("".join((row if isinstance(row, str) else json.dumps(row)) + "\n" for row in rows), encoding="utf-8")
        return path

    def all_text(self, directory):
        return "".join(p.read_text(encoding="utf-8") for p in Path(directory).rglob("*") if p.is_file())


class ConversionTests(ConverterCase):
    def test_converts_selected_fields_in_source_order_with_provenance(self):
        result = final_input.convert(self.sources, self.out)
        self.assertEqual(result["records"], 4)
        records = [json.loads(l) for l in (self.out / "final_input.jsonl").read_text().splitlines()]
        self.assertEqual([r["id"] for r in records], ["admin_de_7", "admin_de_3", "admin_fr_7", "admin_it_5"])  # file order, not sorted
        self.assertTrue(all(set(r) == {"id", "language", "text_a", "text_b"} for r in records))
        self.assertEqual(records[0]["text_a"], ROWS["de"][0]["text_a"])  # tokenized text verbatim
        provenance = json.loads((self.out / "final_input.provenance.json").read_text())
        self.assertEqual(provenance["sources"][0]["sha256"], final._sha256(self.sources[0][1].read_bytes()))
        self.assertEqual(provenance["output"]["sha256"], final._sha256((self.out / "final_input.jsonl").read_bytes()))
        self.assertFalse(provenance["development_exclusions_applied"])
        self.assertIn("not an organiser-confirmed", provenance["note"])

    def test_annotation_and_untokenized_values_never_reach_outputs(self):
        final_input.convert(self.sources, self.out)
        blob = self.all_text(self.out)
        self.assertNotIn(str(SENTINEL_LABEL), blob)
        self.assertNotIn(SENTINEL_TEXT, blob)

    def test_token_boundaries_match_the_official_tokens(self):
        final_input.convert(self.sources, self.out)
        draft = json.loads((self.out / "contract.draft.json").read_text())
        items = final.load_final_input(self.out / "final_input.jsonl", draft)
        for item in items:
            row = next(r for rows in ROWS.values() for r in rows if r["id"] == item.id)
            self.assertEqual(list(item.text_a.tokens), row["text_a"].split())
            self.assertEqual(len(item.text_b), len(row["labels_b"]))  # vector length = official label length

    def test_draft_contract_is_unresolved_and_refused(self):
        final_input.convert(self.sources, self.out)
        draft = json.loads((self.out / "contract.draft.json").read_text())
        self.assertEqual(draft["status"], "unresolved")
        self.assertEqual([e["id"] for e in draft["order"]], ["admin_de_7", "admin_de_3", "admin_fr_7", "admin_it_5"])
        with self.assertRaises(final.FinalBlocked):
            final.load_contract(self.out / "contract.draft.json")

    def test_no_overwrite(self):
        final_input.convert(self.sources, self.out)
        before = (self.out / "final_input.jsonl").read_bytes()
        with self.assertRaises(final_input.ConversionError):
            final_input.convert(self.sources, self.out)
        self.assertEqual((self.out / "final_input.jsonl").read_bytes(), before)


class RejectionTests(ConverterCase):
    def assert_rejected(self, rows, language="de"):
        path = self.write_rows(rows)
        with self.assertRaises(final_input.ConversionError) as caught:
            final_input.convert([(language, path)], self.out)
        message = str(caught.exception)
        self.assertNotIn(str(SENTINEL_LABEL), message)
        self.assertNotIn(SENTINEL_TEXT, message)
        self.assertFalse((self.out / "final_input.jsonl").exists())
        return message

    def test_malformed_records_are_rejected_without_echoing_values(self):
        row = ROWS["de"][0]
        cases = {
            "unknown field": dict(row, gold_score=[SENTINEL_LABEL]),
            "missing text": {k: v for k, v in row.items() if k != "text_b"},
            "non-string text": dict(row, text_a=[SENTINEL_LABEL]),
            "wrong language id": dict(row, id="admin_fr_7"),
            "empty text": dict(row, text_a="   "),
            "not json": "{" + SENTINEL_TEXT,
            "not object": json.dumps([SENTINEL_LABEL]),
        }
        for name, bad in cases.items():
            with self.subTest(name=name):
                message = self.assert_rejected([bad])
                self.assertIn("bad.jsonl:1", message)

    def test_duplicates_within_and_across_sources_are_rejected(self):
        self.assert_rejected([ROWS["de"][0], ROWS["de"][0]])
        other = self.write_rows([ROWS["de"][0]], "other.jsonl")
        with self.assertRaises(final_input.ConversionError):
            final_input.convert([("de", self.sources[0][1]), ("de", other)], self.out)

    def test_development_exclusions_are_not_applied(self):
        # Even an ID that would be on a development drop list is kept: no hidden filtering.
        rows = [official_row("de", 1, "a b", "c d"), official_row("de", 2, "e f", "g h")]
        final_input.convert([("de", self.write_rows(rows, "de.jsonl"))], self.out)
        self.assertEqual(len((self.out / "final_input.jsonl").read_text().splitlines()), 2)

    def test_cli_reports_errors_as_json(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = final_input.main(["--source", "xx=" + str(self.sources[0][1]), "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "error")


class ConvertThenInferTests(ConverterCase):
    """In-process sequence: official-shaped rows → converter → confirmed copy of the draft → final B2 (fake backend)."""

    def test_sentinels_never_reach_prompts_raw_logs_or_predictions(self):
        forbidden = mock.Mock(side_effect=AssertionError("forbidden call"))
        prompts = []

        class Backend:
            def describe(self):
                return {"backend": "fake", "model": "fake", "max_attempts": 1}

            def generate(self, prompt, max_new_tokens):
                prompts.append(prompt)
                return Generation(json.dumps({"differences": [{"a": "30", "b": "60", "kind": "CHANGE", "severity": 5}]}), finish_reason="stop")

        final_input.convert(self.sources, self.out)
        draft = json.loads((self.out / "contract.draft.json").read_text())
        draft.update(status="confirmed", evidence="synthetic test only",
                     decisions={"full_set_order": "synthetic", "dropped_ids": "synthetic", "output_layout": "per_language_jsonl"})
        contract_path = self.tmp / "contract.confirmed.json"
        contract_path.write_text(json.dumps(draft))
        run_dir = self.tmp / "run"
        with mock.patch.object(data_adapter, "load_split", forbidden), mock.patch.object(data_adapter, "fetch_split", forbidden), \
             mock.patch.object(evaluation, "load_official_compute_correlations", forbidden), \
             mock.patch.object(evaluation, "load_official_function", forbidden), redirect_stdout(io.StringIO()):
            code = final.main(["--contract", str(contract_path), "--input", str(self.out / "final_input.jsonl"), "--out", str(run_dir)],
                              backend_factory=lambda timeout: Backend())
        self.assertEqual(code, final.EXIT_OK)
        self.assertTrue(final.verify_run(run_dir)[0])
        blob = "\n".join(prompts) + self.all_text(run_dir)
        self.assertNotIn(str(SENTINEL_LABEL), blob)
        self.assertNotIn(SENTINEL_TEXT, blob)
        de = [json.loads(l) for l in (run_dir / "predictions" / "predictions_de.jsonl").read_text().splitlines()]
        self.assertEqual([r["id"] for r in de], ["admin_de_7", "admin_de_3"])
        self.assertEqual(len(de[0]["labels_b"]), len(ROWS["de"][0]["labels_b"]))
        self.assertEqual(de[0]["labels_b"], [0.0, 0.0, 1.0, 0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
