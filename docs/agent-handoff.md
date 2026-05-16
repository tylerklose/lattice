# Agent Handoff

Lattice is designed to be one deterministic step inside a larger coding-agent workflow, regardless of which agent or model is driving the work.

OpenClaw, Hermes, Codex, xAI-backed agents, Claude Code, and custom local harnesses all have the same contract: the agent extracts and interprets; Lattice validates and generates rows.

## Contract

Lattice sits between a coding harness and the surface being evaluated:

1. the harness inspects code, tests, a plan, a component, a template, or a config matrix
2. the harness extracts a structured schema
3. the harness sends that schema to Lattice
4. Lattice validates the schema and generates deterministic rows
5. the harness uses the rows to strengthen the plan, write tests, build fixtures, render variants, or run another evaluator

The harness should not attempt to reproduce pairwise logic itself.

The schema is first-class. The schema file is optional transport.

## Recommended Prompt Shape

When using Lattice from any agent:

- ask the agent to identify parameters, value partitions, and known invalid combinations
- require the agent to emit a structured schema
- run `lattice validate`
- only then run `lattice generate`
- use the generated rows as the source of truth for planning, tests, fixtures, rendered variants, or visual review

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

## Variant Mode

Input surface:

- view partials
- component props
- template variants
- design-system stories
- config matrices

Output shape:

- fixture matrix
- rendered variant rows
- contact-sheet inputs
- visual diff inputs
- review checklist

## Non-Goals

Lattice should not:

- call an LLM itself
- scrape repositories
- infer parameters from prose on its own
- bundle prompt logic into the CLI
