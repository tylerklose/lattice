---
name: lattice-workflow
description: Use when planning or testing behavior or variant surfaces with interacting states, roles, permissions, feature flags, modes, providers, optional fields, component props, rendering branches, template variants, config matrices, lifecycle states, combinatorial edge cases, pairwise coverage, or t-way coverage. Extract a Lattice schema, run the local Lattice CLI, and use generated rows to strengthen plans, tests, fixtures, rendered variants, or review matrices.
---

# Lattice Workflow

Use this skill to keep Claude on extraction and interpretation while Lattice handles the combinatorics.

## When To Use It

- derive a combinatorial model from a feature or PRD
- derive a test matrix from existing code
- derive a variant matrix from a component, partial, template, design-system story, or config surface
- convert edge cases into explicit parameter/value constraints
- generate pairwise or 3-way scenarios without hand-enumerating combinations
- render a compact visual review matrix instead of every possible variant
- review a plan involving roles, permissions, modes, providers, feature flags, optional fields, component props, rendering branches, template variants, config matrices, or lifecycle states
- find coverage gaps where bugs hide in interactions rather than single branches

## When NOT To Use It

- **Small enumerable spaces.** Fewer than ~10 total combinations — enumerate by hand.
- **Independent dimensions.** No interactions can surface a bug; each parameter affects behavior independently.
- **Non-deterministic systems.** The same input row won't produce repeatable output (e.g., testing LLM responses).

## Minimal Example

A schema (YAML on stdin):

```yaml
model_name: checkout
parameters:
  user: [signed_in, guest]
  payment: [card, apple_pay, paypal]
  cart: [empty, single, multi]
constraints:
  - invalid_pair: {payment: apple_pay, cart: empty}
```

One generated row (JSON):

```json
{"user": "guest", "payment": "card", "cart": "multi"}
```

The schema is the contract. The generated rows are the source of truth. The schema file is optional transport.

## Preflight

```bash
command -v lattice >/dev/null 2>&1 && lattice --help >/dev/null
```

If it fails, install from PyPI:

```bash
pipx install lattice-cli
```

## Workflow

1. **Extract the schema.** Choose one coherent interaction surface — one feature, one workflow, one service behavior, one endpoint family, one component's variant space, one template family, or one config matrix. Parameters represent independent decisions or state partitions. Values are meaningful partitions, not every literal in the codebase.

2. **Encode constraints.** Use the smallest constraint type that matches the rule (see [Constraint Selection](#constraint-selection) below). Encode true impossibilities — do not strip them and mark invalid rows downstream.

3. **Validate.**

   ```bash
   cat schema.json | lattice validate
   ```

4. **Generate.** Default to pairwise unless explicitly asked for higher strength.

   ```bash
   cat schema.json | lattice generate
   ```

5. **Interpret the output.** Plan mode: rows become plan revisions, missing decisions, review scenarios. Test mode: rows become assertions (see [Test Mode Discipline](#test-mode-discipline) below). Variant mode: rows become fixtures, rendered variants, screenshots, visual-diff inputs.

## Constraint Selection

| Rule shape | Use |
|---|---|
| Two assignments cannot coexist | `invalid_pair` |
| One-to-one pairing (if A then B and if B then A) | `bidirectional` |
| A requires B, but B may appear elsewhere | `forward_dep` |
| Child parameter only applies for some parent values | `conditional` |
| This assignment set must appear in at least one row | `forced` |
| Rule only breaks under three or more antecedents | `higher_order` |

Prefer the smallest constraint type that matches. Use `conditional` instead of hand-writing `N/A` values.

## Test Mode Discipline

Source expected behavior from intent — the user's request, a spec, a PRD, a ticket, or explicit reasoning about what the system *should* do. **The code under test is evidence, not truth.** If intent is ambiguous for a row, stop and ask the user.

Do not silently encode current behavior and hedge with `bug_signal:`-style annotations. That produces characterization tests, which lock in the implementation (bugs included) instead of catching divergence from intent. The asymmetries Lattice is designed to expose disappear when the test suite mirrors the same mental model as the code.

## Common Pitfalls

❌ Strip constraints to make generation easier, then mark impossible rows invalid after the fact.
✅ Encode the constraint in the schema, regenerate. Encoding constraints changes the coverage universe to valid interactions — that's the point.

❌ Write tests that assert what the code currently does.
✅ Write tests that assert what the spec, PRD, or user requested. If intent is ambiguous, ask before writing.

❌ Separate parameters for two fields where one determines the other (e.g., `currency` and `currency_symbol`).
✅ One parameter plus a constraint expressing the dependency.

❌ Brittle, prose-y value names (`payment_with_apple_pay_using_new_token_flow`).
✅ Compact partitions: `apple_pay`, `apple_pay_new_token`.

❌ Manually add or remove rows after `lattice generate`.
✅ If the generated set is wrong, fix the schema. Hand-editing rows breaks the coverage guarantee.

## References

- [references/modeling-rules.md](references/modeling-rules.md) — extraction heuristics, parameter selection, value partitioning, constraint guidance
- [references/worked-examples.md](references/worked-examples.md) — concrete examples in this repo

## Development Fallback

In a checkout of the Lattice source where the package is not installed:

```bash
cat schema.json | PYTHONPATH=src python3 -m lattice validate
cat schema.json | PYTHONPATH=src python3 -m lattice generate
```

To install or refresh this skill from the installed package:

```bash
lattice agent install-claude-skill
```
