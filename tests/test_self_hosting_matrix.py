from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SELF_HOSTING_SCENARIOS = ROOT / "examples" / "lattice-self-test" / "scenarios.json"


def fixture_path(schema_profile: str, schema_encoding: str) -> Path:
    return FIXTURES / f"{schema_profile}.{schema_encoding}"


class SelfHostingMatrixTests(unittest.TestCase):
    def run_cli(self, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "lattice", *args],
            cwd=ROOT,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generated_self_hosting_matrix_exercises_cli(self) -> None:
        scenarios = json.loads(SELF_HOSTING_SCENARIOS.read_text())["scenarios"]

        for scenario in scenarios:
            with self.subTest(scenario=scenario["id"]):
                values = scenario["values"]
                fixture = fixture_path(values["schema_profile"], values["schema_encoding"])
                command = [values["command"]]
                if values["output_format"] != "json" or values["command"] == "validate":
                    command.extend(["--format", values["output_format"]])

                payload = None
                if values["input_source"] == "file":
                    command.append(str(fixture))
                else:
                    payload = fixture.read_text()

                result = self.run_cli(*command, input_text=payload)
                valid_schema = values["schema_profile"] != "invalid"
                expected_exit_code = 0 if valid_schema else 1
                self.assertEqual(result.returncode, expected_exit_code, msg=result.stderr or result.stdout)

                if values["command"] == "validate":
                    self._assert_validate_result(values, result, valid_schema)
                else:
                    self._assert_generate_result(values, result, valid_schema)

    def _assert_validate_result(
        self,
        values: dict[str, str],
        result: subprocess.CompletedProcess[str],
        valid_schema: bool,
    ) -> None:
        if values["output_format"] == "json":
            parsed = json.loads(result.stdout)
            if valid_schema:
                self.assertEqual(parsed["status"], "ok")
                self.assertTrue(parsed["valid"])
            else:
                self.assertEqual(parsed["status"], "error")
                self.assertEqual(parsed["code"], "validation_error")
            return

        if valid_schema:
            self.assertIn("Schema is valid.", result.stdout)
        else:
            self.assertIn("duplicate values", result.stderr)

    def _assert_generate_result(
        self,
        values: dict[str, str],
        result: subprocess.CompletedProcess[str],
        valid_schema: bool,
    ) -> None:
        if values["output_format"] == "json":
            parsed = json.loads(result.stdout)
            if valid_schema:
                self.assertIn("meta", parsed)
                self.assertGreater(parsed["meta"]["test_count"], 0)
            else:
                self.assertEqual(parsed["status"], "error")
                self.assertEqual(parsed["code"], "validation_error")
            return

        if valid_schema:
            self.assertIn("Lattice —", result.stdout)
        else:
            self.assertIn("duplicate values", result.stderr)


if __name__ == "__main__":
    unittest.main()
