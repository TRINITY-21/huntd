"""Tests for analytics computations."""

from datetime import date, datetime, timedelta, timezone

from huntd.analytics import (
    compute_activity_patterns,
    compute_health_score,
    compute_heatmap,
    compute_languages,
    compute_streaks,
)
from huntd.git import Commit, FileChange, RepoInfo


def _make_commit(days_ago: int = 0, hour: int = 12, insertions: int = 10, deletions: int = 5) -> Commit:
    """Create a test commit at `days_ago` days in the past at a specific local hour."""
    today = date.today()
    d = today - timedelta(days=days_ago)
    # Create a naive datetime at the specified hour, then make it tz-aware in local time
    ts = datetime(d.year, d.month, d.day, hour, 30, 0).astimezone()
    return Commit(
        hash="abc123",
        author="Test",
        email="test@test.com",
        timestamp=ts,
        subject="test commit",
        insertions=insertions,
        deletions=deletions,
        files_changed=1,
    )


# --- Streaks ---

def test_streaks_empty():
    s = compute_streaks([])
    assert s.current == 0
    assert s.longest == 0


def test_streaks_today_only():
    commits = [_make_commit(0)]
    s = compute_streaks(commits)
    assert s.current == 1
    assert s.longest == 1


def test_streaks_consecutive_days():
    commits = [_make_commit(0), _make_commit(1), _make_commit(2)]
    s = compute_streaks(commits)
    assert s.current == 3
    assert s.longest == 3


def test_streaks_gap():
    commits = [_make_commit(0), _make_commit(1), _make_commit(5), _make_commit(6)]
    s = compute_streaks(commits)
    assert s.current == 2  # today + yesterday
    assert s.longest == 2


def test_streaks_no_today():
    commits = [_make_commit(1), _make_commit(2), _make_commit(3)]
    s = compute_streaks(commits)
    assert s.current == 3  # starts from yesterday
    assert s.longest == 3


def test_streaks_multiple_commits_same_day():
    commits = [_make_commit(0), _make_commit(0), _make_commit(0)]
    s = compute_streaks(commits)
    assert s.current == 1
    assert s.longest == 1


# --- Heatmap ---

def test_heatmap_shape():
    commits = [_make_commit(i) for i in range(10)]
    matrix = compute_heatmap(commits, weeks=52)
    assert len(matrix) == 7
    assert len(matrix[0]) == 52


def test_heatmap_empty():
    matrix = compute_heatmap([], weeks=52)
    assert len(matrix) == 7
    assert all(all(v == 0 for v in row) for row in matrix)


def test_heatmap_has_values():
    commits = [_make_commit(0), _make_commit(1), _make_commit(2)]
    matrix = compute_heatmap(commits, weeks=52)
    total = sum(sum(row) for row in matrix)
    assert total == 3


# --- Languages ---

def test_languages_basic():
    changes = [
        FileChange("a", datetime.now(timezone.utc), "main.py", ".py", 100, 20),
        FileChange("b", datetime.now(timezone.utc), "app.js", ".js", 50, 10),
        FileChange("c", datetime.now(timezone.utc), "util.py", ".py", 30, 5),
    ]
    langs = compute_languages(changes)
    assert "Python" in langs
    assert "JavaScript" in langs
    assert langs["Python"] > langs["JavaScript"]


def test_languages_empty():
    langs = compute_languages([])
    assert langs == {}


def test_languages_unknown_ext():
    changes = [
        FileChange("a", datetime.now(timezone.utc), "data.xyz", ".xyz", 10, 0),
    ]
    langs = compute_languages(changes)
    assert ".xyz" in langs


# --- Activity ---

def test_activity_patterns():
    commits = [_make_commit(i, hour=14) for i in range(7)]
    a = compute_activity_patterns(commits)
    assert a.busiest_hour == 14
    assert a.avg_commits_per_day > 0


def test_activity_empty():
    a = compute_activity_patterns([])
    assert a.busiest_day == ""
    assert a.avg_commits_per_day == 0.0


def test_activity_commits_by_hour():
    commits = [_make_commit(0, hour=10), _make_commit(1, hour=10), _make_commit(2, hour=22)]
    a = compute_activity_patterns(commits)
    assert a.commits_by_hour[10] >= 2


# --- Health Score ---

def test_health_score_perfect():
    repo = RepoInfo(
        path="/test",
        name="test",
        branch_count=2,
        last_commit=datetime.now(timezone.utc),
        has_readme=True,
        total_commits=150,
        is_dirty=False,
    )
    score = compute_health_score(repo)
    assert score == 100  # 40 + 20 + 15 + 15 + 10


def test_health_score_minimal():
    repo = RepoInfo(path="/test", name="test")
    score = compute_health_score(repo)
    assert score == 0


def test_health_score_old_repo():
    repo = RepoInfo(
        path="/test",
        name="test",
        branch_count=3,
        last_commit=datetime.now(timezone.utc) - timedelta(days=60),
        has_readme=True,
        total_commits=25,
        is_dirty=True,
    )
    score = compute_health_score(repo)
    # 20 (90d) + 10 (25 commits) + 15 (readme) + 15 (branches) + 0 (dirty) = 60
    assert score == 60
