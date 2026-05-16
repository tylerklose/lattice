from __future__ import annotations

import unittest
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lattice.parser import ValidationError, parse_model_data


class ParserTests(unittest.TestCase):
    def test_yaml_mapping_parameters_and_conditional_parameter_are_supported(self) -> None:
        raw = yaml.safe_load(
            """
            model_name: checkout
            parameters:
              payment_method: [credit_card, paypal]
              region: [US, UK]
            constraints:
              - type: conditional
                parameter: card_type
                values: [visa, mastercard]
                parent: payment_method
                applies_when: [credit_card]
            strength: 2
            """
        )

        model = parse_model_data(raw)

        self.assertIn("card_type", model.parameter_lookup)
        self.assertEqual(model.parameter_lookup["card_type"].values, ("visa", "mastercard", "N/A"))

    def test_invalid_duplicate_values_raise_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            parse_model_data(
                {
                    "parameters": {
                        "browser": ["chrome", "chrome"],
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
