from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class CliTests(unittest.TestCase):
    def run_cli(
        self,
        *args: str,
        input_text: str | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT / "src")
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, "-m", "lattice", *args],
            cwd=ROOT,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_validate_command_accepts_file_input(self) -> None:
        result = self.run_cli("validate", str(FIXTURES / "simple.json"))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["status"], "ok")
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["schema"]["name"], "simple")

    def test_generate_defaults_to_json_and_accepts_stdin(self) -> None:
        payload = (FIXTURES / "skillit.json").read_text()
        result = self.run_cli("generate", input_text=payload)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["meta"]["model_name"], "saved_search_slugs")
        self.assertGreater(parsed["meta"]["test_count"], 0)

    def test_validate_can_render_text_for_humans(self) -> None:
        result = self.run_cli("validate", "--format", "text", str(FIXTURES / "simple.json"))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Schema is valid.", result.stdout)

    def test_invalid_schema_returns_structured_json_error(self) -> None:
        result = self.run_cli(
            "validate",
            "--format",
            "json",
            input_text=json.dumps({"parameters": {"browser": ["chrome", "chrome"]}}),
        )
        self.assertEqual(result.returncode, 1)
        parsed = json.loads(result.stdout)
        self.assertEqual(parsed["status"], "error")
        self.assertEqual(parsed["code"], "validation_error")
        self.assertTrue(any("duplicate values" in error for error in parsed["errors"]))

    def test_agent_memory_prints_reach_for_lattice_guidance(self) -> None:
        result = self.run_cli("agent", "memory")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("Reach for Lattice", result.stdout)
        self.assertIn("lattice validate", result.stdout)

    def test_agent_installs_bundled_codex_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "lattice-workflow"
            result = self.run_cli(
                "agent",
                "install-codex-skill",
                "--target",
                str(target),
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["status"], "ok")
            self.assertEqual(parsed["skill_name"], "lattice-workflow")
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "agents" / "openai.yaml").is_file())
            self.assertTrue((target / "references" / "modeling-rules.md").is_file())

    def test_agent_installs_bundled_claude_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "lattice-workflow"
            result = self.run_cli(
                "agent",
                "install-claude-skill",
                "--target",
                str(target),
                "--force",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["status"], "ok")
            self.assertEqual(parsed["surface"], "claude-code")
            self.assertEqual(parsed["skill_name"], "lattice-workflow")
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "references" / "modeling-rules.md").is_file())

    def test_agent_doctor_checks_codex_skill_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_dir = Path(temp_dir) / "bin"
            bin_dir.mkdir()
            for command in ("codex", "claude"):
                executable = bin_dir / command
                executable.write_text("#!/bin/sh\nexit 0\n")
                executable.chmod(0o755)

            codex_target = Path(temp_dir) / "codex" / "lattice-workflow"
            claude_target = Path(temp_dir) / "claude" / "lattice-workflow"
            env = {
                "CODEX_HOME": "",
                "HOME": str(Path(temp_dir) / "home"),
                "PATH": str(bin_dir),
            }

            missing = self.run_cli(
                "agent",
                "doctor",
                "--target",
                str(codex_target),
                "--claude-target",
                str(claude_target),
                "--format",
                "json",
                env_overrides=env,
            )
            self.assertEqual(missing.returncode, 1)
            missing_payload = json.loads(missing.stdout)
            self.assertEqual(missing_payload["status"], "missing")

            codex = self.run_cli("agent", "install-codex-skill", "--target", str(codex_target), env_overrides=env)
            self.assertEqual(codex.returncode, 0, msg=codex.stderr)

            claude = self.run_cli("agent", "install-claude-skill", "--target", str(claude_target), env_overrides=env)
            self.assertEqual(claude.returncode, 0, msg=claude.stderr)

            ok = self.run_cli(
                "agent",
                "doctor",
                "--target",
                str(codex_target),
                "--claude-target",
                str(claude_target),
                "--format",
                "json",
                env_overrides=env,
            )
            self.assertEqual(ok.returncode, 0, msg=ok.stderr)
            ok_payload = json.loads(ok.stdout)
            self.assertEqual(ok_payload["status"], "ok")
            self.assertTrue(ok_payload["codex_skill_installed"])
            self.assertTrue(ok_payload["claude_skill_installed"])

    def test_agent_bootstrap_can_skip_claude_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_target = Path(temp_dir) / "codex" / "lattice-workflow"
            result = self.run_cli(
                "agent",
                "bootstrap",
                "--target",
                str(codex_target),
                "--force-codex",
                "--skip-claude",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["status"], "ok")
            self.assertTrue((codex_target / "SKILL.md").is_file())
            self.assertFalse(parsed["claude"]["installed"])
            self.assertEqual(parsed["claude"]["skipped_reason"], "skipped by --skip-claude")

    def test_agent_bootstrap_can_skip_codex_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_target = Path(temp_dir) / "claude" / "lattice-workflow"
            result = self.run_cli(
                "agent",
                "bootstrap",
                "--skip-codex",
                "--claude-target",
                str(claude_target),
                "--force-claude",
                "--format",
                "json",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["status"], "ok")
            self.assertFalse(parsed["codex"]["installed"])
            self.assertEqual(parsed["codex"]["skipped_reason"], "skipped by --skip-codex")
            self.assertTrue((claude_target / "SKILL.md").is_file())

    def test_agent_bootstrap_installs_only_detected_harnesses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_dir = Path(temp_dir) / "bin"
            bin_dir.mkdir()
            claude = bin_dir / "claude"
            claude.write_text("#!/bin/sh\nexit 0\n")
            claude.chmod(0o755)

            codex_target = Path(temp_dir) / "codex" / "lattice-workflow"
            claude_target = Path(temp_dir) / "claude" / "lattice-workflow"
            result = self.run_cli(
                "agent",
                "bootstrap",
                "--target",
                str(codex_target),
                "--claude-target",
                str(claude_target),
                "--format",
                "json",
                env_overrides={
                    "CODEX_HOME": "",
                    "HOME": str(Path(temp_dir) / "home"),
                    "PATH": str(bin_dir),
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            parsed = json.loads(result.stdout)
            self.assertFalse(parsed["codex"]["available"])
            self.assertFalse(parsed["codex"]["installed"])
            self.assertEqual(parsed["codex"]["skill_path"], str(codex_target))
            self.assertEqual(parsed["codex"]["skipped_reason"], "Codex was not detected")
            self.assertTrue(parsed["claude"]["available"])
            self.assertTrue(parsed["claude"]["installed"])
            self.assertFalse((codex_target / "SKILL.md").exists())
            self.assertTrue((claude_target / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
