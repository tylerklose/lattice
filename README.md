# Lattice

Lattice turns finite, constrained parameter spaces into deterministic coverage rows.

It is built to be easy for coding agents to call, but it is not limited to backend logic. Use it whenever a surface has dimensions, values, rules, and an evaluator: a feature, workflow, API, state machine, Rails partial, design-system component, email template, config matrix, or data-model slice.

Project status: experimental `0.1`. The CLI and agent skill bootstrap path work, but the schema contract may still evolve while the project finds its first users.

The big picture is simple:

1. A person or agent names the surface and extracts parameters, values, and constraints.
2. The harness sends that schema to Lattice as JSON or YAML.
3. `lattice generate` turns the schema into deterministic pairwise or t-way coverage rows.
4. The harness maps those rows to an evaluator: tests, screenshots, contact sheets, visual diffs, sandbox calls, fixtures, or plan review.

The harness handles extraction and synthesis. Lattice handles validation, constraints, and combinatorics.

A schema should usually be scoped to one coherent surface: one feature, one workflow, one service behavior, one endpoint family, one rendering surface, one component's variant space, one template family, one config matrix, or one data-model slice.

Reach for Lattice when the combinations are easy to describe but annoying or risky to enumerate by hand. The product is not the schema file. The product is the compact set of rows that tells an evaluator what to inspect.

## Install For Agents

Start with [docs/install.md](docs/install.md) when you want any coding agent or harness to adopt Lattice.

That page covers:

- installing the `lattice` CLI with `pipx`, `uvx`, or `pip`
- printing universal instructions with `lattice agent instructions`
- installing a generic `lattice-workflow` skill into any harness directory with `lattice agent install-skill <target>`
- installing Codex and Claude Code convenience skills with `lattice agent bootstrap`
- adding an agent memory for when to reach for Lattice
- running a smoke test over stdin

## Why This Shape

Lattice is split into three small modules on purpose:

- `parser.py`: the schema contract between a harness and the engine
- `constraints.py`: deterministic feasibility and constraint reasoning
- `ipog.py`: covering-array generation and coverage accounting

That keeps the math isolated from OpenClaw, Hermes, Codex, xAI-backed agents, Claude Code, or any other harness wrapper.

## CLI

```bash
# stdin-first, harness-friendly
cat schema.json | lattice validate
cat schema.json | lattice generate

# file input is optional and useful for debugging
lattice validate schema.yaml --format text
lattice generate schema.yaml --strength 3 --format table
lattice generate schema.yaml --strength 4 --progress --progress-every 25 > scenarios.json
lattice generate schema.yaml --strength 4 --stop-after-coverage 84 > prefix.json

# explicit machine-readable validation
lattice validate schema.json --format json
```

Supported output formats:

- `json`
- `table`
- `csv`
- `summary`

`generate` defaults to JSON because the primary consumer is usually a coding harness. File-based schemas are supported, but the schema file is transport, not the product surface.

For long higher-strength runs, use `--progress` to stream coverage progress to
stderr while keeping stdout clean for JSON, CSV, table, or summary output.
`--progress-every N` controls how many generated scenarios pass between
updates.

Use `--stop-after-coverage PCT` for prefix runs that stop after the first
generated scenario reaching that cumulative coverage percentage. Use
`--max-rows N` for a fixed-size prefix. If both are set, generation stops at
whichever limit is reached first. `--stop-after-coverage 100` is treated as a
full run so rounded `100.0%` coverage near the tail does not skip final rows.

## Model Features

Lattice currently supports:

- pairwise and t-way generation
- JSON and YAML schema transport
- `invalid_pair`
- `bidirectional`
- `forward_dep`
- `conditional`
- `forced`
- `higher_order`
- inline parameter `weights`
- deterministic generation via `--seed`

Model true impossibilities as constraints before generation. Do not strip
constraints and mark impossible rows downstream: that changes the coverage
surface from valid interactions to an unconstrained cross-product. Use
`invalid_pair` for two assignments that cannot coexist and `higher_order` when
the invalid rule needs multiple antecedents.

`conditional` parameters are first-class schema features. The parser expands them into concrete parameter domains and the constraint engine enforces `N/A` semantics automatically.

## Solver Notes

The current engine is deterministic and self-contained. If `ortools` is installed via the `solver` extra, Lattice can use CP-SAT feasibility checks for partial assignments; otherwise it falls back to the built-in backtracking solver.

Install in editable mode while developing:

```bash
python3 -m pip install -e /path/to/lattice
```

Install with the optional solver backend:

```bash
python3 -m pip install -e "/path/to/lattice[solver]"
```

## Using In Other Projects

The normal workflow in another repo is:

1. install Lattice once into the Python environment your harness uses
2. have the harness emit a schema on stdin
3. call `lattice validate`
4. call `lattice generate`
5. consume the JSON output inside the harness

Example:

```bash
cat schema.json | lattice validate
cat schema.json | lattice generate
```

If you want an agent such as OpenClaw, Hermes, Codex, an xAI-backed harness, Claude Code, or a custom local agent to use the same workflow in another repo, start with [docs/install.md](docs/install.md), then see [docs/using-in-other-projects.md](docs/using-in-other-projects.md).

Scope each schema to the thing being worked on: the feature, service, workflow, component, rendering surface, template family, config matrix, or behavior slice under active design or test work.

The shortest agent adoption path after install is:

```bash
lattice agent instructions
lattice agent bootstrap
lattice agent doctor
```

`instructions` works for any agent. `bootstrap` installs convenience skills only for known harnesses detected on the machine.

## Harness Contract

Lattice is intentionally narrow. A harness owns extraction and interpretation; Lattice owns schema validation and deterministic row generation.

- plan synthesis: harness extracts schema from a plan, Lattice generates scenarios, harness strengthens the plan
- test synthesis: harness extracts schema from code/tests, Lattice generates scenarios, harness writes missing tests
- variant coverage: harness extracts component, template, or design-system variants, Lattice generates rows, harness renders screenshots, a contact sheet, or visual diffs
- evaluator coverage: harness extracts a config or sandbox matrix, Lattice generates rows, harness runs each row through the relevant evaluator

See [docs/agent-handoff.md](docs/agent-handoff.md) for the repository-level handoff shape.
See [docs/workflows.md](docs/workflows.md) for concrete agent usage patterns.
See [docs/case-studies.md](docs/case-studies.md) for public audit examples and the standard for how to write them up.
See [docs/using-in-other-projects.md](docs/using-in-other-projects.md) for portable installation and adoption.
See [docs/lattice-on-lattice.md](docs/lattice-on-lattice.md) for a worked example of Lattice testing its own agent bootstrap surface.

## Skill

This repo includes a repo-local Codex skill at `.codex/skills/lattice-workflow/`, bundled Codex and Claude Code skill resources, and a generic skill resource for any harness that accepts a `SKILL.md` directory.

Use it when you want a coding harness to:

- extract a schema from code, a spec, or a variant surface
- validate the schema before generation
- run Lattice deterministically
- interpret the rows as design review scenarios, rendered variants, fixtures, or test cases

## Examples

The `examples/` directory contains eight end-to-end examples:

- `plan-mode-saved-search`: plan -> schema -> generated scenarios
- `test-mode-checkout`: code/test surface -> schema -> generated scenarios
- `three-way-notifications`: strength-3 schema -> generated scenarios
- `lattice-self-test`: Lattice generates a matrix for testing Lattice itself
- `agent-bootstrap-matrix`: Lattice generates a matrix for testing agent skill bootstrap behavior
- `schema-guidance-matrix`: Lattice generates a matrix for testing Lattice's schema discoverability guidance
- `component-variant-matrix`: component/rendering surface -> schema -> generated visual review variants
- `httpx-query-param-merge`: OSS audit example for a real HTTPX query-parameter interaction issue
