from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.constraints import ConstraintEngine
from lattice.model import Assignment
from lattice.parser import parse_model_data


def load_fixture(name: str):
    return parse_model_data(json.loads((ROOT / "tests" / "fixtures" / name).read_text()))


class ConstraintEngineTests(unittest.TestCase):
    def test_implied_pairs_capture_transitive_conflicts(self) -> None:
        model = load_fixture("constrained.json")
        engine = ConstraintEngine(model)

        self.assertTrue(
            engine.conflicts(
                Assignment(parameter="loyalty", value="gold"),
                Assignment(parameter="card_type", value="N/A"),
            )
        )

    def test_forward_dependency_survives_closure(self) -> None:
        model = load_fixture("constrained.json")
        engine = ConstraintEngine(model)

        requirements = engine.implied_requirements(Assignment(parameter="loyalty", value="gold"))
        self.assertIn(Assignment(parameter="payment_method", value="credit_card"), requirements)

    def test_model_is_feasible(self) -> None:
        model = load_fixture("constrained.json")
        engine = ConstraintEngine(model)
        self.assertTrue(engine.can_complete({}))


if __name__ == "__main__":
    unittest.main()
