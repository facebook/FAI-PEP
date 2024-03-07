# pyre-unsafe
import unittest
from unittest.mock import call, MagicMock, patch

from utils import subprocess_with_logger
from utils.subprocess_with_logger import processRun


class SubprocessWithLoggerTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_subprocess_error_logging(self):
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        with patch.object(
            subprocess_with_logger, "getLogger", return_value=mock_logger
        ):
            with patch.object(
                subprocess_with_logger,
                "_getOutput",
                return_value=(["ls: no_such_dir: No such file or directory"], None),
            ), patch.object(
                subprocess_with_logger.subprocess.Popen, "wait", return_value=1
            ):
                ret = processRun(["ls", "no_such_dir"], retry=1, silent=True)
                self.assertEqual(
                    ret, ([], "ls: no_such_dir: No such file or directory")
                )
                mock_logger.info.assert_not_called()
                ret = processRun(["ls", "no_such_dir"], retry=1, silent=False)
                mock_logger.info.assert_has_calls(
                    [
                        call(">>>>>> Running: %s", "ls no_such_dir"),
                        call("Process exited with status: 1"),
                        call(
                            "\n\nProgram Output:\n================================================================================\nls: no_such_dir: No such file or directory\n================================================================================\n"
                        ),
                    ]
                )

    def test_subprocess_success_logging(self):
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        with patch.object(
            subprocess_with_logger, "getLogger", return_value=mock_logger
        ):
            ret = processRun(["echo", "success"], retry=1, silent=False)
            self.assertEqual(ret, (["success"], None))
            mock_logger.info.assert_has_calls(
                [
                    call(">>>>>> Running: %s", "echo success"),
                    call("Process Succeeded: %s", "echo success"),
                ]
            )
