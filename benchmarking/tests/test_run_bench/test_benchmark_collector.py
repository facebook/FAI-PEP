# pyre-unsafe

import os
import shutil
import tempfile
import unittest

from benchmarks.benchmarks import BenchmarkCollector


class BenchmarkCollectorCopyFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.collector = BenchmarkCollector(
            framework=None, model_cache=os.path.join(self.tmp, "model_cache")
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _writeSource(self, content: bytes) -> str:
        src = os.path.join(self.tmp, "src", "speech.tuna.mock_flat.fbpkg.lock")
        os.makedirs(os.path.dirname(src))
        with open(src, "wb") as f:
            f.write(content)
        return src

    def test_copyFile_creates_missing_nested_parent_dir(self) -> None:
        # Regression: a filename carrying a nested subpath (e.g. an
        # fbpkg-internal ".fbpkg.tmp/*.fbpkg.lock" artifact) yields a
        # destination whose parent dir does not exist yet. _copyFile used to
        # crash with FileNotFoundError instead of creating the parent.
        content = b"lockdata"
        src = self._writeSource(content)
        model_dir = os.path.join(self.tmp, "model_cache", "pytorch", "[ASR] - f1 - 42")
        os.makedirs(model_dir)
        destination = os.path.join(
            model_dir, ".fbpkg.tmp", "speech.tuna.mock_flat.fbpkg.lock"
        )
        # A non-matching md5 is fine: the file is copied before the md5 check,
        # so the copy (and its parent-dir creation) is what we exercise here.
        field = {
            "location": src,
            "filename": "speech.tuna.mock_flat.fbpkg.lock",
            "md5": "0" * 32,
        }

        self.assertFalse(os.path.isdir(os.path.dirname(destination)))
        self.collector._copyFile(field, destination, source=src)

        self.assertTrue(os.path.isfile(destination))
        with open(destination, "rb") as f:
            self.assertEqual(f.read(), content)
