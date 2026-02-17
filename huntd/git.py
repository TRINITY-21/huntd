"""Git data extraction — subprocess-based for maximum speed."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


COMMIT_SEP = "---HUNTD_SEP---"


@dataclass
class Commit:
    hash: str
    author: str
    email: str
    timestamp: datetime
    subject: str
    insertions: int = 0
    deletions: int = 0
    files_changed: int = 0


@dataclass
class FileChange:
    hash: str
    timestamp: datetime
    path: str
    ext: str
    added: int
    removed: int


@dataclass
class RepoInfo:
    path: str
    name: str
    branch_count: int = 0
    last_commit: Optional[datetime] = None
    has_readme: bool = False
    total_commits: int = 0
    is_dirty: bool = False
    commits: list[Commit] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)


def _run_git(repo_path: str, args: list[str], timeout: int = 60) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def get_commits(repo_path: str) -> list[Commit]:
    """Extract all commits with stats in a single subprocess call."""
    # Marker at START of each commit so shortstat stays in the same block
    marker = COMMIT_SEP
    fmt = f"{marker}%n%H%n%an%n%ae%n%aI%n%s"
    output = _run_git(repo_path, [
        "log", "--all", f"--pretty=format:{fmt}", "--shortstat",
    ])
    if not output.strip():
        return []

    commits: list[Commit] = []
    blocks = output.split(marker)

    for block in blocks:
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        if len(lines) < 5:
            continue

        try:
            ts = datetime.fromisoformat(lines[3])
        except (ValueError, IndexError):
            continue

        commit = Commit(
            hash=lines[0],
            author=lines[1],
            email=lines[2],
            timestamp=ts,
            subject=lines[4],
        )

        # Parse --shortstat line if present
        for line in lines[5:]:
            if "changed" in line:
                ins = re.search(r"(\d+) insertion", line)
                dels = re.search(r"(\d+) deletion", line)
                files = re.search(r"(\d+) file", line)
                commit.insertions = int(ins.group(1)) if ins else 0
                commit.deletions = int(dels.group(1)) if dels else 0
                commit.files_changed = int(files.group(1)) if files else 0
                break

        commits.append(commit)

    return commits


def get_file_stats(repo_path: str) -> list[FileChange]:
    """Extract per-file line changes for language breakdown."""
    fmt = "%H %aI"
    output = _run_git(repo_path, [
        "log", "--all", f"--pretty=format:{fmt}", "--numstat",
    ])
    if not output.strip():
        return []

    changes: list[FileChange] = []
    current_hash: Optional[str] = None
    current_ts: Optional[datetime] = None

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Check if this is a commit header (40-char hash + space + ISO timestamp)
        parts = line.split(" ", 1)
        if len(parts) == 2 and len(parts[0]) == 40 and all(c in "0123456789abcdef" for c in parts[0]):
            current_hash = parts[0]
            try:
                current_ts = datetime.fromisoformat(parts[1])
            except ValueError:
                current_ts = None
            continue

        # numstat line: <added>\t<removed>\t<filepath>
        tabs = line.split("\t")
        if len(tabs) == 3 and current_hash and current_ts:
            added_str, removed_str, filepath = tabs
            # Binary files show "-" for added/removed
            if added_str == "-" or removed_str == "-":
                continue
            try:
                added = int(added_str)
                removed = int(removed_str)
            except ValueError:
                continue
            ext = Path(filepath).suffix.lower() or "(no ext)"
            changes.append(FileChange(
                hash=current_hash,
                timestamp=current_ts,
                path=filepath,
                ext=ext,
                added=added,
                removed=removed,
            ))

    return changes


def get_repo_info(repo_path: str) -> RepoInfo:
    """Get basic repo metadata (fast — small individual calls)."""
    name = Path(repo_path).name
    info = RepoInfo(path=repo_path, name=name)

    # Branch count
    branches_out = _run_git(repo_path, ["branch", "-a"])
    if branches_out.strip():
        info.branch_count = len([b for b in branches_out.strip().split("\n") if b.strip()])

    # Last commit date
    last_out = _run_git(repo_path, ["log", "-1", "--format=%aI"])
    if last_out.strip():
        try:
            info.last_commit = datetime.fromisoformat(last_out.strip())
        except ValueError:
            pass

    # README exists
    tree_out = _run_git(repo_path, ["ls-tree", "--name-only", "HEAD"])
    if tree_out:
        info.has_readme = any("readme" in f.lower() for f in tree_out.strip().split("\n"))

    # Total commit count
    count_out = _run_git(repo_path, ["rev-list", "--count", "--all"])
    if count_out.strip():
        try:
            info.total_commits = int(count_out.strip())
        except ValueError:
            pass

    # Dirty check
    status_out = _run_git(repo_path, ["status", "--porcelain"], timeout=10)
    info.is_dirty = bool(status_out.strip())

    return info


def scan_repo(repo_path: str) -> RepoInfo:
    """Full scan of a single repo — returns RepoInfo with commits and file changes."""
    info = get_repo_info(repo_path)
    info.commits = get_commits(repo_path)
    info.file_changes = get_file_stats(repo_path)
    return info
