---
name: lattice-workflow
description: Use when planning or testing behavior with interacting states, roles, permissions, feature flags, modes, providers, optional fields, validation branches, lifecycle states, combinatorial edge cases, pairwise coverage, or t-way coverage. Extract a Lattice schema, run the local Lattice CLI, and use generated rows to strengthen plans or tests.
---

# Lattice Workflow

Use this skill to keep the agent on the extraction and interpretation work while Lattice handles the combinatorics.

## When To Use It

Use this skill when the task is any of:

- derive a combinatorial model from a feature or PRD
- derive a test matrix from existing code
- convert edge cases into explicit parameter/value constraints
- generate pairwise or 3-way scenarios without hand-enumerating combinations
- review a plan involving roles, permissions, modes, providers, feature flags, optional fields, validation branches, or lifecycle states
- find coverage gaps where bugs are likely to hide in interactions rather than single branches

Do not use this skill to invent pairwise combinations manually. The schema is the contract. The generated rows are the source of truth. The schema file is optional transport.

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
lattice agent bootstrap
```

If the skill was copied from a Lattice checkout, the agent setup page is available at `docs/install.md` in that checkout.

In this repository, the development fallback remains:

```bash
cat schema.json | PYTHONPATH=src python3 -m lattice validate
cat schema.json | PYTHONPATH=src python3 -m lattice generate
```

## Workflow

1. Extract the schema.
   First choose the scope. A schema should usually describe one coherent interaction surface: one feature, one workflow, one service behavior, one endpoint family, or one data-model interaction surface. Then choose parameters that represent independent decisions or state partitions inside that scope. Choose values that are meaningful partitions, not every literal in the codebase.
2. Encode constraints.
   Prefer the smallest constraint type that matches the rule. Use `conditional` instead of hand-writing `N/A` values.
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
   In plan mode, turn rows into plan revisions, missing decisions, and review scenarios. In test mode, diff the rows against the existing tests and write the missing cases.

## Modeling Rules

- Scope one schema to one interaction surface. Do not default to the whole app unless the app is genuinely small and the behavior surface is still coherent.
- Keep parameter names stable and implementation-adjacent.
- Use value partitions such as `present` and `absent`, not brittle prose.
- Avoid derived duplicate parameters. If one field is determined by another, represent that as a constraint.
- Add constraints only for true business or system rules. Do not use them to encode preferences.
- If a parameter only matters under a parent value, use `conditional`.
- If a scenario must appear at least once, use `forced`.
- If a rule only breaks under multiple antecedents, use `higher_order`.

Read [references/modeling-rules.md](references/modeling-rules.md) when you need extraction heuristics or constraint selection guidance.

## Output Discipline

- Run `validate` before `generate`.
- Prefer stdin and JSON because another agent step usually consumes the output.
- Do not add or remove rows after generation.
- If validation fails, fix the schema instead of weakening the generation step.

Read [references/worked-examples.md](references/worked-examples.md) for concrete examples in this repo.
