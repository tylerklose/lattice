# Using In Other Projects

This file describes the portable workflow for using Lattice outside this repository.

## Install Once

Install Lattice into the Python environment used by your coding harness:

```bash
python3 -m pip install -e /path/to/lattice
```

With the optional solver backend:

```bash
python3 -m pip install -e "/path/to/lattice[solver]"
```

Once `lattice-cover` is published to the package index your agents use, install with:

```bash
python3 -m pip install lattice-cover
```

## Check Before Running

Before a harness or skill tries to use Lattice, check whether it is already available:

```bash
command -v lattice >/dev/null 2>&1 && lattice --help >/dev/null
```

If that fails, install it into the current Python environment before continuing.

## Harness Pattern

In another repository, the primary loop should be:

1. the harness inspects code, tests, or a plan
2. the harness extracts a schema
3. the harness pipes that schema to `lattice validate`
4. the harness pipes that schema to `lattice generate`
5. the harness uses the generated rows to revise a plan or write tests

Example:

```bash
cat schema.json | lattice validate
cat schema.json | lattice generate
```

Use files only when they help with debugging, auditing, or repeatability.

## Agent Skills

For the full agent setup path, including the skill and memory snippet, see [install.md](install.md).

After the CLI is installed, use:

```bash
lattice agent bootstrap
lattice agent doctor
```

This detects available harnesses and installs matching skills. Codex is detected from the `codex` command, `$CODEX_HOME`, or `~/.codex`; Claude Code is detected from the `claude` command or `~/.claude`.

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

## When To Persist Schemas

Persist the schema only when there is a good reason:

- auditing a complex interaction space
- reviewing a feature plan over time
- debugging a difficult constraint model
- keeping a stable example or regression fixture

Otherwise, treat the schema as harness-generated transport.
