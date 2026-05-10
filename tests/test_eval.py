"""Tests for eval/replay.py — capture validation, intent-bucket classification,
and replay comparison."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.replay import (
    classify_tool,
    validate,
    compare,
    KNOWN_BUCKETS,
    BUCKET_MAP,
)


# ── classify_tool ─────────────────────────────────────────────────────────

def test_classify_known_hermes_tools():
    assert classify_tool("terminal", "hermes") == "shell-exec"
    assert classify_tool("read_file", "hermes") == "filesystem-read"
    assert classify_tool("write_file", "hermes") == "code-edit"
    assert classify_tool("patch", "hermes") == "code-edit"
    assert classify_tool("search_files", "hermes") == "filesystem-read"
    assert classify_tool("web_search", "hermes") == "web-fetch"
    assert classify_tool("delegate_task", "hermes") == "agent-spawn"
    assert classify_tool("browser_navigate", "hermes") == "web-fetch"
    assert classify_tool("execute_code", "hermes") == "shell-exec"


def test_classify_known_claude_code_tools():
    assert classify_tool("Bash", "claude-code") == "shell-exec"
    assert classify_tool("Write", "claude-code") == "code-edit"
    assert classify_tool("Task", "claude-code") == "agent-spawn"


def test_classify_known_codex_tools():
    assert classify_tool("execute", "codex") == "shell-exec"
    assert classify_tool("read_file", "codex") == "filesystem-read"


def test_classify_unknown_tool_fallback():
    """Unknown tools should hit the heuristic fallback."""
    assert classify_tool("run_bash_script", "unknown-harness") == "shell-exec"
    assert classify_tool("search_code", "unknown-harness") == "filesystem-read"


def test_classify_all_known_buckets():
    """Every value in BUCKET_MAP must be a known bucket."""
    for harness, mapping in BUCKET_MAP.items():
        for tool, bucket in mapping.items():
            assert bucket in KNOWN_BUCKETS, \
                f"{harness}:{tool} → {bucket} not in KNOWN_BUCKETS"


# ── validate ──────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, lines: list[dict]) -> None:
    with open(path, "w") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


def test_validate_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        f.write("")
        f.flush()
        result = validate(Path(f.name))
    assert result["total"] == 0
    assert result["valid"] == 0


def test_validate_valid_captures():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "fix the bug",
             "buckets": ["shell-exec", "code-edit"], "timestamp": "2026-05-09T12:00:00Z",
             "harness": "hermes"},
            {"memory_hash": "def456", "prompt": "review PR",
             "buckets": ["filesystem-read", "agent-spawn"], "timestamp": "2026-05-09T13:00:00Z",
             "harness": "claude-code"},
        ])
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 2
    assert result["total"] == 2
    assert result["issues"] == []


def test_validate_missing_fields():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"prompt": "no memory_hash or buckets"},
        ])
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 0
    assert result["total"] == 1
    assert len(result["issues"]) >= 1


def test_validate_null_buckets():
    """buckets: null should be caught, not crash."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc", "prompt": "test",
             "buckets": None,
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 0
    assert any("not a list" in i for i in result["issues"])


def test_validate_buckets_is_string():
    """buckets as a string should be flagged as not-a-list."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc", "prompt": "test",
             "buckets": "shell-exec",
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 0
    assert any("not a list" in i for i in result["issues"])


def test_validate_unknown_bucket():
    """Unknown buckets get a warning but the capture is still valid."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc", "prompt": "test",
             "buckets": ["shell-exec", "not-a-real-bucket"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 1  # unknown bucket is a warning, not a hard fail
    assert len(result["issues"]) == 1
    assert any("not-a-real-bucket" in str(i) for i in result["issues"])


def test_validate_invalid_json():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        f.write("{not valid json\n")
        f.flush()
        result = validate(Path(f.name))
    assert result["valid"] == 0
    assert any("invalid JSON" in i for i in result["issues"])


def test_validate_missing_file():
    result = validate(Path("/nonexistent/path.jsonl"))
    assert result["valid"] == 0
    assert "file not found" in result["issues"]


# ── compare ────────────────────────────────────────────────────────────────

def test_compare_first_bucket_stable():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "fix bug",
             "buckets": ["filesystem-read", "code-edit", "shell-exec"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = compare(
            Path(f.name), 1,
            ["filesystem-read", "code-edit"],
        )
    assert result["plan_stability"]["first_bucket_stable"] is True
    assert result["plan_stability"]["baseline_first"] == "filesystem-read"
    assert result["plan_stability"]["replayed_first"] == "filesystem-read"


def test_compare_first_bucket_diverged():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "fix bug",
             "buckets": ["filesystem-read", "code-edit"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = compare(
            Path(f.name), 1,
            ["shell-exec", "code-edit"],
        )
    assert result["plan_stability"]["first_bucket_stable"] is False


def test_compare_redundant_avoided():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "fix bug",
             "buckets": ["filesystem-read", "code-edit", "shell-exec", "web-fetch"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = compare(
            Path(f.name), 1,
            ["filesystem-read", "code-edit"],
        )
    assert result["redundant_avoided"]["steps_skipped_count"] == 2
    assert "shell-exec" in result["redundant_avoided"]["steps_skipped"]
    assert "web-fetch" in result["redundant_avoided"]["steps_skipped"]


def test_compare_repeated_buckets():
    """Repeated buckets in baseline missing from replay should be counted."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "test",
             "buckets": ["filesystem-read", "filesystem-read", "code-edit"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        result = compare(
            Path(f.name), 1,
            ["filesystem-read", "code-edit"],
        )
    assert result["redundant_avoided"]["steps_skipped_count"] == 1
    assert result["redundant_avoided"]["steps_skipped"] == ["filesystem-read"]


def test_compare_line_out_of_range():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc", "prompt": "test",
             "buckets": ["shell-exec"], "timestamp": "", "harness": "hermes"},
        ])
        f.flush()
        result = compare(Path(f.name), 99, ["shell-exec"])
    assert "error" in result
    assert "out of range" in result["error"]


# ── Knit: validate + compare ──────────────────────────────────────────────

def test_valid_capture_passes_validate_and_compare():
    """A valid capture should validate clean and produce sensible compare output."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        _write_jsonl(Path(f.name), [
            {"memory_hash": "abc123", "prompt": "add test for X",
             "buckets": ["filesystem-read", "code-edit"],
             "timestamp": "2026-05-09T12:00:00Z", "harness": "hermes"},
        ])
        f.flush()
        val = validate(Path(f.name))
        assert val["valid"] == 1
        assert val["issues"] == []

        comp = compare(Path(f.name), 1, ["filesystem-read", "shell-exec"])
        assert comp["plan_stability"]["first_bucket_stable"] is True
        assert comp["redundant_avoided"]["steps_skipped_count"] >= 0
