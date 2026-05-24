---
name: lattice-workflow
description: Use when planning or testing behavior or variant surfaces with interacting states, roles, permissions, feature flags, modes, providers, optional fields, component props, rendering branches, template variants, config matrices, lifecycle states, combinatorial edge cases, pairwise coverage, or t-way coverage. Extract a Lattice schema, run the local Lattice CLI, and use generated rows to strengthen plans, tests, fixtures, rendered variants, or review matrices.
---

# Lattice Workflow

Use this skill to keep Claude on extraction and interpretation while Lattice handles combinatorial coverage.

## When To Use It

Use this skill when the task is any of:

- derive a combinatorial model from a feature or PRD
- derive a test matrix from existing code
- derive a variant matrix from a component, partial, template, design-system story, or config surface
- convert edge cases into explicit parameter/value constraints
- generate pairwise or 3-way scenarios without hand-enumerating combinations
- render a compact visual review matrix instead of every possible variant
- review a plan involving roles, permissions, modes, providers, feature flags, optional fields, component props, rendering branches, template variants, config matrices, or lifecycle states
- find coverage gaps where bugs are likely to hide in interactions rather than single branches

Do not invent pairwise combinations manually. The schema is the contract. The generated rows are the source of truth. The schema file is optional transport.

## Preflight

Before using this skill, check whether `lattice` is already installed:

```bash
command -v lattice >/dev/null 2>&1 && lattice --help >/dev/null
```

If that succeeds, use the installed command.

If it fails and you know the path to the Lattice source checkout, install it into the current Python environment:

```bash
python3 -m pip install -e /path/to/lattice
```

To install or refresh this skill from the installed package:

```bash
lattice agent install-claude-skill
```

## Workflow

1. Extract the schema.
   First choose the scope. A schema should usually describe one coherent interaction surface: one feature, one workflow, one service behavior, one endpoint family, one rendering surface, one component's variant space, one template family, one config matrix, or one data-model interaction surface. Then choose parameters that represent independent decisions or state partitions inside that scope. Choose values that are meaningful partitions, not every literal in the codebase.
2. Encode constraints.
   Prefer the smallest constraint type that matches the rule. Lattice supports exclusion-style constraints, not only conditional parameters: use `invalid_pair` when two assignments cannot coexist and `higher_order` when a combination only becomes invalid with multiple antecedents. Use `conditional` instead of hand-writing `N/A` values.
3. Validate before generation.
   Prefer the installed `lattice` command with JSON or YAML on stdin:

   ```bash
   cat schema.json | lattice validate
   ```

   If you are working inside this repository and the package is not installed yet, the fallback is:

   ```bash
   cat schema.json | PYTHONPATH=src python3 -m lattice validate
   ```

   Use a temp file only if the harness needs one for debugging or tool interop.
4. Generate deterministic scenarios.

   ```bash
   cat schema.json | lattice generate
   ```

   The development fallback in this repo is:

   ```bash
   cat schema.json | PYTHONPATH=src python3 -m lattice generate
   ```

   Default to pairwise unless the user explicitly asks for a higher strength.
5. Interpret the output.
   In plan mode, turn rows into plan revisions, missing decisions, and review scenarios. In test mode, diff the rows against the existing tests and write the missing cases. In variant mode, turn rows into fixtures, rendered variants, screenshots, contact sheets, visual diff inputs, or review checklists.

   In test mode, source expected behavior from intent — the user's request, a spec, a PRD, a ticket, or explicit reasoning about what the system *should* do. The code under test is evidence, not truth. If intent is ambiguous for a row, stop and ask the user. Do not silently encode current behavior and hedge with `bug_signal:`-style annotations: that produces characterization tests, which lock in the implementation (bugs included) instead of catching divergence from intent. The asymmetries Lattice is designed to expose disappear when the test suite mirrors the same mental model as the code.

## Modeling Rules

- Scope one schema to one interaction surface. Do not default to the whole app unless the app is genuinely small and the behavior or rendering surface is still coherent.
- Keep parameter names stable and implementation-adjacent.
- Use value partitions such as `present` and `absent`, not brittle prose.
- Avoid derived duplicate parameters. If one field is determined by another, represent that as a constraint.
- Add constraints only for true business or system rules. Do not use them to encode preferences.
- Do not strip true constraints to make generation easier, and do not generate nonsensical rows just to mark them invalid later. Encoding constraints changes the coverage universe to valid interactions, which is the point of using Lattice.
- If two assignments cannot coexist, use `invalid_pair`.
- If a parameter only matters under a parent value, use `conditional`.
- If a scenario must appear at least once, use `forced`.
- If a rule only breaks under multiple antecedents, use `higher_order`.

Read [references/modeling-rules.md](references/modeling-rules.md) when you need extraction heuristics or constraint selection guidance.

## Output Discipline

- Run `validate` before `generate`.
- Prefer stdin and JSON because another agent step usually consumes the output.
- Do not add or remove rows after generation.
- If validation fails, fix the schema instead of weakening the generation step.
- If generation emits rows that are impossible in the target system, stop and add the missing constraint rather than filtering or annotating those rows downstream.
- In test mode, assertions must reflect intended behavior, not observed behavior. Read intent from the spec, PRD, ticket, or user — never from the code under test. If intent is ambiguous, stop and ask.

Read [references/worked-examples.md](references/worked-examples.md) for concrete examples in this repo.
