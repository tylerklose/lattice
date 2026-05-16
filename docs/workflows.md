# Workflows

This file makes the harness-to-Lattice boundary explicit. Lattice is one deterministic step inside a larger agent workflow.

## Core Contract

1. The harness inspects code, a PRD, or a design thread.
2. The harness extracts a structured schema for one coherent interaction surface.
3. The harness runs `lattice validate`.
4. The harness runs `lattice generate`.
5. The harness interprets the rows.

The harness does not invent the pairwise combinations itself.

Good default scope: one feature, one workflow, one service behavior, one endpoint family, or one state-machine slice.

## Command Pattern

In another repo or in a normal installed environment, use:

```bash
cat schema.json | lattice validate
cat schema.json | lattice generate
```

While developing inside this repo, the equivalent fallback is:

```bash
cat schema.json | PYTHONPATH=src python3 -m lattice validate
cat schema.json | PYTHONPATH=src python3 -m lattice generate
```

Files remain useful for examples, debugging, and audit trails, but they are not the primary abstraction.

## Plan Mode

Use when the starting point is a feature discussion, PRD, or architecture note.

Recommended prompt shape:

1. Ask the agent to identify parameters, value partitions, and known invalid combinations.
2. Require a structured schema.
3. Require `validate` before `generate`.
4. Ask for the output to be turned into a stronger implementation plan.

Example:

```text
Use $lattice-workflow. Read this feature brief, extract a Lattice schema, validate it, generate pairwise scenarios, and revise the plan so it explicitly accounts for the generated rows.
```

Reference example:

- [examples/plan-mode-saved-search/feature.md](examples/plan-mode-saved-search/feature.md)
- [examples/plan-mode-saved-search/model.yaml](examples/plan-mode-saved-search/model.yaml)
- [examples/plan-mode-saved-search/scenarios.json](examples/plan-mode-saved-search/scenarios.json)

## Test Mode

Use when the starting point is code, a PR diff, or an existing test suite.

Recommended prompt shape:

1. Ask the agent to derive parameters from real behavior branches.
2. Require a structured schema, using a temp file only if needed to call the CLI.
3. Require generated rows to be compared against existing tests.
4. Ask for missing rows to become concrete test cases.

Example:

```text
Use $lattice-workflow. Inspect the checkout code and tests, extract a Lattice schema, validate it, generate pairwise scenarios, and turn uncovered rows into concrete tests.
```

Reference example:

- [examples/test-mode-checkout/code-notes.md](examples/test-mode-checkout/code-notes.md)
- [examples/test-mode-checkout/model.json](examples/test-mode-checkout/model.json)
- [examples/test-mode-checkout/scenarios.json](examples/test-mode-checkout/scenarios.json)

## Higher Strength Mode

Use when the user explicitly asks for 3-way coverage or the risk is concentrated in three-way interactions.

Example:

```text
Use $lattice-workflow. Build a strength-3 schema from this notification rollout brief, validate it, generate 3-way scenarios, and summarize the riskiest rows.
```

Reference example:

- [examples/three-way-notifications/brief.md](examples/three-way-notifications/brief.md)
- [examples/three-way-notifications/model.yaml](examples/three-way-notifications/model.yaml)
- [examples/three-way-notifications/scenarios.json](examples/three-way-notifications/scenarios.json)

## Self-Hosting Mode

Use when Lattice should test its own CLI, configuration, or agent integration behavior.

Reference document:

- [docs/lattice-on-lattice.md](docs/lattice-on-lattice.md)
