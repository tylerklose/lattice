from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "examples" / "schema-guidance-matrix" / "scenarios.json"


BAD_CONDITIONAL_SCHEMA = """
model_name: bad_conditional
parameters:
  mode: [basic, advanced]
  aggregation_level: [none, low, high]
constraints:
  - type: conditional
    parameter: aggregation_level
    values: [low, high]
    parent: mode
    applies_when: [advanced]
"""


class SchemaGuidanceMatrixTests(unittest.TestCase):
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

    def test_generated_schema_guidance_matrix(self) -> None:
        scenarios = json.loads(SCENARIOS.read_text())["scenarios"]

        for scenario in scenarios:
            values = scenario["values"]
            with self.subTest(scenario=scenario["id"], values=values):
                surface_text = self._surface_text(values["surface"])
                self.assertIn(self._expected_fragment(values["assertion"]), surface_text)

    def _surface_text(self, surface: str) -> str:
        if surface == "generate_help":
            result = self.run_cli("generate", "--help")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            return result.stdout

        if surface == "validate_help":
            result = self.run_cli("validate", "--help")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            return result.stdout

        if surface == "agent_instructions":
            result = self.run_cli("agent", "instructions", "--format", "json")
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            return "\n".join([payload["instructions"], payload["memory"], payload["default_prompt"]])

        if surface == "install_generic_skill":
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / "lattice-workflow"
                result = self.run_cli("agent", "install-skill", str(target), "--format", "json")
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                return "\n".join(
                    [
                        (target / "SKILL.md").read_text(),
                        (target / "references" / "modeling-rules.md").read_text(),
                    ]
                )

        if surface == "repo_local_skill":
            skill = ROOT / ".codex" / "skills" / "lattice-workflow"
            return "\n".join(
                [
                    (skill / "SKILL.md").read_text(),
                    (skill / "references" / "modeling-rules.md").read_text(),
                ]
            )

        if surface == "conditional_conflict_error":
            result = self.run_cli("validate", "--format", "text", input_text=BAD_CONDITIONAL_SCHEMA)
            self.assertEqual(result.returncode, 1)
            return result.stdout + result.stderr

        raise AssertionError(f"Unknown schema guidance surface: {surface}")

    def _expected_fragment(self, assertion: str) -> str:
        fragments = {
            "schema_features": "Schema features",
            "invalid_pair": "invalid_pair",
            "higher_order": "higher_order",
            "forward_dep": "forward_dep",
            "no_strip_constraints": "Do not strip",
            "conditional_child_parameter": "Use `conditional` only to define a child parameter",
            "full_schema_reference": "lattice agent instructions",
        }
        return fragments[assertion]


if __name__ == "__main__":
    unittest.main()
