# Install Lattice For Agents

This page is the agent-friendly setup path. After it is complete, any coding agent should know two things:

1. how to run the `lattice` CLI
2. when to reach for Lattice instead of hand-enumerating combinations

## 1. Install The CLI

From a local checkout or release archive:

```bash
python3 -m pip install -e /path/to/lattice
lattice --help
```

With the optional solver backend:

```bash
python3 -m pip install -e "/path/to/lattice[solver]"
lattice --help
```

Once `lattice-cli` is published to the package index your agents use, the install command should become:

```bash
pipx install lattice-cli
lattice --help
```

For a one-shot agent setup without a persistent install, use `uvx`:

```bash
uvx --from lattice-cli lattice agent instructions
```

If neither `pipx` nor `uvx` is available, plain `pip` still works:

```bash
python3 -m pip install lattice-cli
lattice --help
```

## 2. Universal Agent Setup

Every harness can use Lattice if it can run shell commands and keep a short instruction. This applies to OpenClaw, Hermes, Codex, xAI-backed agents, Claude Code, or a custom local harness.

Print the portable instruction block with:

```bash
lattice agent instructions
```

If the harness accepts skill folders, install a generic `SKILL.md` directory wherever that harness expects skills:

```bash
lattice agent install-skill /path/to/harness/skills/lattice-workflow
```

If the harness has persistent memory, also save:

```bash
lattice agent memory
```

## 3. Install Known Convenience Skills

The package also includes ready-to-use convenience skills for Codex and Claude Code. Detect available known harnesses, install the matching skills, and print the same portable guidance with:

```bash
lattice agent bootstrap
```

`bootstrap` installs only for detected known harnesses by default:

- Codex is detected from the `codex` command, `$CODEX_HOME`, or an existing `~/.codex` directory.
- Claude Code is detected from the `claude` command or an existing `~/.claude` directory.

Check the install with:

```bash
lattice agent doctor
```

If you only want to install one surface:

```bash
lattice agent install-codex-skill
lattice agent install-claude-skill
```

If you want to override detection during bootstrap:

```bash
lattice agent bootstrap --force-codex
lattice agent bootstrap --force-claude
lattice agent bootstrap --skip-codex
lattice agent bootstrap --skip-claude
```

If you only want the memory snippet:

```bash
lattice agent memory
```

The source checkout also includes the same skills at:

```text
.codex/skills/lattice-workflow/
src/lattice/resources/claude/lattice-workflow/
src/lattice/resources/generic/lattice-workflow/
```

If the CLI installer is not available, copy the Codex skill into the user's Codex skills directory manually:

```bash
install_dir="${CODEX_HOME:-$HOME/.codex}/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/.codex/skills/lattice-workflow/ "$install_dir/"
```

For Claude Code, copy the Claude skill into the user's Claude Code skills directory:

```bash
install_dir="$HOME/.claude/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/src/lattice/resources/claude/lattice-workflow/ "$install_dir/"
```

For any other harness that accepts a skill folder, copy the generic skill:

```bash
install_dir="/path/to/harness/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/src/lattice/resources/generic/lattice-workflow/ "$install_dir/"
```

Then ask the agent to use it:

```text
Use $lattice-workflow. Inspect this feature, test surface, component variant space, template, or config matrix; extract a Lattice schema; validate it; generate pairwise rows; and use the rows to strengthen the plan, tests, fixtures, or visual review.
```

## 4. If The Skill Cannot Be Downloaded

If an agent cannot copy the bundled skill, ask it to create a skill named `lattice-workflow` with this minimum `SKILL.md`:

````markdown
---
name: lattice-workflow
description: Use when planning, testing, or reviewing behavior or variant surfaces with interacting states, roles, permissions, feature flags, modes, providers, optional fields, component props, rendering branches, template variants, config matrices, lifecycle states, or edge-case matrices. Extract a Lattice schema, run the local Lattice CLI for pairwise or t-way coverage, and use generated rows to strengthen plans, tests, fixtures, rendered variants, or review matrices.
---

# Lattice Workflow

Use Lattice when a feature, PRD, code path, test surface, component, template, or config matrix has interacting dimensions.

Workflow:

1. Choose one coherent behavior or rendering surface.
2. Extract parameters, values, and true constraints.
3. Encode impossible combinations as constraints, not downstream annotations. Use `invalid_pair` when two assignments cannot coexist, `higher_order` when a rule needs multiple antecedents, and `conditional` only for parent-gated parameters.
4. Run `lattice validate` on the schema.
5. Run `lattice generate` only after validation succeeds.
6. Use the generated rows as the source of truth for plan review, rendered variants, fixtures, or missing tests.

Prefer JSON or YAML on stdin:

```bash
cat schema.json | lattice validate
cat schema.json | lattice generate
```

Do not manually add, remove, or reshuffle generated rows. Do not strip true constraints and mark impossible rows invalid after generation; fix the schema so Lattice covers the valid interaction space.
````

## 5. Add Agent Memory

If the environment supports persistent memories, add this memory:

```text
Reach for Lattice when planning, testing, or reviewing a finite constrained surface with interacting states such as roles, permissions, feature flags, modes, providers, optional fields, component props, rendering branches, template variants, config matrices, lifecycle states, or cross-product edge cases. Extract a schema with parameters, values, and true constraints; run `lattice validate`; then run `lattice generate`; use the generated rows as the source of truth for plan review, rendered variants, fixtures, or missing tests instead of hand-enumerating pairwise combinations.
```

## 6. One-Shot Setup Prompt

Use this prompt with a coding agent in a target repo:

```text
Set up Lattice for this repo.

1. Check whether `lattice --help` works.
2. If it does not, install the CLI from the local Lattice checkout or from the configured package index.
3. Run `lattice agent instructions` and save the output in this harness's instruction mechanism.
4. If this harness has a skill directory, run `lattice agent install-skill <target-skill-dir>`.
5. Run `lattice agent bootstrap` only if Codex or Claude Code convenience skills are useful on this machine.
6. Verify by validating and generating scenarios from a small schema over stdin.
```

## 7. Smoke Test

After install, this should produce JSON output with at least one scenario:

```bash
cat <<'JSON' | lattice validate
{
  "model_name": "install_smoke",
  "parameters": {
    "role": ["admin", "member"],
    "flag": ["on", "off"],
    "input": ["valid", "invalid"]
  }
}
JSON

cat <<'JSON' | lattice generate
{
  "model_name": "install_smoke",
  "parameters": {
    "role": ["admin", "member"],
    "flag": ["on", "off"],
    "input": ["valid", "invalid"]
  }
}
JSON
```
