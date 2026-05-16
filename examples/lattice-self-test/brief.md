# Lattice Self-Test

Use Lattice to generate a compact matrix for exercising Lattice's own CLI surface.

The dimensions we care about are:

- command: `validate` or `generate`
- input source: stdin or file
- schema encoding: JSON or YAML
- schema profile: simple, constrained, or invalid
- output format: JSON, text, or table

The goal is not exhaustive CLI testing by hand. The goal is a deterministic scenario matrix that a coding harness can turn into smoke tests for Lattice itself.
