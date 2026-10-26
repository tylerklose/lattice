from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

from lattice.formatters import _yaml_string, format_json, format_yaml, render_output
from lattice.ipog import GenerationResult, generate_covering_array
from lattice.parser import load_model


def uescape(hex_digits: str) -> str:
    # Built in pieces so the source stays ASCII.
    return '"' + "\\" + "u" + hex_digits + '"'


def quoted(*code_points: int) -> str:
    return '"' + "".join(chr(point) for point in code_points) + '"'


class YamlFormatTests(unittest.TestCase):
    """`--format yaml`: the same content as `--format json`, written by hand.

    tests/fixtures/yaml_edges.golden.yaml pins the exact bytes for
    tests/fixtures/yaml_edges.json; the Ruby gem (latticerb) tests against
    the same pair.
    """

    def generate(self, fixture: str):
        model = load_model(str(FIXTURES / fixture))
        return model, generate_covering_array(model, strength=model.strength, seed=42, pool_size=50)

    def test_edge_case_fixture_matches_golden_bytes(self) -> None:
        model, result = self.generate("yaml_edges.json")
        golden = (FIXTURES / "yaml_edges.golden.yaml").read_text(encoding="utf-8")
        self.assertEqual(format_yaml(model, result, seed=42) + "\n", golden)

    def test_yaml_reads_back_as_the_json_payload(self) -> None:
        for fixture in ("simple.json", "constrained.json", "skillit.json", "yaml_edges.json"):
            with self.subTest(fixture=fixture):
                model, result = self.generate(fixture)
                self.assertEqual(
                    yaml.safe_load(format_yaml(model, result, seed=42)),
                    json.loads(format_json(model, result, seed=42)),
                )

    def test_empty_result_writes_empty_lists_and_null_seed(self) -> None:
        model = load_model(str(FIXTURES / "simple.json"))
        result = GenerationResult(rows=(), coverage_curve=(), total_valid_tuples=0)
        expected = "\n".join(
            [
                "meta:",
                '  model_name: "simple"',
                "  strength: 2",
                "  test_count: 0",
                "  exhaustive_count: 8",
                '  reduction: "inf"',
                '  coverage: "0.0%"',
                "  seed: null",
                "coverage_curve: []",
                "scenarios: []",
            ]
        )
        self.assertEqual(render_output(model, result, output_format="yaml", seed=None), expected)

    def test_yaml_string_escapes(self) -> None:
        backslash = "\\"
        cases = {
            "plain": '"plain"',
            "": '""',
            "yes": '"yes"',
            "~": '"~"',
            'say "hi"': '"say ' + backslash + '"hi' + backslash + '""',
            "back" + backslash + "slash": '"back' + backslash * 2 + 'slash"',
            chr(0x08): '"' + backslash + 'b"',
            chr(0x09): '"' + backslash + 't"',
            chr(0x0A): '"' + backslash + 'n"',
            chr(0x0C): '"' + backslash + 'f"',
            chr(0x0D): '"' + backslash + 'r"',
            chr(0x00): uescape("0000"),
            chr(0x07): uescape("0007"),
            chr(0x0B): uescape("000b"),
            chr(0x1F): uescape("001f"),
            chr(0x7E): '"~"',
            chr(0x7F): uescape("007f"),
            chr(0x80): uescape("0080"),
            chr(0x85): uescape("0085"),
            chr(0x9F): uescape("009f"),
            chr(0xA0): quoted(0xA0),
            "caf" + chr(0xE9): quoted(0x63, 0x61, 0x66, 0xE9),
            chr(0x2027): quoted(0x2027),
            chr(0x2028): uescape("2028"),
            chr(0x2029): uescape("2029"),
            chr(0x202A): quoted(0x202A),
            chr(0xFEFF): uescape("feff"),
            chr(0xFFFD): quoted(0xFFFD),
            chr(0xFFFE): uescape("fffe"),
            chr(0xFFFF): uescape("ffff"),
            chr(0x1F600): quoted(0x1F600),
        }
        for value, expected in cases.items():
            with self.subTest(value=ascii(value)):
                self.assertEqual(_yaml_string(value), expected)

    def test_cli_generate_format_yaml(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-m", "lattice", "generate", "--format", "yaml", str(FIXTURES / "yaml_edges.json")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, (FIXTURES / "yaml_edges.golden.yaml").read_bytes())


if __name__ == "__main__":
    unittest.main()
