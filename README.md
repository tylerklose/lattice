# Lattice

Say you're testing a checkout flow. Users are signed in or guest. They have a coupon or not. The cart is empty, single-item, or multi-item. Shipping is standard, express, or pickup. Payment is card, Apple Pay, or PayPal. The site renders in light or dark mode.

Six knobs, a few settings each — 216 combinations. Real product surfaces have dozens of knobs and hundreds of thousands of combinations. And most production bugs are *interaction* bugs: the one where dark mode plus Apple Pay plus the new coupon breaks the order page, even though each piece works fine alone.

Nobody writes tests for 216 combinations. Nobody can write tests for 200,000. So humans and coding agents alike pick a handful of cases by gut feel, and the interaction bug ships.

Lattice is the way out. You list the knobs, the settings, and any rules ("Apple Pay isn't allowed for pickup orders"). Lattice gives back a short, deterministic list of scenarios that hits every *pair* of settings at least once. The six-knob example above collapses from 216 cases to about a dozen — enough to catch the overwhelming majority of interaction bugs without writing the universe.

The math behind this is old. It's what Hexawise and similar tools have been selling for years. What's new here is the packaging: schema in on stdin, rows out on stdout, deterministic, built for a coding agent to call while planning a feature or writing tests. The agent describes the surface, Lattice does the combinatorics, the agent turns each row into a test, a rendered screenshot, a fixture, or a step of plan review.

## How it goes

1. The agent writes a small JSON or YAML schema: parameters, values, constraints.
2. Pipe it to `lattice generate`.
3. Lattice returns the covering rows. Same schema and seed always produce the same rows.
4. The agent maps each row to whatever it's evaluating — a test, a render, a fixture, a sandbox call.

The schema is the contract between agent and engine. The rows are the product. Lattice does not care whether the surface is a backend feature, an API, a state machine, a Rails partial, a design-system component, an email template, a config matrix, or a data-model slice — if it has dimensions, values, rules, and an evaluator, Lattice can cover it.

Project status: experimental `0.1`. The CLI and agent skill bootstrap path work; the schema contract may still evolve as the project finds its first users.

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
