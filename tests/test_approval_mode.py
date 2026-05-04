"""Tests for configurable approval mode (build_memory_discipline, mode_for,
validate_approval_mode, and render-uniqueness across adapters)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.utils import (
    build_memory_discipline,
    build_approval_gate,
    mode_for,
    validate_approval_mode,
    MEMORY_FILE_DESCRIPTORS,
    EXCLUDED_FROM_APPROVAL_MODE,
    COMPAT_REVIEW_DEFAULTS,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _cfg(default="auto", review=None):
    """Minimal config for approval_mode tests."""
    return {
        "memory": {
            "approval_mode": {
                "default": default,
                "review": review or [],
            }
        }
    }

def _cfg_missing():
    """Config with no approval_mode key (backward-compat)."""
    return {"memory": {}}


# ── mode_for ────────────────────────────────────────────────────────────────

def test_mode_for_all_auto():
    cfg = _cfg(default="auto", review=[])
    assert mode_for("memory/semantic.md", cfg) == "auto"
    assert mode_for("DECISIONS.md", cfg) == "auto"
    assert mode_for("memory/working.md", cfg) == "auto"

def test_mode_for_all_review():
    cfg = _cfg(default="review", review=[])
    assert mode_for("memory/semantic.md", cfg) == "review"
    assert mode_for("DECISIONS.md", cfg) == "review"

def test_mode_for_mixed():
    cfg = _cfg(default="auto", review=["DECISIONS.md"])
    assert mode_for("memory/semantic.md", cfg) == "auto"
    assert mode_for("DECISIONS.md", cfg) == "review"

def test_mode_for_missing_config_defaults_to_review():
    """Backward compat: missing approval_mode → default='review'."""
    assert mode_for("memory/semantic.md", {}) == "review"
    assert mode_for("DECISIONS.md", {}) == "review"


# ── build_memory_discipline ─────────────────────────────────────────────────

def test_build_all_auto():
    output = build_memory_discipline(_cfg(default="auto"), "vision.md")
    assert "update directly after changes" in output
    assert "summarize what you changed" in output
    assert "propose updates; wait for approval" not in output
    assert output.startswith("### Memory Discipline")

def test_build_semantic_review():
    cfg = _cfg(default="auto", review=["memory/semantic.md"])
    output = build_memory_discipline(cfg, "vision.md")
    assert "propose updates; wait for approval before writing" in output
    assert "update directly after changes; summarize new entries" in output  # DECISIONS still auto

def test_build_both_review():
    cfg = _cfg(default="auto", review=["memory/semantic.md", "DECISIONS.md"])
    output = build_memory_discipline(cfg, "vision.md")
    assert "propose updates; wait for approval before writing" in output
    assert "propose entries for approval" in output

def test_build_all_review_via_default():
    output = build_memory_discipline(_cfg(default="review"), "vision.md")
    assert "propose updates; wait for approval" in output
    assert "propose entries for approval" in output

def test_build_missing_config():
    """Backward compat: missing approval_mode → review for semantic/DECISIONS."""
    output = build_memory_discipline(_cfg_missing(), "vision.md")
    assert "propose updates; wait for approval before writing" in output
    assert "propose entries for approval" in output
    assert "update freely after each response" in output  # working always auto

def test_build_includes_arch_file():
    output = build_memory_discipline(_cfg(), "my_vision.md")
    assert "`my_vision.md`" in output
    assert "update only on merge" in output

def test_build_includes_decisions_vs_assumptions():
    output = build_memory_discipline(_cfg(), "vision.md")
    assert "DECISIONS.md vs. Assumptions distinction" in output
    assert "On PR merge:" in output
    # Each appears exactly once
    assert output.count("DECISIONS.md vs. Assumptions distinction") == 1
    assert output.count("On PR merge:") == 1


# ── build_approval_gate ─────────────────────────────────────────────────────

def test_approval_gate_both_review():
    cfg = _cfg(default="auto", review=["memory/semantic.md", "DECISIONS.md"])
    output = build_approval_gate(cfg)
    assert "requires explicit user approval" in output
    assert "memory/semantic.md" in output
    assert "DECISIONS.md" in output

def test_approval_gate_all_auto():
    cfg = _cfg(default="auto")
    output = build_approval_gate(cfg)
    assert "may be updated directly" in output
    assert "requires explicit user approval" not in output


# ── validate_approval_mode ──────────────────────────────────────────────────

def test_validate_all_covered():
    files = {"memory/semantic.md", "DECISIONS.md", "memory/working.md"}
    msgs = validate_approval_mode(_cfg(), files)
    assert msgs == []

def test_validate_stale_review_entry():
    """File in review list but no adapter references it → DRIFT."""
    cfg = _cfg(default="auto", review=["DECISIONS.md"])
    files = {"memory/semantic.md", "memory/working.md"}  # DECISIONS not referenced
    msgs = validate_approval_mode(cfg, files)
    assert any("DECISIONS.md" in m and "stale" not in m for m in msgs) or \
           any("no adapter references it" in m for m in msgs)

def test_validate_unknown_referenced_file():
    """Adapter declares a file not in MEMORY_FILE_DESCRIPTORS → DRIFT."""
    cfg = _cfg()
    files = {"memory/unknown.md"}
    msgs = validate_approval_mode(cfg, files)
    assert any("DRIFT registry" in m for m in msgs)

def test_validate_compat_info_when_approval_missing():
    """Missing approval_mode + new file → INFO to surface it."""
    files = {"memory/semantic.md", "DECISIONS.md", "memory/foobar.md"}
    msgs = validate_approval_mode({"memory": {}}, files)
    info_msgs = [m for m in msgs if m.startswith("INFO")]
    assert len(info_msgs) >= 1
    assert "approval_mode unset" in info_msgs[0]
    assert "memory/foobar.md" in info_msgs[0]

def test_validate_compat_silent_for_known_files():
    """Missing approval_mode with only known compat files → no message."""
    files = {"memory/semantic.md", "DECISIONS.md", "memory/working.md"}
    msgs = validate_approval_mode({"memory": {}}, files)
    assert msgs == []

def test_validate_vision_excluded():
    """vision.md in referenced set is ignored."""
    cfg = _cfg()
    files = {"memory/semantic.md", "vision.md"}
    msgs = validate_approval_mode(cfg, files)
    assert msgs == []  # vision.md excluded, semantic covered


# ── Render-uniqueness: no duplicated paragraphs in adapter output ────────────

def _render_adapter(adapter_name, config=None):
    """Render the managed content for an adapter and return it as a string."""
    import importlib
    mod = importlib.import_module(f"adapters.{adapter_name}")
    cfg = config or {
        "project": {"name": "test", "description": "test project"},
        "architecture": {"file": "vision.md"},
        "conventions": ["test convention"],
        "memory": {"approval_mode": {"default": "auto", "review": []}},
        "skills": {"enabled": False},
    }
    return mod._build_managed_content(cfg)

def test_no_duplicate_decisions_paragraph():
    """Each adapter's output must contain 'DECISIONS.md vs. Assumptions' at most once."""
    for name in ["hermes", "codex", "gemini_cli", "cursor", "openclaw", "windsurf"]:
        output = _render_adapter(name)
        count = output.count("DECISIONS.md vs. Assumptions distinction")
        assert count <= 1, f"{name} has {count} copies of DECISIONS distinction paragraph"

def test_no_duplicate_pr_merge_paragraph():
    """Each adapter's output must contain 'On PR merge:' at most once."""
    for name in ["hermes", "codex", "gemini_cli", "cursor", "openclaw", "windsurf"]:
        output = _render_adapter(name)
        count = output.count("On PR merge:")
        assert count <= 1, f"{name} has {count} copies of On PR merge paragraph"

def test_memory_discipline_heading_once():
    """Each adapter's output must contain '### Memory Discipline' exactly once."""
    for name in ["hermes", "codex", "gemini_cli", "cursor", "openclaw", "windsurf"]:
        output = _render_adapter(name)
        count = output.count("### Memory Discipline")
        assert count == 1, f"{name} has {count} Memory Discipline headings"


# ── All descriptors have required fields ────────────────────────────────────

def test_all_descriptors_have_required_keys():
    required = {"path", "description", "review_text", "auto_text"}
    for d in MEMORY_FILE_DESCRIPTORS:
        missing = required - set(d.keys())
        assert not missing, f"Descriptor for {d.get('path', '?')} missing keys: {missing}"
