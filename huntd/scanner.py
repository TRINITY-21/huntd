"""Repo discovery — recursively find all git repositories under a directory."""

from __future__ import annotations

import os
from pathlib import Path

SKIP_DIRS = frozenset({
    "node_modules", ".venv", "venv", "__pycache__", "target", "build",
    "dist", ".gradle", ".dart_tool", "vendor", ".next", ".nuxt",
    "bin", "obj", ".tox", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "site-packages", ".cargo", ".rustup", "Pods",
})


def find_repos(root: str, max_depth: int = 6) -> list[str]:
    """Recursively find all git repository paths under root.

    Returns a sorted list of absolute paths to directories containing .git.
    """
    root = os.path.expanduser(root)
    root = os.path.abspath(root)
    repos: list[str] = []

    def _walk(path: str, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = list(os.scandir(path))
        except (PermissionError, OSError):
            return

        has_git = False
        subdirs: list[os.DirEntry] = []

        for entry in entries:
            try:
                if entry.name == ".git" and entry.is_dir(follow_symlinks=False):
                    has_git = True
                elif entry.is_dir(follow_symlinks=False):
                    subdirs.append(entry)
            except (PermissionError, OSError):
                continue

        if has_git:
            repos.append(path)
            # Don't recurse into a found repo — avoids submodule noise
            return

        for d in subdirs:
            if d.name.startswith("."):
                continue
            if d.name in SKIP_DIRS:
                continue
            _walk(d.path, depth + 1)

    _walk(root, 0)
    repos.sort()
    return repos
