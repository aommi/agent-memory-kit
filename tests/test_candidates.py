"""Tests for stage/graduate promotion (#11) — candidates.md flow, always-auto enforcement,
and scaffolding in generated output."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.utils import (
    MEMORY_FILE_DESCRIPTORS,
    build_memory_discipline,
    mode_for,
    validate_approval_mode,
    ALWAYS_AUTO,
)
from generate import cmd_init


# ── Registry ─────────────────────────────────────────────────────────────

def test_candidates_in_registry():
    paths = {d["path"] for d in MEMORY_FILE_DESCRIPTORS}
    assert "memory/candidates.md" in paths
    assert "memory/candidates.rejected.md" in paths


def test_candidates_always_auto():
    assert "memory/candidates.md" in ALWAYS_AUTO
    assert "memory/candidates.rejected.md" in ALWAYS_AUTO


def test_candidates_descriptor_fields():
    for path in ["memory/candidates.md", "memory/candidates.rejected.md"]:
        desc = next(d for d in MEMORY_FILE_DESCRIPTORS if d["path"] == path)
        for field in ("path", "description", "review_text", "auto_text"):
            assert field in desc, f"{path} missing {field}"


# ── mode_for ──────────────────────────────────────────────────────────────

def _cfg(default="auto", review=None):
    return {"memory": {"approval_mode": {"default": default, "review": review or []}}}

def _cfg_missing():
    return {"memory": {}}


def test_mode_for_candidates_always_auto_with_config():
    """Candidates are auto even when default=review."""
    cfg = _cfg(default="review")
    assert mode_for("memory/candidates.md", cfg) == "auto"
    assert mode_for("memory/candidates.rejected.md", cfg) == "auto"


def test_mode_for_candidates_auto_with_missing_config():
    """Candidates are auto under backward compat (missing approval_mode)."""
    assert mode_for("memory/candidates.md", _cfg_missing()) == "auto"
    assert mode_for("memory/candidates.rejected.md", _cfg_missing()) == "auto"


def test_mode_for_candidates_auto_even_in_review_list():
    """Even if someone puts candidates in the review list, they stay auto."""
    cfg = _cfg(default="auto", review=["memory/candidates.md"])
    assert mode_for("memory/candidates.md", cfg) == "auto"


# ── build_memory_discipline ───────────────────────────────────────────────

def test_discipline_includes_stage_graduate_flow():
    output = build_memory_discipline(_cfg(), "vision.md")
    assert "Stage → Graduate promotion (#11)" in output
    assert "memory/candidates.md" in output
    assert "memory/candidates.rejected.md" in output
    assert "**Why accepted:**" in output
    assert "**Why rejected:**" in output
    assert "- Staged:" in output


def test_discipline_includes_grep_dedup_instruction():
    output = build_memory_discipline(_cfg(), "vision.md")
    assert "grep" in output
    assert "matching claims" in output
    assert "duplicate" in output


# ── validate_approval_mode ────────────────────────────────────────────────

def test_validate_no_false_compat_for_candidates():
    """Missing approval_mode should not warn about candidates files (they're always auto)."""
    files = {"memory/semantic.md", "DECISIONS.md", "memory/working.md",
             "memory/candidates.md", "memory/candidates.rejected.md"}
    msgs = validate_approval_mode({"memory": {}}, files)
    # No INFO messages about candidates — they're in ALWAYS_AUTO
    assert not any("candidates" in m for m in msgs)


# ── cmd_init scaffolding ──────────────────────────────────────────────────

def test_init_creates_candidates_files():
    """cmd_init() scaffolds candidates.md and candidates.rejected.md."""
    import io
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Simulate interactive init with canned inputs.
        # Order: project name, description, arch file, claude-code (y), codex (y),
        # hermes (n), openclaw (n), cursor (n), windsurf (n), gemini-cli (n),
        # antigravity (n), response (y), commit (n), merge (y)
        canned = io.StringIO(
            "test-project\n"
            "test description\n"
            "\n"     # arch file: default vision.md
            "\n"     # claude-code: Y (default)
            "\n"     # codex: Y (default)
            "\n"     # hermes: N (default)
            "\n"     # openclaw: N (default)
            "\n"     # cursor: N (default)
            "\n"     # windsurf: N (default)
            "\n"     # gemini-cli: N (default)
            "\n"     # antigravity: N (default)
            "\n"     # response: Y (default)
            "\n"     # commit: N (default)
            "\n"     # merge: Y (default)
        )

        with patch("sys.stdin", canned), patch("sys.stdout", io.StringIO()):
            cmd_init(root)

        candidates_path = root / "memory" / "candidates.md"
        rejected_path = root / "memory" / "candidates.rejected.md"

        assert candidates_path.exists(), "candidates.md not created by init"
        assert rejected_path.exists(), "candidates.rejected.md not created by init"

        content = candidates_path.read_text()
        assert "Candidate Lessons" in content
        assert "- Staged: YYYY-MM-DD" in content
        assert "- Sources:" in content

        rejected_content = rejected_path.read_text()
        assert "Rejected Candidates" in rejected_content
