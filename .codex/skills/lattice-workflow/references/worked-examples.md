# Worked Examples

These examples live in the repo-level `examples/` directory.

## `examples/plan-mode-saved-search`

Use when the agent starts from a feature discussion or PRD and needs a review checklist.

- Input: `feature.md`
- Schema transport: `model.yaml`
- Output: `scenarios.json`

## `examples/test-mode-checkout`

Use when the agent starts from code and an existing test surface and needs missing cases.

- Input: `code-notes.md`
- Schema transport: `model.json`
- Output: `scenarios.json`

## `examples/three-way-notifications`

Use when pairwise is not enough and the user explicitly wants 3-way coverage.

- Input: `brief.md`
- Schema transport: `model.yaml`
- Output: `scenarios.json`

## `examples/component-variant-matrix`

Use when the agent starts from a visual component, rendering surface, template, or design-system story and needs compact review variants instead of every possible combination.

- Input: `brief.md`
- Schema transport: `model.yaml`
- Output: `scenarios.json`

## `examples/lattice-self-test`

Use when you want a meta example of the harness extracting a schema for Lattice's own CLI surface and then using generated rows to drive CLI smoke tests.

- Input: `brief.md`
- Schema transport: `model.yaml`
- Output: `scenarios.json`

## `examples/agent-bootstrap-matrix`

Use when you want a meta example of Lattice testing its own agent skill bootstrap behavior across harness detection, force/skip directives, target modes, and output formats.

- Input: `brief.md`
- Schema transport: `model.yaml`
- Output: `scenarios.json`
