# Schema Guidance Matrix

Use Lattice to test Lattice's own schema-discoverability guidance.

The matrix covers the places an agent is likely to look when it misunderstands
constraints:

- `lattice generate --help`
- `lattice validate --help`
- `lattice agent instructions`
- installed generic `lattice-workflow` skill files
- the tracked repo-local Codex `lattice-workflow` skill files
- validation errors for a misused `conditional` constraint

The goal is to keep the guidance discoverable without relying on a human to
remember the canonical README. If a future edit weakens the wording around
`invalid_pair`, `higher_order`, or "do not strip constraints", the generated
matrix test should fail.
