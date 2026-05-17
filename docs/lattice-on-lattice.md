# Lattice On Lattice

This document shows Lattice testing part of its own agent adoption surface. It is meant as a study artifact for coding agents: read it when you want to see how to turn a behavior surface into a schema, generate scenarios, and use those rows as executable tests.

## What Was Tested

The behavior surface was:

```bash
lattice agent bootstrap
```

This command detects available known agent harnesses and installs the matching Lattice skill integrations. Generic agents use `lattice agent instructions` or `lattice agent install-skill <target>`. The interesting bootstrap behavior is not one branch at a time; it is the interaction between:

- which harnesses are detected
- which harnesses are forced or skipped
- whether explicit target paths are supplied
- whether the user asks for JSON or text output

That makes it a good Lattice target.

## Source Behavior

The implementation lives in:

- [src/lattice/agent.py](../src/lattice/agent.py)
- [src/lattice/cli.py](../src/lattice/cli.py)

The command currently supports these adoption paths:

- `lattice agent bootstrap`
- `lattice agent install-codex-skill`
- `lattice agent install-claude-skill`
- `lattice agent memory`
- `lattice agent doctor`

For this exercise, the schema focused only on `bootstrap`. That kept the model coherent and avoided mixing separate command contracts into one matrix.

## Schema Extraction

The schema lives at:

- [examples/agent-bootstrap-matrix/model.yaml](../examples/agent-bootstrap-matrix/model.yaml)

The extracted parameters were:

```yaml
parameters:
  codex_detection: [available, unavailable]
  claude_detection: [available, unavailable]
  codex_directive: [default, force, skip]
  claude_directive: [default, force, skip]
  target_mode: [explicit, default]
  output_format: [json, text]
```

These are behavior partitions, not implementation details. For example, the schema does not model every possible `PATH` value. It models the observable state: Codex detected or unavailable, Claude Code detected or unavailable.

## Forced Rows

The schema includes three `forced` constraints. These are not preferences; they are specific scenarios that must appear at least once because they carry product meaning.

1. Claude-only default bootstrap:
   Codex unavailable, Claude available, both directives default, explicit targets, JSON output. This protects the rule that bootstrap is harness-detection driven and should not install Codex just because a Codex target was supplied.

2. No harnesses detected:
   Codex unavailable, Claude unavailable, both directives default, default target mode, JSON output. This protects the empty-environment case.

3. Both harnesses skipped:
   Codex available, Claude available, both directives skip, explicit targets, text output. This protects explicit user intent overriding detection.

## Generation

The model was validated first:

```bash
PYTHONPATH=src python3 -m lattice validate examples/agent-bootstrap-matrix/model.yaml
```

Then Lattice generated the scenarios:

```bash
PYTHONPATH=src python3 -m lattice generate examples/agent-bootstrap-matrix/model.yaml > examples/agent-bootstrap-matrix/scenarios.json
```

The output lives at:

- [examples/agent-bootstrap-matrix/scenarios.json](../examples/agent-bootstrap-matrix/scenarios.json)

Result:

- 144 exhaustive combinations
- 10 generated scenarios
- 14.4x reduction
- 100% pairwise coverage

## Turning Rows Into Tests

The executable test lives at:

- [tests/test_agent_bootstrap_matrix.py](../tests/test_agent_bootstrap_matrix.py)

The test does not hand-pick cases. It reads the generated scenario file:

```python
scenarios = json.loads(SCENARIOS.read_text())["scenarios"]
```

For each row, it creates an isolated temporary environment:

- a fake `codex` executable when `codex_detection = available`
- a fake `claude` executable when `claude_detection = available`
- a temp `HOME`
- empty `CODEX_HOME`
- explicit target directories when `target_mode = explicit`

Then it translates directives into CLI flags:

- `force` becomes `--force-codex` or `--force-claude`
- `skip` becomes `--skip-codex` or `--skip-claude`
- `default` adds no flag

Finally, it asserts the expected behavior:

- default installs only when the harness is detected
- force installs even when not detected
- skip never installs
- JSON output reports availability, installed status, skill paths, memory, default prompt, and generic instruction commands
- text output includes install or skipped status plus memory, default prompt, and the generic fallback path

## Why This Is Useful

This is the pattern Lattice is designed for:

1. Pick one coherent behavior surface.
2. Extract meaningful behavior dimensions.
3. Add constraints or forced rows only for real system rules.
4. Validate the schema.
5. Generate deterministic rows.
6. Make the rows drive concrete tests.

The important handoff is that Lattice did not write the assertions. The harness still interpreted the generated rows into executable checks. Lattice supplied the coverage surface and prevented the agent from hand-enumerating a few comfortable examples.

## Maintenance Rule

If `lattice agent bootstrap` gains a new behavior dimension, update the schema first, regenerate `scenarios.json`, and then update the executable test to interpret the new parameter.

Do not manually edit generated scenario rows. The schema is the contract; generated rows are the source of truth.
