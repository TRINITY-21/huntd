"""Tests for git data extraction."""

import os
import subprocess
import tempfile

import pytest

from huntd.git import get_commits, get_file_stats, get_repo_info, scan_repo


def _create_test_repo(path: str) -> str:
    """Create a real git repo with some commits for testing."""
    subprocess.run(["git", "init", path], capture_output=True)
    subprocess.run(["git", "-C", path, "config", "user.email", "test@test.com"], capture_output=True)
    subprocess.run(["git", "-C", path, "config", "user.name", "Test User"], capture_output=True)

    # Commit 1: add a Python file
    py_file = os.path.join(path, "main.py")
    with open(py_file, "w") as f:
        f.write("print('hello world')\n")
    subprocess.run(["git", "-C", path, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "Initial commit"], capture_output=True)

    # Commit 2: add a JS file
    js_file = os.path.join(path, "app.js")
    with open(js_file, "w") as f:
        f.write("console.log('hello');\n")
    subprocess.run(["git", "-C", path, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "Add JS file"], capture_output=True)

    # Commit 3: modify Python file
    with open(py_file, "a") as f:
        f.write("print('goodbye')\n")
    subprocess.run(["git", "-C", path, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "Update Python file"], capture_output=True)

    # Add a README
    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# Test\n")
    subprocess.run(["git", "-C", path, "add", "."], capture_output=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "Add README"], capture_output=True)

    return path


def test_get_commits():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        commits = get_commits(repo)
        assert len(commits) == 4
        assert commits[0].subject == "Add README"  # most recent first
        assert commits[0].author == "Test User"
        assert commits[0].email == "test@test.com"


def test_get_commits_has_stats():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        commits = get_commits(repo)
        # At least some commits should have insertion stats
        has_insertions = any(c.insertions > 0 for c in commits)
        assert has_insertions


def test_get_commits_empty_repo():
    with tempfile.TemporaryDirectory() as tmp:
        repo = os.path.join(tmp, "empty")
        subprocess.run(["git", "init", repo], capture_output=True)
        commits = get_commits(repo)
        assert commits == []


def test_get_commits_nonexistent():
    commits = get_commits("/nonexistent/path")
    assert commits == []


def test_get_file_stats():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        changes = get_file_stats(repo)
        assert len(changes) > 0
        exts = {fc.ext for fc in changes}
        assert ".py" in exts
        assert ".js" in exts


def test_get_file_stats_has_line_counts():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        changes = get_file_stats(repo)
        total_added = sum(fc.added for fc in changes)
        assert total_added > 0


def test_get_repo_info():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        info = get_repo_info(repo)
        assert info.name == "test-repo"
        assert info.total_commits == 4
        assert info.has_readme is True
        assert info.branch_count >= 1
        assert info.last_commit is not None
        assert info.is_dirty is False


def test_get_repo_info_dirty():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        # Make it dirty
        with open(os.path.join(repo, "dirty.txt"), "w") as f:
            f.write("uncommitted\n")
        info = get_repo_info(repo)
        assert info.is_dirty is True


def test_scan_repo_full():
    with tempfile.TemporaryDirectory() as tmp:
        repo = _create_test_repo(os.path.join(tmp, "test-repo"))
        info = scan_repo(repo)
        assert info.total_commits == 4
        assert len(info.commits) == 4
        assert len(info.file_changes) > 0
