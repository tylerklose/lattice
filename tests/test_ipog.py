from __future__ import annotations

import json
import unittest
from itertools import combinations, product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.constraints import ConstraintEngine
from lattice.ipog import generate_covering_array
from lattice.parser import parse_model_data


def load_fixture(name: str):
    return parse_model_data(json.loads((ROOT / "tests" / "fixtures" / name).read_text()))


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


class IpogTests(unittest.TestCase):
    def test_pairwise_generation_covers_simple_model(self) -> None:
        model = load_fixture("simple.json")
        result = generate_covering_array(model, seed=42, pool_size=8)
        verify_coverage(model, result.rows, strength=2)

    def test_strength_three_generation_covers_simple_model(self) -> None:
        model = load_fixture("simple.json")
        model = model.__class__(
            model_name=model.model_name,
            parameters=model.parameters,
            constraints=model.constraints,
            strength=3,
        )
        result = generate_covering_array(model, seed=42, pool_size=8)
        verify_coverage(model, result.rows, strength=3)

    def test_constrained_generation_covers_valid_pairs_and_forced_interaction(self) -> None:
        model = load_fixture("constrained.json")
        result = generate_covering_array(model, seed=42, pool_size=20)
        verify_coverage(model, result.rows, strength=2)

        payment_index = model.parameter_names.index("payment_method")
        browser_index = model.parameter_names.index("browser")
        os_index = model.parameter_names.index("os")
        self.assertTrue(
            any(
                row[payment_index] == model.parameters[payment_index].values.index("apple_pay")
                and row[browser_index] == model.parameters[browser_index].values.index("safari")
                and row[os_index] == model.parameters[os_index].values.index("macos")
                for row in result.rows
            )
        )


if __name__ == "__main__":
    unittest.main()
