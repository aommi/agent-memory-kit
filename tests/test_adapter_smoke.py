"""End-to-end smoke tests for adapter generate() + check() pairs.

These exercise the production code paths that unit tests miss — specifically,
that generate() and check() agree on signatures and produce no spurious drift
against a freshly generated tree. Caught a real bug where _build_stop_sh()
was called with the wrong arity from claude_code.check().
"""
import importlib
import shutil
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(KIT_ROOT))


ADAPTERS = [
    "claude_code",
    "codex",
    "cursor",
    "gemini_cli",
    "hermes",
    "openclaw",
    "windsurf",
    "antigravity",
]


def _minimal_config() -> dict:
    return {
        "project": {"name": "smoke", "description": "smoke test"},
        "architecture": {"file": "vision.md"},
        "memory": {
            "files": {
                "semantic": "memory/semantic.md",
                "working": "memory/working.md",
                "decisions": "DECISIONS.md",
            },
            "approval_mode": {"default": "auto", "review": []},
        },
        "conventions": ["use pytest", "never commit .env"],
    }


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / "vision.md").write_text("# vision\n")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "semantic.md").write_text("")
    (tmp_path / "memory" / "working.md").write_text("")
    (tmp_path / "DECISIONS.md").write_text("")
    # Some adapters (claude_code, antigravity) read templates from a vendored
    # .agent/memory-kit/templates/ directory inside the project.
    vendored = tmp_path / ".agent" / "memory-kit" / "templates"
    vendored.parent.mkdir(parents=True)
    shutil.copytree(KIT_ROOT / "templates", vendored)
    return tmp_path


@pytest.mark.parametrize("adapter_name", ADAPTERS)
def test_generate_then_check_is_clean(project: Path, adapter_name: str):
    """Each adapter's generate() must produce output that its own check() accepts."""
    mod = importlib.import_module(f"adapters.{adapter_name}")
    config = _minimal_config()

    # generate() must not raise
    mod.generate(project, config)

    # check() must not raise (this is what B4 broke) and must report no drift
    diffs = mod.check(project, config)
    assert diffs == [], (
        f"{adapter_name}.check() reported drift immediately after generate(): {diffs}"
    )


@pytest.mark.parametrize("adapter_name", ADAPTERS)
def test_check_without_generate_does_not_crash(project: Path, adapter_name: str):
    """check() on a project with no generated files must not raise — it should
    return drift entries indicating the missing files."""
    mod = importlib.import_module(f"adapters.{adapter_name}")
    # Should return a list (possibly with drift), never raise
    diffs = mod.check(project, _minimal_config())
    assert isinstance(diffs, list)
