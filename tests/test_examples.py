from __future__ import annotations

import json
import unittest
from itertools import combinations, product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.constraints import ConstraintEngine
from lattice.formatters import render_output
from lattice.ipog import generate_covering_array
from lattice.parser import load_model


def verify_coverage(model, rows, strength: int) -> None:
    engine = ConstraintEngine(model)
    for combo in combinations(range(len(model.parameters)), strength):
        domains = [range(len(model.parameters[index].values)) for index in combo]
        for value_tuple in product(*domains):
            partial = {combo[offset]: value_tuple[offset] for offset in range(strength)}
            if not engine.can_complete(partial):
                continue
            covered = any(
                all(row[combo[offset]] == value_tuple[offset] for offset in range(strength))
                for row in rows
            )
            if not covered:
                raise AssertionError(f"Uncovered tuple for combo {combo}: {value_tuple}")


class ExampleModelTests(unittest.TestCase):
    def test_examples_validate_and_generate(self) -> None:
        example_cases = [
            (
                ROOT / "examples" / "plan-mode-saved-search" / "model.yaml",
                ROOT / "examples" / "plan-mode-saved-search" / "scenarios.json",
            ),
            (
                ROOT / "examples" / "test-mode-checkout" / "model.json",
                ROOT / "examples" / "test-mode-checkout" / "scenarios.json",
            ),
            (
                ROOT / "examples" / "three-way-notifications" / "model.yaml",
                ROOT / "examples" / "three-way-notifications" / "scenarios.json",
            ),
            (
                ROOT / "examples" / "lattice-self-test" / "model.yaml",
                ROOT / "examples" / "lattice-self-test" / "scenarios.json",
            ),
            (
                ROOT / "examples" / "agent-bootstrap-matrix" / "model.yaml",
                ROOT / "examples" / "agent-bootstrap-matrix" / "scenarios.json",
            ),
        ]

        for model_path, scenarios_path in example_cases:
            with self.subTest(model=str(model_path)):
                model = load_model(str(model_path))
                result = generate_covering_array(model, seed=42, pool_size=50)
                verify_coverage(model, result.rows, strength=model.strength)
                rendered = render_output(model, result, output_format="json", seed=42)
                self.assertEqual(json.loads(rendered), json.loads(scenarios_path.read_text()))


if __name__ == "__main__":
    unittest.main()
