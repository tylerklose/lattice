# Agent Bootstrap Matrix

Use Lattice to test Lattice's own agent adoption command.

The behavior surface is `lattice agent bootstrap`, which detects available harnesses and installs only the matching skills unless an explicit force or skip directive is provided.

Behavior dimensions:

- Codex detection: available or unavailable
- Claude Code detection: available or unavailable
- Codex directive: default, force, or skip
- Claude directive: default, force, or skip
- target mode: explicit target paths or default home-based target paths
- output format: JSON or text

Expected behavior:

- default installs only when the harness is detected
- force installs even when the harness is not detected
- skip never installs
- JSON output should describe availability, installation status, skill paths, memory, and default prompt
- text output should still include installation/skipped status plus the memory and default prompt
