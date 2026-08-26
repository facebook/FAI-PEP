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

    def _writeSource(
        self,
        content: bytes,
        directory: str = "src",
        filename: str = "speech.tuna.mock_flat.fbpkg.lock",
    ) -> str:
        src = os.path.join(self.tmp, directory, filename)
        os.makedirs(os.path.dirname(src), exist_ok=True)
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

    def test_updateFiles_isolates_same_filename_by_content_hash(self) -> None:
        benchmark_file = self._writeSource(
            b"{}", directory="benchmark", filename="benchmark.json"
        )
        drama_source = self._writeSource(
            b"drama", directory="drama", filename="tokenizer.json"
        )
        wordpiece_source = self._writeSource(
            b"wordpiece", directory="wordpiece", filename="tokenizer.json"
        )
        drama = {
            "location": drama_source,
            "filename": "tokenizer.json",
            "md5": "0" * 32,
        }
        wordpiece = {
            "location": wordpiece_source,
            "filename": "tokenizer.json",
            "md5": self.collector._calcalateFileMD5(wordpiece_source),
        }
        benchmark = {
            "model": {
                "files": {"drama": drama, "wordpiece": wordpiece},
                "format": "pytorch",
                "name": "API Benchmark",
            },
            "tests": [],
        }

        self.collector._updateFiles(benchmark, benchmark_file, "test")

        drama_path = benchmark["model"]["files"]["drama"]["location"]
        wordpiece_path = benchmark["model"]["files"]["wordpiece"]["location"]
        self.assertEqual(os.path.basename(os.path.dirname(drama_path)), drama["md5"])
        self.assertNotEqual(drama_path, wordpiece_path)
        with open(drama_path, "rb") as f:
            self.assertEqual(f.read(), b"drama")
        with open(wordpiece_path, "rb") as f:
            self.assertEqual(f.read(), b"wordpiece")
