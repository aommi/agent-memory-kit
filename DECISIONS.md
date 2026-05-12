# Decisions — agent-memory-kit

## 2026-05-12 — CI Gate For Generated-File Drift

**Decision:** Add CI that runs the test suite and `python3 generate.py all . --check` against the kit repo's own generated `AGENTS.md`.

**Reasoning:** The applycling audit found a real failure mode: generated entrypoints can be manually corrected while the generator source remains stale. A prose closeout rule helps, but CI is the enforcement mechanism that prevents stale generated output from merging unnoticed.

**Trade-offs:** The kit repo now carries a minimal `.agent/project.yaml`, `AGENTS.md`, and tracked memory files for itself. That is a small amount of self-dogfood state, but it gives CI a real generated artifact to compare against without introducing any daemon, database, or non-markdown state.

**When to revisit:** If the generated surface grows too large for the kit repo itself, move the self-check target to a tracked fixture project and run `generate.py all <fixture> --check` instead.

**Affects:** `.github/workflows/ci.yml`, `.agent/project.yaml`, `AGENTS.md`, `memory/semantic.md`, `DECISIONS.md`
