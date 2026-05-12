# Semantic Memory — agent-memory-kit

## Core Systems

- **Purpose:** agent-memory-kit is a vendored, markdown-first project memory kit for coding agents. It stores durable project context in repo-local markdown under git, with no daemon, database, MCP server, dashboard, or telemetry.
- **Generator:** `generate.py` reads `.agent/project.yaml` and renders agent entrypoints/configs through adapters in `adapters/`. It supports `init`, per-agent generation, `all`, `all --force`, and `all --check`.
- **Adapters:** Claude Code, Codex, Hermes, Cursor, Gemini CLI, Windsurf, OpenClaw, and Antigravity share the same memory files. Adapters expose `generate()`, `check()`, and `referenced_memory_files()`.
- **Managed sections:** Generated markdown entrypoints use `<!-- amk:start -->` / `<!-- amk:end -->` sentinels. Regeneration replaces only the managed block and preserves user content outside it.
- **Approval mode:** `memory.approval_mode` in `.agent/project.yaml` controls whether semantic/decision memory is direct-write (`auto`) or propose-first (`review`). `memory/working.md`, `dev/[task]/context.md`, and candidate files are always auto.
- **Stage/graduate memory:** `memory/candidates.md` stages recurring lessons; promotion to `memory/semantic.md` requires a `**Why accepted:**` rationale. Rejections move to `memory/candidates.rejected.md` with `**Why rejected:**`.
- **Self-check target:** The kit repo has its own `.agent/project.yaml` and generated `AGENTS.md` so CI can run `python3 generate.py all . --check` against real checked-in generated output.

## Key Patterns

- Keep the kit vendored and repo-local; do not introduce global installs or load-bearing state outside markdown.
- Prefer deterministic generated output plus `--check` drift detection over runtime services.
- Generated files must be reproducible from `generate.py`, `adapters/`, `templates/`, and `.agent/project.yaml`.
- If a generated file is manually corrected, update the source config/template/adapter so regeneration preserves the correction.

## Active Areas

- Add CI enforcement so generated-file drift blocks PR merge.
- Add a merge-closeout consistency protocol so memory, docs, generated files, hooks, and manuals are reconciled after merges.
- Later: add `generate.py doctor` as advisory automation for broader closeout checks.
