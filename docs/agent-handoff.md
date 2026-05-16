# Agent Handoff

Lattice is designed to be one deterministic step inside a larger coding-agent workflow.

## Contract

Lattice sits between a coding harness and the codebase:

1. the harness inspects code, tests, or a plan
2. the harness extracts a structured schema
3. the harness sends that schema to Lattice
4. Lattice validates the schema and generates deterministic scenarios
5. the harness uses the rows to strengthen the plan or write tests

The harness should not attempt to reproduce pairwise logic itself.

The schema is first-class. The schema file is optional transport.

## Recommended Prompt Shape

When using Lattice from Codex, Claude Code, or a similar agent:

- ask the agent to identify parameters, value partitions, and known invalid combinations
- require the agent to emit a structured schema
- run `lattice validate`
- only then run `lattice generate`
- use the generated rows as the source of truth for planning or tests

## Plan Mode

Input surface:

- PRDs
- feature specs
- architecture notes

Output shape:

- scenario checklist
- missing design combinations
- forced edge-case review
- strengthened implementation plan

## Test Mode

Input surface:

- existing application code
- test suite
- PR diff

Output shape:

- uncovered scenario list
- candidate test names
- concrete test setup matrices
- generated final test cases where appropriate

## Non-Goals

Lattice should not:

- call an LLM itself
- scrape repositories
- infer parameters from prose on its own
- bundle prompt logic into the CLI
