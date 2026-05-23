# Modeling Rules

Use this file when you are extracting a schema from code or prose and need tighter guardrails than the main skill body provides.

## Parameter Selection

- Scope one schema to one coherent behavior or rendering surface.
  Good scopes: one feature, one service behavior, one workflow, one endpoint family, one state-machine slice, one component's variant space, one template family.
  Bad default scope: the whole app.
- Model the decisions that change behavior, not every field in a payload.
- Prefer parameters that are visible in tests, UI branches, rendering branches, validation logic, template variants, component props, or feature flags.
- Split large raw domains into behavioral partitions.
  Good: `pay_range = present|absent`
  Bad: every exact salary string
- Avoid separate parameters for values that are already implied by another parameter unless the implication is partial and needs a constraint.

## Value Selection

- Values should be mutually exclusive and collectively useful for testing.
- Keep domains small and meaningful. Most parameters should land in the 2-5 value range.
- Normalize booleans as `true` and `false`.
- For optional subordinate parameters, let `conditional` introduce `N/A`. Do not hand-add `N/A` unless the schema genuinely needs it as a first-class value.

## Constraint Choice

- `invalid_pair`: two assignments cannot coexist
- `bidirectional`: one-to-one pairing; if A then B and if B then A
- `forward_dep`: A requires B, but B may appear elsewhere
- `conditional`: a child parameter only applies for some parent values
- `forced`: this assignment set must appear in at least one generated row
- `higher_order`: the invalid rule only appears when two or more antecedents are true

Choose the smallest expressive type. If a rule can be represented as `invalid_pair`, do not use `higher_order`.

## Extraction Process

1. Choose the behavior or rendering surface you are modeling.
2. Start from branches, validations, and business rules inside that scope.
3. Convert prose like "only when", "must", "cannot", and "except" into candidate constraints.
4. Remove cosmetic parameters that do not affect behavior.
5. Check whether a missing value is really a separate partition or just noise.
6. Validate the schema.
7. Only after validation, generate scenarios.

## Interpretation

- Plan mode: each row becomes a review scenario or a missing decision in the plan.
- Test mode: each row becomes a candidate setup matrix. Source the expected behavior from intent — user request, spec, PRD, or ticket — not from the code under test. If you cannot determine intent for a row, stop and surface the ambiguity to the user. Do not encode the current behavior and label it `bug_signal:` to hedge: characterization tests pass for the wrong reasons and hide the asymmetries Lattice is designed to expose. Example: if a mailbox accepts a spoofed `From:` header today, the assertion is still "rejects spoofed sender" — let the test fail and fix the code, do not invert the assertion to match the bug.
- Variant mode: each row becomes a rendered variant, fixture, screenshot, visual diff input, contact-sheet item, or review checklist item.
- Generated rows are not test names by themselves. The agent still needs to map them to application-specific assertions.
