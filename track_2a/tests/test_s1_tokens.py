"""S1-TOKENS: official order, exact offsets, exact lengths, no repair."""

import math
import unittest

from uzh_rsd.tokens import LengthMismatchError, check_vector, tokenize


class TokenizeTests(unittest.TestCase):
    CASES = [
        "",
        "   ",
        "single",
        "The fee is CHF 50 .",
        "  leading and trailing  ",
        "tab\tseparated\nnew line\r\nwindows",
        "Für Bürger:innen gilt „Art. 5“ — siehe § 3 .",
        "zero​width stays joined",
        "repeat repeat repeat .",
        "emoji 👍🏽 and combining é ok",
        "ideographic　space and line separator",
    ]

    def test_tokens_match_official_split_for_every_case(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(tokenize(text).tokens, tuple(text.split()))

    def test_offsets_recover_each_token_from_original_text(self):
        for text in self.CASES:
            result = tokenize(text)
            for token, (start, end) in zip(result.tokens, result.offsets):
                self.assertEqual(text[start:end], token)
            starts = [start for start, _ in result.offsets]
            self.assertEqual(starts, sorted(starts))

    def test_repeated_tokens_get_distinct_offsets(self):
        result = tokenize("Contact us . Contact us again .")
        self.assertEqual(result.offsets[0], (0, 7))
        self.assertEqual(result.offsets[3], (13, 20))
        self.assertEqual(result.tokens[0], result.tokens[3])

    def test_unicode_whitespace_splits_but_zero_width_space_does_not(self):
        self.assertEqual(len(tokenize("a b").tokens), 2)
        self.assertEqual(len(tokenize("a b").tokens), 2)
        self.assertEqual(len(tokenize("a​b").tokens), 1)

    def test_rejects_non_string(self):
        with self.assertRaises(TypeError):
            tokenize(None)


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.doc = tokenize("one two three .")

    def test_exact_length_passes_and_mismatch_never_pads_or_truncates(self):
        self.assertEqual(check_vector(self.doc, [0, 0.5, 1, 0.0], name="p"), (0.0, 0.5, 1.0, 0.0))
        for wrong in ([0.0] * 3, [0.0] * 5, []):
            with self.subTest(length=len(wrong)), self.assertRaises(LengthMismatchError):
                check_vector(self.doc, wrong, name="p")

    def test_rejects_invalid_values(self):
        for bad in (math.nan, math.inf, -math.inf, 1.01, -0.01, True, "0.5", None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                check_vector(self.doc, [0.0, 0.0, 0.0, bad], name="p")

    def test_punctuation_mask_only_allowed_for_gold(self):
        self.assertEqual(check_vector(self.doc, [0, 0, 0, -1], name="gold", allow_mask=True)[-1], -1.0)
        with self.assertRaises(ValueError):
            check_vector(self.doc, [0, 0, 0, -1], name="prediction")
        with self.assertRaises(ValueError):
            check_vector(self.doc, [0, 0, 0, -0.5], name="gold", allow_mask=True)


if __name__ == "__main__":
    unittest.main()
