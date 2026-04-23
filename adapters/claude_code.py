"""
Claude Code Adapter — generates CLAUDE.md + .claude/settings.json hooks

Reads project config to produce a project-specific entry-point file.

CLAUDE.md is managed via sentinel comments so user-added content outside
the managed block is never clobbered on regeneration:

    <!-- amk:start -->
    ...generated content...
    <!-- amk:end -->
"""
import difflib
import json
from pathlib import Path

SENTINEL_START = "<!-- amk:start -->"
SENTINEL_END = "<!-- amk:end -->"


def _write_managed_section(claude_md_path: Path, content: str) -> str:
    """Insert or replace the amk-managed block in CLAUDE.md.

    Returns a human-readable status line describing what changed.
    """
    block = f"{SENTINEL_START}\n{content}\n{SENTINEL_END}\n"

    if not claude_md_path.exists():
        claude_md_path.write_text(block)
        return "  - CLAUDE.md (created)"

    existing = claude_md_path.read_text()
    start_idx = existing.find(SENTINEL_START)
    end_idx = existing.find(SENTINEL_END)

    if start_idx == -1 or end_idx == -1:
        # No sentinels yet — append to whatever the user already has
        sep = "\n" if existing.endswith("\n") else "\n\n"
        claude_md_path.write_text(existing + sep + block)
        return "  - CLAUDE.md (amk section appended — existing content preserved)"

    old_block = existing[start_idx : end_idx + len(SENTINEL_END)]
    new_block = block.rstrip("\n")

    if old_block == new_block:
        return "  - CLAUDE.md (unchanged)"

    updated = existing[:start_idx] + block + existing[end_idx + len(SENTINEL_END) :].lstrip("\n")
    claude_md_path.write_text(updated)

    diff_lines = list(
        difflib.unified_diff(
            old_block.splitlines(keepends=True),
            new_block.splitlines(keepends=True),
            fromfile="CLAUDE.md (before)",
            tofile="CLAUDE.md (after)",
        )
    )
    diff_str = "".join(diff_lines)
    return f"  - CLAUDE.md (amk section updated)\n{diff_str}"


def generate(project_root: Path, config: dict) -> str:
    """Generate Claude Code configuration."""
    project = config["project"]
    mk_dir = project_root / ".agent" / "memory-kit"
    templates = mk_dir / "templates"

    # Write hooks/preprompt.txt
    hooks_dir = project_root / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    (hooks_dir / "preprompt.txt").write_text((templates / "preprompt.txt").read_text())

    # Write hooks/stop.sh and make executable
    stop_path = hooks_dir / "stop.sh"
    stop_path.write_text((templates / "stop.sh").read_text())
    stop_path.chmod(0o755)

    # Generate .claude/settings.json
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(exist_ok=True)
    settings_path = claude_dir / "settings.json"

    hooks_abs = project_root / "hooks"
    our_hooks = {
        "UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": f"cat {hooks_abs}/preprompt.txt"}]}
        ],
        "Stop": [
            {"hooks": [{"type": "command", "command": f"bash {hooks_abs}/stop.sh"}]}
        ],
    }

    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}

    existing.setdefault("hooks", {}).update(our_hooks)
    settings_path.write_text(json.dumps(existing, indent=2) + "\n")

    # Build managed CLAUDE.md content
    conventions = config.get("conventions", [])
    conventions_md = "\n".join(f"- {c}" for c in conventions) if conventions else ""

    skills = config.get("skills", {})
    skills_md = ""
    if skills.get("enabled"):
        skills_md = f"""\

---

## Skills architecture

All LLM prompt templates live in `{skills.get("directory", "skills/")}<name>/SKILL.md`. There are no prompt strings in Python source files.

Frontmatter is parsed with `pyyaml`. Template engine is plain `str.format` — no Jinja2, no exceptions.
"""

    arch_file = config.get("architecture", {}).get("file", "ARCHITECTURE_VISION.md")

    managed_content = f"""\
# {project["name"]} — Developer Guide

**{project["name"]}** is {project["description"]}

---

## Memory System (Session Startup + Hooks)

**On session start:** Read `memory/semantic.md` ONCE to load project context.

**On every turn:** The preprompt hook (`hooks/preprompt.txt`) handles reading `memory/working.md`.

**Task files:** Only load `/dev/[task]/*` files when actively working on that task.

**MCP efficiency:** Before calling any MCP tool to retrieve information, first check if that information might exist in `memory/semantic.md` or `dev/[task]/context.md` — local files are cheaper than remote MCP queries.

**Keep context minimal:** Do not speculatively load files "just in case".

**Mid-session drift:** If reasoning becomes uncertain or inconsistent with prior context, re-read `memory/semantic.md` before continuing.

---

## Architecture vision

Before implementing a feature, read `{arch_file}`. It is the canonical record of architectural principles, product direction, design-decision rationale, and known risks.{skills_md}
---

## Key conventions

{conventions_md}"""

    claude_md_status = _write_managed_section(project_root / "CLAUDE.md", managed_content)

    return (
        "Claude Code configuration generated:\n"
        f"{claude_md_status}\n"
        "  - .claude/settings.json (hooks merged)\n"
        "  - hooks/preprompt.txt\n"
        "  - hooks/stop.sh"
    )
