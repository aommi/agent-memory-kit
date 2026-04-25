"""Shared adapter utilities."""
from pathlib import Path


def ensure_gitignored(project_root: Path, entry: str) -> None:
    """Add entry to project .gitignore if not already present."""
    gitignore_path = project_root / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if entry in content.splitlines():
            return
        sep = "\n" if content.endswith("\n") else "\n\n"
        gitignore_path.write_text(content + sep + entry + "\n")
    else:
        gitignore_path.write_text(entry + "\n")
