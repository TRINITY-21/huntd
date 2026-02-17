"""Tests for repo discovery scanner."""

import os
import tempfile

from huntd.scanner import find_repos


def test_find_repos_single():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "project-a", ".git"))
        repos = find_repos(tmp)
        assert len(repos) == 1
        assert repos[0] == os.path.join(tmp, "project-a")


def test_find_repos_multiple():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "alpha", ".git"))
        os.makedirs(os.path.join(tmp, "beta", ".git"))
        os.makedirs(os.path.join(tmp, "gamma", ".git"))
        repos = find_repos(tmp)
        assert len(repos) == 3


def test_find_repos_nested_not_counted():
    """Repos inside other repos should be skipped (not recursed into)."""
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "parent", ".git"))
        os.makedirs(os.path.join(tmp, "parent", "child", ".git"))
        repos = find_repos(tmp)
        assert len(repos) == 1
        assert "parent" in repos[0]


def test_find_repos_skips_hidden():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, ".hidden-project", ".git"))
        os.makedirs(os.path.join(tmp, "visible", ".git"))
        repos = find_repos(tmp)
        assert len(repos) == 1
        assert "visible" in repos[0]


def test_find_repos_skips_node_modules():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "node_modules", "dep", ".git"))
        os.makedirs(os.path.join(tmp, "real-project", ".git"))
        repos = find_repos(tmp)
        assert len(repos) == 1
        assert "real-project" in repos[0]


def test_find_repos_empty():
    with tempfile.TemporaryDirectory() as tmp:
        repos = find_repos(tmp)
        assert repos == []


def test_find_repos_max_depth():
    with tempfile.TemporaryDirectory() as tmp:
        deep = os.path.join(tmp, "a", "b", "c", "d", "e", "f", "g", ".git")
        os.makedirs(deep)
        repos = find_repos(tmp, max_depth=3)
        assert len(repos) == 0
        repos = find_repos(tmp, max_depth=10)
        assert len(repos) == 1


def test_find_repos_sorted():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "zebra", ".git"))
        os.makedirs(os.path.join(tmp, "alpha", ".git"))
        os.makedirs(os.path.join(tmp, "middle", ".git"))
        repos = find_repos(tmp)
        names = [os.path.basename(r) for r in repos]
        assert names == ["alpha", "middle", "zebra"]
