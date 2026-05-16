from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.model import Parameter, normalize_scalar


class ModelTests(unittest.TestCase):
    def test_normalize_scalar_canonicalizes_yaml_scalars(self) -> None:
        self.assertEqual(normalize_scalar(True), "true")
        self.assertEqual(normalize_scalar(False), "false")
        self.assertEqual(normalize_scalar(None), "null")
        self.assertEqual(normalize_scalar(7), "7")

    def test_parameter_normalizes_weights(self) -> None:
        parameter = Parameter(name="browser", values=("chrome", "safari"), weights=(0.7, 0.3))
        self.assertEqual(parameter.normalized_weights, (0.7, 0.3))


if __name__ == "__main__":
    unittest.main()
