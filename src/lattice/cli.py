from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from lattice.agent import (
    DEFAULT_PROMPT,
    MEMORY_SNIPPET,
    claude_code_available,
    claude_skill_installed,
    codex_available,
    codex_skill_installed,
    default_claude_skill_path,
    default_codex_skill_path,
    install_claude_skill,
    install_codex_skill,
)
from lattice.constraints import ConstraintEngine, ConstraintError
from lattice.formatters import render_output
from lattice.ipog import generate_covering_array
from lattice.parser import ModelIOError, ValidationError, load_model


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "agent":
        return _run_agent_command(args)

    try:
        model = load_model(args.model, strength_override=getattr(args, "strength", None))
        engine = ConstraintEngine(model)
        if not engine.can_complete({}):
            raise ValidationError(["Model has no valid complete assignments."])
    except ValidationError as exc:
        return _emit_error(args, "validation_error", exc.errors, exit_code=1)
    except ConstraintError as exc:
        return _emit_error(args, "constraint_error", [str(exc)], exit_code=1)
    except ModelIOError as exc:
        return _emit_error(args, "io_error", [str(exc)], exit_code=2)

    if args.command == "validate":
        _print_validation_success(args, model)
        return 0

    try:
        result = generate_covering_array(
            model,
            strength=model.strength,
            seed=args.seed,
            pool_size=args.pool_size,
        )
    except ValueError as exc:
        return _emit_error(args, "generation_error", [str(exc)], exit_code=1)

    print(render_output(model, result, output_format=args.format, seed=args.seed))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lattice")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate deterministic scenarios from a schema.")
    generate.add_argument("model", nargs="?", help="Path to a JSON or YAML schema. Reads stdin when omitted.")
    generate.add_argument("--strength", type=int, help="Override the schema strength.")
    generate.add_argument("--format", default="json", choices=("table", "json", "csv", "summary"))
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--pool-size", type=int, default=50)

    validate = subparsers.add_parser("validate", help="Validate a schema without generating scenarios.")
    validate.add_argument("model", nargs="?", help="Path to a JSON or YAML schema. Reads stdin when omitted.")
    validate.add_argument("--strength", type=int, help="Override the schema strength.")
    validate.add_argument("--format", default="json", choices=("json", "text"))

    agent = subparsers.add_parser("agent", help="Install and describe coding-agent integrations.")
    agent_subparsers = agent.add_subparsers(dest="agent_command", required=True)

    bootstrap = agent_subparsers.add_parser("bootstrap", help="Install skills for detected agent harnesses and print the agent memory.")
    bootstrap.add_argument("--target", help="Codex skill directory. Defaults to $CODEX_HOME or ~/.codex.")
    bootstrap.add_argument("--claude-target", help="Claude Code skill directory. Defaults to ~/.claude/skills.")
    bootstrap.add_argument("--force-codex", action="store_true", help="Install the Codex skill even if Codex is not detected.")
    bootstrap.add_argument("--skip-codex", action="store_true", help="Do not install the Codex skill.")
    bootstrap.add_argument("--skip-claude", action="store_true", help="Do not install the Claude Code skill.")
    bootstrap.add_argument("--force-claude", action="store_true", help="Install the Claude Code skill even if Claude Code is not detected.")
    bootstrap.add_argument("--format", default="text", choices=("text", "json"))

    install_skill = agent_subparsers.add_parser("install-codex-skill", help="Install the bundled Codex skill.")
    install_skill.add_argument("--target", help="Destination skill directory. Defaults to $CODEX_HOME or ~/.codex.")
    install_skill.add_argument("--format", default="text", choices=("text", "json"))

    install_claude = agent_subparsers.add_parser("install-claude-skill", help="Install the bundled Claude Code skill.")
    install_claude.add_argument("--target", help="Destination skill directory. Defaults to ~/.claude/skills.")
    install_claude.add_argument("--force", action="store_true", help="Install even if Claude Code is not detected.")
    install_claude.add_argument("--format", default="text", choices=("text", "json"))

    memory = agent_subparsers.add_parser("memory", help="Print the persistent memory snippet for agents.")
    memory.add_argument("--format", default="text", choices=("text", "json"))

    doctor = agent_subparsers.add_parser("doctor", help="Check whether agent skills are installed.")
    doctor.add_argument("--target", help="Codex skill directory to check. Defaults to $CODEX_HOME or ~/.codex.")
    doctor.add_argument("--claude-target", help="Claude Code skill directory to check. Defaults to ~/.claude/skills.")
    doctor.add_argument("--format", default="text", choices=("text", "json"))
    return parser


def _print_errors(errors: list[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def _emit_error(args: argparse.Namespace, code: str, errors: list[str], *, exit_code: int) -> int:
    if getattr(args, "format", None) == "json":
        print(json.dumps({"status": "error", "code": code, "errors": errors}, indent=2))
    else:
        _print_errors(errors)
    return exit_code


def _print_validation_success(args: argparse.Namespace, model) -> None:
    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "ok",
                    "valid": True,
                    "schema": {
                        "name": model.model_name,
                        "parameter_count": len(model.parameters),
                        "constraint_count": len(model.constraints),
                        "strength": model.strength,
                    },
                },
                indent=2,
            )
        )
        return

    print(
        "\n".join(
            [
                "Schema is valid.",
                f"name: {model.model_name}",
                f"parameters: {len(model.parameters)}",
                f"constraints: {len(model.constraints)}",
                f"strength: {model.strength}",
            ]
        )
    )


def _run_agent_command(args: argparse.Namespace) -> int:
    if args.agent_command == "bootstrap":
        codex_detected = codex_available()
        claude_available = claude_code_available()
        codex_skill_path = Path(args.target).expanduser() if args.target else default_codex_skill_path()
        claude_skill_path = Path(args.claude_target).expanduser() if args.claude_target else default_claude_skill_path()

        codex_setup = None
        codex_skipped_reason = None
        if args.skip_codex:
            codex_skipped_reason = "skipped by --skip-codex"
        elif codex_detected or args.force_codex:
            codex_setup = install_codex_skill(args.target)
        else:
            codex_skipped_reason = "Codex was not detected"

        claude_setup = None
        claude_skipped_reason = None
        if args.skip_claude:
            claude_skipped_reason = "skipped by --skip-claude"
        elif claude_available or args.force_claude:
            claude_setup = install_claude_skill(args.claude_target, force=args.force_claude)
        else:
            claude_skipped_reason = "Claude Code was not detected"

        if args.format == "json":
            payload = {
                "status": "ok",
                "codex": {
                    "available": codex_detected,
                    "installed": codex_setup is not None,
                    "skill_path": str(codex_setup.skill_path) if codex_setup else str(codex_skill_path),
                    "skipped_reason": codex_skipped_reason,
                },
                "claude": {
                    "available": claude_available,
                    "installed": claude_setup is not None,
                    "skill_path": str(claude_setup.skill_path) if claude_setup else str(claude_skill_path),
                    "skipped_reason": claude_skipped_reason,
                },
                "memory": MEMORY_SNIPPET,
                "default_prompt": DEFAULT_PROMPT,
            }
            print(json.dumps(payload, indent=2))
            return 0

        if codex_setup is not None:
            print(f"Installed `{codex_setup.skill_name}` Codex skill at {codex_setup.skill_path}")
        elif codex_skipped_reason:
            print(f"Codex skill: not installed ({codex_skipped_reason})")
        if claude_setup is not None:
            print(f"Installed `{claude_setup.skill_name}` Claude Code skill at {claude_setup.skill_path}")
        elif claude_skipped_reason:
            print(f"Claude Code skill: not installed ({claude_skipped_reason})")
        print("")
        print("Agent memory:")
        print(MEMORY_SNIPPET)
        print("")
        print("Default prompt:")
        print(DEFAULT_PROMPT)
        return 0

    if args.agent_command == "install-codex-skill":
        setup = install_codex_skill(args.target)
        if args.format == "json":
            payload = {"status": "ok", **setup.to_json()}
            print(json.dumps(payload, indent=2))
            return 0

        print(f"Installed `{setup.skill_name}` Codex skill at {setup.skill_path}")
        return 0

    if args.agent_command == "install-claude-skill":
        try:
            setup = install_claude_skill(args.target, force=args.force)
        except RuntimeError as exc:
            if args.format == "json":
                print(json.dumps({"status": "unavailable", "error": str(exc)}, indent=2))
            else:
                print(str(exc), file=sys.stderr)
            return 1

        if args.format == "json":
            payload = {"status": "ok", "available": claude_code_available(), **setup.to_json()}
            print(json.dumps(payload, indent=2))
            return 0

        print(f"Installed `{setup.skill_name}` Claude Code skill at {setup.skill_path}")
        return 0

    if args.agent_command == "memory":
        if args.format == "json":
            print(json.dumps({"memory": MEMORY_SNIPPET}, indent=2))
        else:
            print(MEMORY_SNIPPET)
        return 0

    if args.agent_command == "doctor":
        codex_path = default_codex_skill_path() if args.target is None else args.target
        claude_path = default_claude_skill_path() if args.claude_target is None else args.claude_target
        codex_detected = codex_available()
        codex_installed = codex_skill_installed(args.target)
        claude_available = claude_code_available()
        claude_installed = claude_skill_installed(args.claude_target)
        detected = codex_detected or claude_available
        ok = detected and (not codex_detected or codex_installed) and (not claude_available or claude_installed)
        payload = {
            "status": "ok" if ok else "missing",
            "codex_available": codex_detected,
            "codex_skill_installed": codex_installed,
            "codex_skill_path": str(codex_path),
            "claude_code_available": claude_available,
            "claude_skill_installed": claude_installed,
            "claude_skill_path": str(claude_path),
        }
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            print("Lattice agent setup")
            print("cli: ok")
            print(f"codex: {'available' if codex_detected else 'not detected'}")
            print(f"codex skill: {'installed' if codex_installed else 'missing'}")
            print(f"codex path: {codex_path}")
            print(f"claude code: {'available' if claude_available else 'not detected'}")
            print(f"claude skill: {'installed' if claude_installed else 'missing'}")
            print(f"claude path: {claude_path}")
        return 0 if ok else 1

    print(f"Unknown agent command `{args.agent_command}`.", file=sys.stderr)
    return 2
