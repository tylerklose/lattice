from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

from lattice.formatters import format_json
from lattice.ipog import generate_covering_array
from lattice.parser import ValidationError, load_model, parse_model_data
from lattice.schema_text import SchemaSyntaxError, load_json, load_yaml


def values(model):
    return {parameter.name: list(parameter.values) for parameter in model.parameters}


class SchemaTextTests(unittest.TestCase):
    """Schema values keep the text the user wrote (lattice.schema_text).

    The Ruby gem runs the same cases in test/schema_text_test.rb, and
    tests/fixtures/scalar_text.* is shared between the two.
    """

    def test_yaml_fixture_keeps_value_text(self) -> None:
        model = load_model(str(FIXTURES / "scalar_text.yaml"))
        self.assertEqual(
            values(model),
            {
                "numbers": ["1.10", "0x1F", "012", "1_000", "1e3", "1.0e+20", ".inf", "-.inf", ".nan", "1:30", "+12", "-0"],
                "times": ["2026-10-26", "2026-10-26 10:00:00", "2026-10-26T10:00:00Z", "2026-10-26T10:00:00+02:00"],
                "words": ["true", "false", "null", "yEs", "nO", "y", "yes"],
                "tagged": ["=", "<<", "yes", "07", "1.5"],
                "1.10": ["x", "y"],
                "true": ["p", "q"],
                "weighted": ["a", "b"],
                "merged": ["c", "d"],
            },
        )
        self.assertEqual(model.parameter_lookup["merged"].weights, (0.7, 3.0))

    def test_yaml_fixture_output_matches_golden(self) -> None:
        model = load_model(str(FIXTURES / "scalar_text.yaml"))
        result = generate_covering_array(model, strength=model.strength, seed=42, pool_size=50)
        golden = (FIXTURES / "scalar_text.golden.json").read_text(encoding="utf-8")
        self.assertEqual(format_json(model, result, seed=42) + "\n", golden)

    def test_json_fixture_keeps_number_text(self) -> None:
        model = load_model(str(FIXTURES / "scalar_text.json"))
        self.assertEqual(
            values(model),
            {
                "numbers": ["1.10", "1e20", "1E5", "0", "100000000000000000000.0", "12", "0.1", "-2.50"],
                "literals": ["true", "false", "null", "true!"],
                "weighted": ["a", "b"],
            },
        )
        self.assertEqual(model.parameter_lookup["weighted"].weights, (0.25, 2.0))

    def test_yaml_words(self) -> None:
        words = "yes Yes YES true True TRUE on On ON no No NO false False FALSE off Off OFF ~ null Null NULL yEs nULL y n".split()
        expected = [True] * 9 + [False] * 9 + [None] * 4 + ["yEs", "nULL", "y", "n"]
        self.assertEqual(load_yaml("[" + ", ".join(words) + "]"), expected)
        self.assertEqual(load_yaml("a:\nb: ''\n"), {"a": None, "b": ""})
        self.assertEqual(load_yaml("[\"yes\", 'null', !!str on]"), ["yes", "null", "on"])
        self.assertEqual(load_yaml("[! true, ! x]"), ["true", "x"])
        self.assertEqual(load_yaml("[!!bool yes, !!bool maybe]"), [True, "maybe"])

    def test_yaml_block_and_folded_scalars_keep_text(self) -> None:
        self.assertEqual(load_yaml("a: |\n  yes\nb: >\n  1.10\n"), {"a": "yes\n", "b": "1.10\n"})

    def test_yaml_empty_document(self) -> None:
        self.assertIsNone(load_yaml(""))
        self.assertIsNone(load_yaml("# only a comment\n"))

    def test_yaml_aliases_and_merges(self) -> None:
        data = load_yaml(
            "base: &base {x: 1, y: 2}\n"
            "other: &other {y: 3, z: 4}\n"
            "list: &list [a, b]\n"
            "copy: *list\n"
            "one: {<<: *base, x: 9}\n"
            "many: {<<: [*base, *other], w: 0}\n"
        )
        self.assertEqual(data["copy"], ["a", "b"])
        self.assertEqual(data["one"], {"x": "9", "y": "2"})
        self.assertEqual(data["many"], {"x": "1", "y": "2", "z": "4", "w": "0"})
        self.assertEqual(list(data["many"]), ["x", "y", "z", "w"])

    def test_yaml_merge_key_must_be_plain_untagged_or_merge_tagged(self) -> None:
        self.assertEqual(load_yaml('{"<<": {x: 1}}'), {"<<": {"x": "1"}})
        self.assertEqual(load_yaml("{!!str <<: {x: 1}}"), {"<<": {"x": "1"}})
        self.assertEqual(load_yaml("{!!merge <<: {x: 1}}"), {"x": "1"})

    def test_yaml_alias_as_key(self) -> None:
        self.assertEqual(load_yaml("k: &m x\nmap: {*m : 1}\n"), {"k": "x", "map": {"x": "1"}})

    def test_yaml_errors(self) -> None:
        cases = {
            "a: 1\na: 2\n": "duplicate key `a`",
            "yes: 1\nYES: 2\n": "duplicate key `true`",
            "~: 1\nnull: 2\n": "duplicate key `null`",
            "a: !foo x\n": "unsupported YAML tag `!foo`",
            "a: !!set {x}\n": "unsupported YAML tag `tag:yaml.org,2002:set`",
            "a: !!omap [x: 1]\n": "unsupported YAML tag `tag:yaml.org,2002:omap`",
            "? [a]\n: b\n": "mapping keys must be scalars",
            "? {a: 1}\n: b\n": "mapping keys must be scalars",
            "a: {<<: [{x: 1}, y]}\n": "merge key `<<` needs a mapping or a list of mappings",
            "a: {<<: [[{x: 1}]]}\n": "merge key `<<` needs a mapping or a list of mappings",
            "a: {<<: [x]}\n": "merge key `<<` needs a mapping or a list of mappings",
            "a: {<<: {x: 1}, <<: {y: 2}}\n": "duplicate key `<<`",
            "a: &r [*r]\n": "recursive alias",
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(SchemaSyntaxError) as raised:
                    load_yaml(text)
                self.assertEqual(str(raised.exception), message)
        # PyYAML itself rejects these (Ruby reports them as SchemaText errors).
        for text in ("a: 1\n---\nb: 2\n", "a: *nope\n"):
            with self.subTest(text=text):
                with self.assertRaises(Exception):
                    load_yaml(text)

    def test_json_errors(self) -> None:
        for text in ('{"a": 1, "a": 2}', "[NaN]", "[Infinity]", "[-Infinity]"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    load_json(text)

    def test_json_nesting_and_literals(self) -> None:
        self.assertEqual(
            load_json('{"a": [{"b": 1.5}, 7, true, null, "s"]}'),
            {"a": [{"b": "1.5"}, "7", True, None, "s"]},
        )

    def weight_errors(self, weights):
        try:
            parse_model_data({"parameters": {"a": {"values": ["x", "y"], "weights": weights}}, "strength": 1})
        except ValidationError as error:
            return error.errors
        return None

    def test_weight_text(self) -> None:
        self.assertIsNone(self.weight_errors(["0.7", "3"]))
        self.assertIsNone(self.weight_errors(["+1.5e-1", "007"]))
        self.assertIsNone(self.weight_errors([0.5, 2]))
        numeric = ["`weights` for parameter `a` must be numeric."]
        for weights in (
            ["0x10", "1"], ["1_0", "1"], [".5", "1"], ["1.", "1"], ["inf", "1"], ["1e400", "1"],
            [True, "1"], [None, "1"], [math.inf, 1], [math.nan, 1], ["\u0661", "1"],
        ):
            with self.subTest(weights=weights):
                self.assertEqual(self.weight_errors(weights), numeric)
        self.assertEqual(self.weight_errors(["0", "1"]), ["`weights` for parameter `a` must be greater than zero."])
        self.assertEqual(self.weight_errors(["-1", "1"]), ["`weights` for parameter `a` must be greater than zero."])

    def strength_result(self, strength):
        try:
            return parse_model_data(
                {"parameters": {"a": ["x", "y"], "b": ["x", "y"], "c": ["x", "y"]}, "strength": strength}
            ).strength
        except ValidationError as error:
            return error.errors

    def test_strength_text(self) -> None:
        self.assertEqual(self.strength_result("3"), 3)
        self.assertEqual(self.strength_result("+2"), 2)
        self.assertEqual(self.strength_result("01"), 1)
        self.assertEqual(self.strength_result(2), 2)
        self.assertEqual(self.strength_result(2.9), 2)
        self.assertEqual(self.strength_result(None), 2)
        for strength in ("2.0", "0x2", "1_0", "two", True, math.inf, [2]):
            with self.subTest(strength=strength):
                self.assertEqual(self.strength_result(strength), ["`strength` must be an integer."])


if __name__ == "__main__":
    unittest.main()
