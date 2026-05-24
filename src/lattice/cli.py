from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from lattice.agent import (
    AgentSetup,
    DEFAULT_PROMPT,
    GENERIC_AGENT_INSTRUCTIONS,
    MEMORY_SNIPPET,
    claude_code_available,
    claude_skill_installed,
    codex_available,
    codex_skill_installed,
    default_claude_skill_path,
    default_codex_skill_path,
    install_claude_skill,
    install_codex_skill,
    install_generic_skill,
)
from lattice.constraints import ConstraintEngine, ConstraintError
from lattice.formatters import render_output
from lattice.ipog import GenerationProgress, generate_covering_array
from lattice.parser import ModelIOError, ValidationError, load_model

DEFAULT_AGENT_FORMAT = "text"


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
        progress_callback = (
            _build_progress_callback(args.progress_every)
            if getattr(args, "progress", False)
            else None
        )
        result = generate_covering_array(
            model,
            strength=model.strength,
            seed=args.seed,
            pool_size=args.pool_size,
            progress=progress_callback,
            max_rows=args.max_rows,
            stop_after_coverage=args.stop_after_coverage,
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
    generate.add_argument(
        "--max-rows",
        type=int,
        help="Generate at most the first N scenarios.",
    )
    generate.add_argument(
        "--stop-after-coverage",
        type=float,
        help="Stop after the first generated scenario reaching this cumulative coverage percent.",
    )
    generate.add_argument("--progress", action="store_true", help="Print generation progress to stderr.")
    generate.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="With --progress, print every N generated scenarios plus the final scenario.",
    )

    validate = subparsers.add_parser("validate", help="Validate a schema without generating scenarios.")
    validate.add_argument("model", nargs="?", help="Path to a JSON or YAML schema. Reads stdin when omitted.")
    validate.add_argument("--strength", type=int, help="Override the schema strength.")
    validate.add_argument("--format", default="json", choices=("json", "text"))

    agent = subparsers.add_parser("agent", help="Install and describe coding-agent integrations.")
    agent_subparsers = agent.add_subparsers(dest="agent_command", required=True)

    bootstrap = agent_subparsers.add_parser(
        "bootstrap",
        help="Install skills for detected known harnesses and print universal agent guidance.",
    )
    bootstrap.add_argument("--target", help="Codex skill directory. Defaults to $CODEX_HOME or ~/.codex.")
    bootstrap.add_argument("--claude-target", help="Claude Code skill directory. Defaults to ~/.claude/skills.")
    bootstrap.add_argument("--force-codex", action="store_true", help="Install the Codex skill even if Codex is not detected.")
    bootstrap.add_argument("--skip-codex", action="store_true", help="Do not install the Codex skill.")
    bootstrap.add_argument("--skip-claude", action="store_true", help="Do not install the Claude Code skill.")
    bootstrap.add_argument("--force-claude", action="store_true", help="Install the Claude Code skill even if Claude Code is not detected.")
    bootstrap.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    install_skill = agent_subparsers.add_parser("install-codex-skill", help="Install the bundled Codex skill.")
    install_skill.add_argument("--target", help="Destination skill directory. Defaults to $CODEX_HOME or ~/.codex.")
    install_skill.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    install_generic = agent_subparsers.add_parser(
        "install-skill",
        help="Install the bundled generic skill into any harness-specific skill directory.",
    )
    install_generic.add_argument("target", help="Destination skill directory for the target harness.")
    install_generic.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    install_claude = agent_subparsers.add_parser("install-claude-skill", help="Install the bundled Claude Code skill.")
    install_claude.add_argument("--target", help="Destination skill directory. Defaults to ~/.claude/skills.")
    install_claude.add_argument("--force", action="store_true", help="Install even if Claude Code is not detected.")
    install_claude.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    memory = agent_subparsers.add_parser("memory", help="Print the persistent memory snippet for agents.")
    memory.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    instructions = agent_subparsers.add_parser(
        "instructions",
        help="Print harness-agnostic instructions for any coding agent.",
    )
    instructions.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))

    doctor = agent_subparsers.add_parser("doctor", help="Check whether agent skills are installed.")
    doctor.add_argument("--target", help="Codex skill directory to check. Defaults to $CODEX_HOME or ~/.codex.")
    doctor.add_argument("--claude-target", help="Claude Code skill directory to check. Defaults to ~/.claude/skills.")
    doctor.add_argument("--format", default=DEFAULT_AGENT_FORMAT, choices=("text", "json"))
    return parser


def _build_progress_callback(every: int) -> Callable[[GenerationProgress], None]:
    if every < 1:
        raise ValueError("--progress-every must be at least 1")

    started = time.monotonic()

    def report(progress: GenerationProgress) -> None:
        elapsed = time.monotonic() - started
        if progress.event == "enumerating":
            eta = _format_eta(elapsed, progress.covered, progress.total)
            print(
                "lattice progress: "
                f"enumerating interactions "
                f"checked={progress.covered}/{progress.total} "
                f"progress={progress.cumulative_pct:.1f}% "
                f"elapsed={_format_seconds(elapsed)} "
                f"eta={eta}",
                file=sys.stderr,
                flush=True,
            )
            return

        if progress.event == "enumerated":
            print(
                "lattice progress: "
                f"enumerated {progress.total} valid interactions; starting generation",
                file=sys.stderr,
                flush=True,
            )
            return

        if progress.event == "scenario" and progress.scenario % every != 0 and progress.uncovered != 0:
            return

        eta = _format_eta(elapsed, progress.covered, progress.total)
        label = "stopped " if progress.event == "stopped" else ""
        print(
            "lattice progress: "
            f"{label}scenario={progress.scenario} "
            f"covered={progress.covered}/{progress.total} "
            f"coverage={progress.cumulative_pct:.1f}% "
            f"uncovered={progress.uncovered} "
            f"elapsed={_format_seconds(elapsed)} "
            f"eta={eta}",
            file=sys.stderr,
            flush=True,
        )

    return report


def _format_eta(elapsed: float, covered: int, total: int) -> str:
    if total <= 0 or covered <= 0:
        return "unknown"
    if covered >= total:
        return "0s"
    remaining = elapsed * ((total - covered) / covered)
    return _format_seconds(remaining)


def _format_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{sec:02d}s"
    if minutes:
        return f"{minutes}m{sec:02d}s"
    return f"{sec}s"


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
        codex_setup, codex_skipped_reason = _maybe_install_agent_skill(
            detected=codex_detected,
            force=args.force_codex,
            skip=args.skip_codex,
            skip_flag="--skip-codex",
            unavailable_reason="Codex was not detected",
            install=lambda: install_codex_skill(args.target),
        )
        claude_setup, claude_skipped_reason = _maybe_install_agent_skill(
            detected=claude_available,
            force=args.force_claude,
            skip=args.skip_claude,
            skip_flag="--skip-claude",
            unavailable_reason="Claude Code was not detected",
            install=lambda: install_claude_skill(args.claude_target, force=args.force_claude),
        )

        if args.format == "json":
            payload = {
                "status": "ok",
                "codex": _agent_surface_payload(
                    detected=codex_detected,
                    setup=codex_setup,
                    skill_path=codex_skill_path,
                    skipped_reason=codex_skipped_reason,
                ),
                "claude": _agent_surface_payload(
                    detected=claude_available,
                    setup=claude_setup,
                    skill_path=claude_skill_path,
                    skipped_reason=claude_skipped_reason,
                ),
                "memory": MEMORY_SNIPPET,
                "default_prompt": DEFAULT_PROMPT,
                "instructions_command": "lattice agent instructions",
                "generic_skill_command": "lattice agent install-skill <target>",
            }
            print(json.dumps(payload, indent=2))
            return 0

        _print_agent_install_status("Codex", codex_setup, codex_skipped_reason)
        _print_agent_install_status("Claude Code", claude_setup, claude_skipped_reason)
        print("")
        print("Agent memory:")
        print(MEMORY_SNIPPET)
        print("")
        print("Default prompt:")
        print(DEFAULT_PROMPT)
        print("")
        print("Any other harness:")
        print("Run `lattice agent instructions`, or `lattice agent install-skill <target>` if the harness accepts a SKILL.md directory.")
        return 0

    if args.agent_command == "install-codex-skill":
        setup = install_codex_skill(args.target)
        return _emit_agent_setup(setup, "Codex", args.format)

    if args.agent_command == "install-skill":
        setup = install_generic_skill(args.target)
        return _emit_agent_setup(setup, "generic", args.format)

    if args.agent_command == "install-claude-skill":
        try:
            setup = install_claude_skill(args.target, force=args.force)
        except RuntimeError as exc:
            if args.format == "json":
                print(json.dumps({"status": "unavailable", "error": str(exc)}, indent=2))
            else:
                print(str(exc), file=sys.stderr)
            return 1

        return _emit_agent_setup(
            setup,
            "Claude Code",
            args.format,
            extra={"available": claude_code_available()},
        )

    if args.agent_command == "memory":
        if args.format == "json":
            print(json.dumps({"memory": MEMORY_SNIPPET}, indent=2))
        else:
            print(MEMORY_SNIPPET)
        return 0

    if args.agent_command == "instructions":
        if args.format == "json":
            print(
                json.dumps(
                    {
                        "instructions": GENERIC_AGENT_INSTRUCTIONS,
                        "memory": MEMORY_SNIPPET,
                        "default_prompt": DEFAULT_PROMPT,
                    },
                    indent=2,
                )
            )
        else:
            print(GENERIC_AGENT_INSTRUCTIONS)
        return 0

    if args.agent_command == "doctor":
        codex_path = default_codex_skill_path() if args.target is None else args.target
        claude_path = default_claude_skill_path() if args.claude_target is None else args.claude_target
        codex_detected = codex_available()
        codex_installed = codex_skill_installed(args.target)
        claude_available = claude_code_available()
        claude_installed = claude_skill_installed(args.claude_target)
        known_harness_detected = codex_detected or claude_available
        known_skills_ok = (not codex_detected or codex_installed) and (not claude_available or claude_installed)
        ok = known_skills_ok
        payload = {
            "status": "ok" if ok else "missing",
            "generic_instructions_available": True,
            "known_harness_detected": known_harness_detected,
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
            print("generic instructions: available (`lattice agent instructions`)")
            print(f"codex: {'available' if codex_detected else 'not detected'}")
            print(f"codex skill: {'installed' if codex_installed else 'missing'}")
            print(f"codex path: {codex_path}")
            print(f"claude code: {'available' if claude_available else 'not detected'}")
            print(f"claude skill: {'installed' if claude_installed else 'missing'}")
            print(f"claude path: {claude_path}")
        return 0 if ok else 1

    print(f"Unknown agent command `{args.agent_command}`.", file=sys.stderr)
    return 2


def _maybe_install_agent_skill(
    *,
    detected: bool,
    force: bool,
    skip: bool,
    skip_flag: str,
    unavailable_reason: str,
    install: Callable[[], AgentSetup],
) -> tuple[AgentSetup | None, str | None]:
    if skip:
        return None, f"skipped by {skip_flag}"
    if detected or force:
        return install(), None
    return None, unavailable_reason


def _agent_surface_payload(
    *,
    detected: bool,
    setup: AgentSetup | None,
    skill_path: Path,
    skipped_reason: str | None,
) -> dict[str, Any]:
    return {
        "available": detected,
        "installed": setup is not None,
        "skill_path": str(setup.skill_path if setup else skill_path),
        "skipped_reason": skipped_reason,
    }


def _emit_agent_setup(
    setup: AgentSetup,
    label: str,
    output_format: str,
    *,
    extra: dict[str, Any] | None = None,
) -> int:
    if output_format == "json":
        print(json.dumps({"status": "ok", **(extra or {}), **setup.to_json()}, indent=2))
        return 0

    print(f"Installed `{setup.skill_name}` {label} skill at {setup.skill_path}")
    return 0


def _print_agent_install_status(
    label: str,
    setup: AgentSetup | None,
    skipped_reason: str | None,
) -> None:
    if setup is not None:
        print(f"Installed `{setup.skill_name}` {label} skill at {setup.skill_path}")
    elif skipped_reason:
        print(f"{label} skill: not installed ({skipped_reason})")
