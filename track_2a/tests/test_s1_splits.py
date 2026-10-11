"""S1-SPLIT: every split other than train/dev is refused before any I/O."""

import builtins
import contextlib
import io
import os
import pathlib
import socket
import tempfile
import unittest
import urllib.request
from unittest import mock

from uzh_rsd import cli, data_adapter, evaluation
from uzh_rsd.data_adapter import SplitUnavailableError, fetch_split, load_split, local_path, source_url
from uzh_rsd.splits import SplitNotAllowedError, assert_development_split

REJECTED = ["test", "Test", "TEST", " dev", "dev ", "Dev", "full", "validation", "val", "dev/test", "", None, 0, ["dev"]]


class IOSpy:
    """Make every filesystem/network primitive the adapter could use raise."""

    def __init__(self):
        self.calls = []
        self._stack = contextlib.ExitStack()

    def _trap(self, name):
        def trapped(*args, **kwargs):
            self.calls.append(name)
            raise AssertionError(f"I/O attempted via {name}")

        return trapped

    def __enter__(self):
        targets = [
            (builtins, "open"),
            (io, "open"),
            (os, "replace"),
            (os, "makedirs"),
            (os, "stat"),
            (os, "listdir"),
            (pathlib.Path, "exists"),
            (pathlib.Path, "read_bytes"),
            (pathlib.Path, "read_text"),
            (pathlib.Path, "write_text"),
            (pathlib.Path, "write_bytes"),
            (pathlib.Path, "mkdir"),
            (pathlib.Path, "open"),
            (urllib.request, "urlopen"),
            (socket, "create_connection"),
            (tempfile, "NamedTemporaryFile"),
        ]
        for owner, name in targets:
            self._stack.enter_context(mock.patch.object(owner, name, self._trap(f"{getattr(owner, '__name__', owner)}.{name}")))
        return self

    def __exit__(self, *exc):
        self._stack.close()
        return False


class GuardTests(unittest.TestCase):
    def test_train_and_dev_are_allowed(self):
        self.assertEqual(assert_development_split("dev"), "dev")
        self.assertEqual(assert_development_split("train"), "train")

    def test_everything_else_is_rejected(self):
        for split in REJECTED:
            with self.subTest(split=split), self.assertRaises(SplitNotAllowedError):
                assert_development_split(split)


class AdapterRejectsBeforeIOTests(unittest.TestCase):
    def test_path_url_fetch_and_load_refuse_test_without_io(self):
        never_called = mock.Mock(side_effect=AssertionError("network opener called"))
        for split in REJECTED:
            for entry_point in (
                lambda s: local_path(s, "de"),
                lambda s: source_url(s, "de"),
                lambda s: fetch_split(s, "de", data_dir=pathlib.PurePath("/nonexistent"), opener=never_called),
                lambda s: load_split(s, "de", data_dir=pathlib.PurePath("/nonexistent")),
            ):
                with self.subTest(split=split), IOSpy() as spy, self.assertRaises(SplitNotAllowedError):
                    entry_point(split)
                self.assertEqual(spy.calls, [])
        never_called.assert_not_called()

    def test_absent_data_dir_does_not_change_rejection(self):
        with IOSpy() as spy, self.assertRaises(SplitNotAllowedError):
            load_split("test", "de", data_dir=pathlib.PurePath("/definitely/absent"))
        self.assertEqual(spy.calls, [])

    def test_train_is_policy_legal_but_has_no_official_source(self):
        with IOSpy() as spy, self.assertRaises(SplitUnavailableError):
            fetch_split("train", "de", opener=mock.Mock(side_effect=AssertionError))
        self.assertEqual(spy.calls, [])

    def test_no_test_split_source_is_registered(self):
        self.assertEqual(set(data_adapter._SPLIT_FILES), {"dev"})
        for files in data_adapter._SPLIT_FILES.values():
            for pinned in files.values():
                self.assertNotIn("test", pinned.path)


class CliTests(unittest.TestCase):
    def test_cli_refuses_test_split_before_any_command_runs(self):
        for command in ("dry-run", *cli.S1_COMMANDS, *cli.MVP_COMMANDS):
            # argparse's gettext may stat system locale catalogs on Python 3.12.
            # Isolate that stdlib presentation detail, not any data/network path.
            # All application I/O traps and the evaluator trap remain active.
            with self.subTest(command=command), mock.patch.object(cli.argparse, "_", lambda message: message):
                with IOSpy() as spy, mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    with mock.patch.object(evaluation, "fetch_official", side_effect=AssertionError("fetch")):
                        exit_code = cli.main([command, "--split", "test"])
                self.assertEqual(exit_code, 2)
                self.assertIn("not available in development", stderr.getvalue())
                self.assertEqual(spy.calls, [])


if __name__ == "__main__":
    unittest.main()
