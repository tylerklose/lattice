from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

SKILL_NAME = "lattice-workflow"

MEMORY_SNIPPET = (
    "Reach for Lattice when planning or testing behavior with interacting states such as "
    "roles, permissions, feature flags, modes, providers, optional fields, validation "
    "branches, lifecycle states, or cross-product edge cases. Extract a schema with "
    "parameters, values, and true constraints; run `lattice validate`; then run "
    "`lattice generate`; use the generated rows as the source of truth for plan review "
    "or missing tests instead of hand-enumerating pairwise combinations."
)

DEFAULT_PROMPT = (
    "Use $lattice-workflow. Inspect this feature or test surface, extract a Lattice "
    "schema, validate it, generate pairwise scenarios, and use the rows to strengthen "
    "the plan or tests."
)


@dataclass(frozen=True)
class AgentSetup:
    surface: str
    skill_name: str
    skill_path: Path
    memory: str
    default_prompt: str

    def to_json(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "skill_name": self.skill_name,
            "skill_path": str(self.skill_path),
            "memory": self.memory,
            "default_prompt": self.default_prompt,
        }


def default_codex_skill_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "skills" / SKILL_NAME


def default_claude_skill_path() -> Path:
    return Path.home() / ".claude" / "skills" / SKILL_NAME


def codex_available() -> bool:
    return shutil.which("codex") is not None or (Path.home() / ".codex").exists() or bool(os.environ.get("CODEX_HOME"))


def claude_code_available() -> bool:
    return shutil.which("claude") is not None or (Path.home() / ".claude").exists()


def install_codex_skill(target: str | None = None) -> AgentSetup:
    destination = Path(target).expanduser() if target else default_codex_skill_path()
    source = files("lattice") / "resources" / "codex" / SKILL_NAME
    if not source.is_dir():
        raise FileNotFoundError(f"Bundled Codex skill `{SKILL_NAME}` was not found.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return AgentSetup(
        surface="codex",
        skill_name=SKILL_NAME,
        skill_path=destination,
        memory=MEMORY_SNIPPET,
        default_prompt=DEFAULT_PROMPT,
    )


def install_claude_skill(target: str | None = None, *, force: bool = False) -> AgentSetup:
    if not force and not claude_code_available():
        raise RuntimeError("Claude Code was not detected. Re-run with --force to install anyway.")

    destination = Path(target).expanduser() if target else default_claude_skill_path()
    source = files("lattice") / "resources" / "claude" / SKILL_NAME
    if not source.is_dir():
        raise FileNotFoundError(f"Bundled Claude skill `{SKILL_NAME}` was not found.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=True)
    return AgentSetup(
        surface="claude-code",
        skill_name=SKILL_NAME,
        skill_path=destination,
        memory=MEMORY_SNIPPET,
        default_prompt=DEFAULT_PROMPT,
    )


def codex_skill_installed(target: str | None = None) -> bool:
    destination = Path(target).expanduser() if target else default_codex_skill_path()
    return (destination / "SKILL.md").is_file()


def claude_skill_installed(target: str | None = None) -> bool:
    destination = Path(target).expanduser() if target else default_claude_skill_path()
    return (destination / "SKILL.md").is_file()
