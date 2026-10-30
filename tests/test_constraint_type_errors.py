from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.parser import ValidationError, load_model

FIXTURES = ROOT / "tests" / "fixtures"
# Shared with the Ruby implementation (test/fixtures/invalid and
# test/fixtures/golden/errors there), which must print the same messages.
CASES = ["constraint_missing_type", "constraint_type_shorthand", "constraint_type_not_string", "unknown_constraint_type"]


class ConstraintTypeErrorTests(unittest.TestCase):
    def test_messages_match_goldens(self) -> None:
        for name in CASES:
            with self.subTest(name=name):
                golden = json.loads((FIXTURES / "golden_errors" / f"{name}.json").read_text())
                with self.assertRaises(ValidationError) as raised:
                    load_model(str(FIXTURES / "invalid" / f"{name}.json"))
                self.assertEqual(golden["errors"], raised.exception.errors)


if __name__ == "__main__":
    unittest.main()
