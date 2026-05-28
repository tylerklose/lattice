# Lattice TODOs

## Distribution: static binary + thin language wrappers

Ship a standalone `lattice` executable so non-Python ecosystems don't need pipx + Python in their CI to use it. Coding agents in sandboxed environments (Codex, some Cursor setups) often can't install across language ecosystems; a static binary removes that friction. Claude Code and Codex CLI both ship this way.

Plan:

- Compile via PyInstaller, Nuitka, or PyOxidizer — evaluate which produces the smallest, fastest binary with the best startup time
- Distribute via `curl -fsSL https://… | sh` and GitHub Releases (one binary per OS/arch)
- Thin npm wrapper (`@tylerklose/lattice` or similar) that downloads the binary on install — same pattern Claude Code and Codex CLI use
- Same idea for `gem install lattice-cli` if Ruby reach matters
- Keep `pipx install lattice-cli` as the Python-shop path; the binary is for everyone else

Single source of truth stays the Python algorithm. Multiple distribution paths around it. One bug fix lands everywhere.

**Not doing:** full polyglot reimplementations (Lattice-in-JS, Lattice-in-Ruby). The math is the moat; maintaining three implementations of IPOG + the constraint solver is the wrong tax for a one-person project. Agents shell out — they don't need language-native bindings.

Revisit this if positioning ever shifts from "agent calls Lattice via CLI" toward "human developer imports Lattice directly into test files." That's a different product and would justify polyglot bindings; the current product doesn't.
