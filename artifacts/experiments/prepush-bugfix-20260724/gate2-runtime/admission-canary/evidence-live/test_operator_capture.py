#!/usr/bin/env python3
"""Windows launcher and UTF-8 evidence-capture regressions."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

from capture_command import run_and_capture
from producer_launcher import render_launcher


@unittest.skipUnless(os.name == "nt", "cmd.exe regression is Windows-specific")
class LauncherExitCapture(unittest.TestCase):
    def test_zero_and_multidigit_exit_codes_are_captured_exactly(self):
        for code in (0, 12):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as td:
                child = os.path.join(td, "child.cmd")
                launcher = os.path.join(td, "launcher.cmd")
                prompt = os.path.join(td, "prompt.txt")
                stdout = os.path.join(td, "stdout.txt")
                stderr = os.path.join(td, "stderr.txt")
                exit_file = os.path.join(td, "exit.txt")
                with open(child, "w", encoding="utf-8", newline="") as handle:
                    handle.write(f"@exit /b {code}\r\n")
                with open(prompt, "wb") as handle:
                    handle.write(b"prompt")
                rendered = render_launcher(
                    [child],
                    prompt=prompt,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code_out=exit_file,
                )
                with open(launcher, "w", encoding="utf-8", newline="") as handle:
                    handle.write(rendered)

                completed = subprocess.run(
                    [os.environ["COMSPEC"], "/d", "/c", launcher],
                    check=False,
                )
                self.assertEqual(completed.returncode, code)
                with open(exit_file, encoding="utf-8") as handle:
                    self.assertEqual(handle.read().strip(), str(code))

    def test_redirection_precedes_echo(self):
        rendered = render_launcher(
            ["child.cmd"],
            prompt=r"C:\prompt.txt",
            stdout=r"C:\stdout.txt",
            stderr=r"C:\stderr.txt",
            exit_code_out=r"C:\exit.txt",
        )
        self.assertIn('> "C:\\exit.txt" echo %claudeExit%', rendered)
        self.assertNotIn("echo %errorlevel%>", rendered)


class Utf8Capture(unittest.TestCase):
    def test_stdout_stderr_and_multidigit_exit_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            stdout = os.path.join(td, "stdout.txt")
            stderr = os.path.join(td, "stderr.txt")
            exit_file = os.path.join(td, "exit.txt")
            code = (
                "import sys;"
                "sys.stdout.buffer.write('out — utf8\\n'.encode());"
                "sys.stderr.buffer.write('err — utf8\\n'.encode());"
                "raise SystemExit(12)"
            )
            rc = run_and_capture(
                [sys.executable, "-c", code],
                stdout_path=stdout,
                stderr_path=stderr,
                exit_code_path=exit_file,
            )
            self.assertEqual(rc, 12)
            with open(stdout, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "out — utf8\n")
            with open(stderr, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "err — utf8\n")
            with open(exit_file, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "12\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
