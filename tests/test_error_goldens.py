from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
# Shared with the Ruby gem (test/fixtures/invalid and test/fixtures/golden/errors
# there), which must report the same error codes and messages.
CASES = sorted(path.stem for path in (FIXTURES / "invalid").glob("*.json"))


class ErrorGoldenTests(unittest.TestCase):
    def test_validate_reports_the_golden_errors(self) -> None:
        self.assertGreater(len(CASES), 30)
        for name in CASES:
            with self.subTest(name=name):
                golden = (FIXTURES / "golden_errors" / f"{name}.json").read_text()
                result = subprocess.run(
                    [sys.executable, "-m", "lattice", "validate", "--format", "json", str(FIXTURES / "invalid" / f"{name}.json")],
                    capture_output=True,
                    text=True,
                    env={"PYTHONPATH": str(ROOT / "src")},
                )
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(json.loads(golden), json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
