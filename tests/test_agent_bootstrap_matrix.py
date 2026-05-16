from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "examples" / "agent-bootstrap-matrix" / "scenarios.json"


class AgentBootstrapMatrixTests(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "lattice", *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generated_agent_bootstrap_matrix(self) -> None:
        scenarios = json.loads(SCENARIOS.read_text())["scenarios"]

        for scenario in scenarios:
            values = scenario["values"]
            with self.subTest(scenario=scenario["id"], values=values):
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir)
                    env = self._make_env(temp_path, values)
                    codex_target = temp_path / "targets" / "codex" / "lattice-workflow"
                    claude_target = temp_path / "targets" / "claude" / "lattice-workflow"
                    command = ["agent", "bootstrap"]

                    if values["target_mode"] == "explicit":
                        command.extend(["--target", str(codex_target)])
                        command.extend(["--claude-target", str(claude_target)])

                    self._apply_directive(command, "codex", values["codex_directive"])
                    self._apply_directive(command, "claude", values["claude_directive"])

                    if values["output_format"] == "json":
                        command.extend(["--format", "json"])

                    result = self.run_cli(*command, env=env)
                    self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

                    expected_codex = self._expected_installed(values["codex_detection"], values["codex_directive"])
                    expected_claude = self._expected_installed(values["claude_detection"], values["claude_directive"])
                    expected_codex_path = self._expected_codex_path(temp_path, codex_target, values["target_mode"])
                    expected_claude_path = self._expected_claude_path(temp_path, claude_target, values["target_mode"])

                    self.assertEqual((expected_codex_path / "SKILL.md").is_file(), expected_codex)
                    self.assertEqual((expected_claude_path / "SKILL.md").is_file(), expected_claude)

                    if values["output_format"] == "json":
                        payload = json.loads(result.stdout)
                        self.assertEqual(payload["status"], "ok")
                        self.assertEqual(payload["codex"]["available"], values["codex_detection"] == "available")
                        self.assertEqual(payload["claude"]["available"], values["claude_detection"] == "available")
                        self.assertEqual(payload["codex"]["installed"], expected_codex)
                        self.assertEqual(payload["claude"]["installed"], expected_claude)
                        self.assertEqual(payload["codex"]["skill_path"], str(expected_codex_path))
                        self.assertEqual(payload["claude"]["skill_path"], str(expected_claude_path))
                        self.assertIn("Reach for Lattice", payload["memory"])
                        self.assertIn("$lattice-workflow", payload["default_prompt"])
                    else:
                        self.assertIn("Agent memory:", result.stdout)
                        self.assertIn("Default prompt:", result.stdout)
                        self.assertIn("Codex skill:", result.stdout) if not expected_codex else self.assertIn("Codex skill at", result.stdout)
                        self.assertIn("Claude Code skill:", result.stdout) if not expected_claude else self.assertIn("Claude Code skill at", result.stdout)

    def _make_env(self, temp_path: Path, values: dict[str, str]) -> dict[str, str]:
        bin_dir = temp_path / "bin"
        bin_dir.mkdir()
        if values["codex_detection"] == "available":
            self._write_fake_executable(bin_dir / "codex")
        if values["claude_detection"] == "available":
            self._write_fake_executable(bin_dir / "claude")

        env = dict(os.environ)
        env.update(
            {
                "CODEX_HOME": "",
                "HOME": str(temp_path / "home"),
                "PATH": str(bin_dir),
                "PYTHONPATH": str(ROOT / "src"),
            }
        )
        return env

    def _write_fake_executable(self, path: Path) -> None:
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)

    def _apply_directive(self, command: list[str], harness: str, directive: str) -> None:
        if directive == "force":
            command.append(f"--force-{harness}")
        elif directive == "skip":
            command.append(f"--skip-{harness}")

    def _expected_installed(self, detection: str, directive: str) -> bool:
        if directive == "skip":
            return False
        if directive == "force":
            return True
        return detection == "available"

    def _expected_codex_path(self, temp_path: Path, explicit_target: Path, target_mode: str) -> Path:
        if target_mode == "explicit":
            return explicit_target
        return temp_path / "home" / ".codex" / "skills" / "lattice-workflow"

    def _expected_claude_path(self, temp_path: Path, explicit_target: Path, target_mode: str) -> Path:
        if target_mode == "explicit":
            return explicit_target
        return temp_path / "home" / ".claude" / "skills" / "lattice-workflow"


if __name__ == "__main__":
    unittest.main()
