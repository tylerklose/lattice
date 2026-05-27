# Using In Other Projects

This file describes the portable workflow for using Lattice outside this repository.

## Install Once

Install Lattice into the Python environment used by your coding harness:

```bash
pipx install lattice-cli
```

With the optional solver backend:

```bash
pipx install "lattice-cli[solver]"
```

For one-shot use from an agent, run the package-provided command through `uvx`:

```bash
uvx --from lattice-cli lattice agent instructions
```

Plain `pip` is still fine when the target harness owns the Python environment:

```bash
python3 -m pip install lattice-cli
```

For development against a local checkout:

```bash
python3 -m pip install -e /path/to/lattice
```

With the solver extra in development:

```bash
python3 -m pip install -e "/path/to/lattice[solver]"
```

## Check Before Running

Before a harness or skill tries to use Lattice, check whether it is already available:

```bash
command -v lattice >/dev/null 2>&1 && lattice --help >/dev/null
```

If that fails, install it into the current Python environment before continuing.

## Harness Pattern

In another repository, the primary loop should be:

1. the harness inspects code, tests, a plan, a component, a template, or a config matrix
2. the harness extracts a schema
3. the harness pipes that schema to `lattice validate`
4. the harness pipes that schema to `lattice generate`
5. the harness uses the generated rows to revise a plan, write tests, render variants, build fixtures, or run visual review

Example:

```bash
cat schema.json | lattice validate
cat schema.json | lattice generate
```

Use files only when they help with debugging, auditing, or repeatability.

## Agent Skills

For the full agent setup path, including the skill and memory snippet, see [install.md](install.md).

After the CLI is installed, every harness can use:

```bash
lattice agent instructions
```

If the harness accepts a skill directory, use:

```bash
lattice agent install-skill /path/to/harness/skills/lattice-workflow
```

For Codex and Claude Code convenience installs, use:

```bash
lattice agent bootstrap
lattice agent doctor
```

This detects available known harnesses and installs matching skills. Codex is detected from the `codex` command, `$CODEX_HOME`, or `~/.codex`; Claude Code is detected from the `claude` command or `~/.claude`.

If the CLI installer is unavailable and you have the source checkout, copy the bundled Codex skill into a user's skill directory:

```bash
install_dir="${CODEX_HOME:-$HOME/.codex}/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/.codex/skills/lattice-workflow/ "$install_dir/"
```

Copy the bundled Claude Code skill into the user's Claude Code skills directory:

```bash
install_dir="$HOME/.claude/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/src/lattice/resources/claude/lattice-workflow/ "$install_dir/"
```

For any other harness with a skill folder, copy the generic skill:

```bash
install_dir="/path/to/harness/skills/lattice-workflow"
mkdir -p "$(dirname "$install_dir")"
rsync -a --delete /path/to/lattice/src/lattice/resources/generic/lattice-workflow/ "$install_dir/"
```

Keep the skill examples on the installed `lattice` command. Retain the repo-local `PYTHONPATH=src python3 -m lattice` form only as a fallback for this repository itself.

## Prompt Shape

Plan work:

```text
Use $lattice-workflow. Read this feature plan, extract a Lattice schema, validate it, generate pairwise scenarios, and revise the plan so it accounts for the generated rows.
```

Test work:

```text
Use $lattice-workflow. Inspect this code and test surface, extract a Lattice schema, validate it, generate pairwise scenarios, and turn uncovered rows into concrete tests.
```

Variant work:

```text
Use $lattice-workflow. Inspect this component or template variant surface, extract a Lattice schema, validate it, generate pairwise rows, and turn the rows into fixtures, rendered variants, or a visual review matrix.
```

## When To Persist Schemas

Persist the schema only when there is a good reason:

- auditing a complex interaction space
- reviewing a feature plan over time
- debugging a difficult constraint model
- keeping a stable example or regression fixture

Otherwise, treat the schema as harness-generated transport.
