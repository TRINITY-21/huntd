"""Tests for analytics computations."""

from datetime import date, datetime, timedelta, timezone

from huntd.analytics import (
    compute_activity_patterns,
    compute_code_velocity,
    compute_file_hotspots,
    compute_focus_score,
    compute_health_score,
    compute_heatmap,
    compute_language_evolution,
    compute_languages,
    compute_streaks,
    compute_workday_split,
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


# --- Helpers for v0.3 tests ---

def _make_file_change(days_ago: int, ext: str, added: int = 50, removed: int = 10) -> FileChange:
    today = date.today()
    d = today - timedelta(days=days_ago)
    ts = datetime(d.year, d.month, d.day, 12, 0, 0).astimezone()
    return FileChange(hash="abc123", timestamp=ts, path=f"file{ext}", ext=ext, added=added, removed=removed)


def _make_repo_with_commits(name: str, days_list: list[int]) -> RepoInfo:
    commits = [_make_commit(d) for d in days_list]
    return RepoInfo(path=f"/fake/{name}", name=name, commits=commits)


def _make_repo_with_file_changes(name: str, changes: list[FileChange]) -> RepoInfo:
    return RepoInfo(path=f"/fake/{name}", name=name, file_changes=changes)


# --- Language Evolution ---

def test_language_evolution_empty():
    le = compute_language_evolution([])
    assert le.monthly == {}
    assert le.top_languages == []


def test_language_evolution_groups_by_month():
    changes = [
        _make_file_change(0, ".py", added=100),
        _make_file_change(0, ".js", added=50),
        _make_file_change(40, ".py", added=200),
    ]
    le = compute_language_evolution(changes)
    assert len(le.monthly) >= 1
    assert "Python" in le.top_languages


def test_language_evolution_top_languages_ordered():
    changes = [_make_file_change(0, ".py", added=500)] * 3
    changes += [_make_file_change(0, ".js", added=10)]
    le = compute_language_evolution(changes)
    assert le.top_languages[0] == "Python"


# --- Code Velocity ---

def test_code_velocity_empty():
    cv = compute_code_velocity([])
    assert cv.commits_by_week == {}
    assert cv.trend == "stable"
    assert cv.peak_commits == 0


def test_code_velocity_groups_by_week():
    commits = [_make_commit(i) for i in range(14)]
    cv = compute_code_velocity(commits)
    assert len(cv.commits_by_week) >= 2
    assert cv.peak_commits > 0
    assert cv.peak_week != ""


def test_code_velocity_trend_stable_on_short_history():
    commits = [_make_commit(i * 7) for i in range(3)]
    cv = compute_code_velocity(commits)
    assert cv.trend == "stable"


# --- Focus Score ---

def test_focus_score_empty():
    fs = compute_focus_score([])
    assert fs.avg_repos_per_day == 0.0


def test_focus_score_single_repo():
    repo = _make_repo_with_commits("myproject", [0, 1, 2, 3, 4])
    fs = compute_focus_score([repo])
    assert fs.avg_repos_per_day == 1.0
    assert fs.interpretation == "deep focus"


def test_focus_score_multiple_repos():
    r1 = _make_repo_with_commits("a", [0, 1])
    r2 = _make_repo_with_commits("b", [0, 2])
    r3 = _make_repo_with_commits("c", [0])
    fs = compute_focus_score([r1, r2, r3])
    assert fs.avg_repos_per_day > 1.0
    assert fs.most_scattered_day != ""


# --- Workday Split ---

def test_workday_split_empty():
    ws = compute_workday_split([])
    assert ws.weekday_commits == 0
    assert ws.weekend_commits == 0


def test_workday_split_all_weekday():
    today = date.today()
    commits = []
    for weeks_ago in range(4):
        d = today - timedelta(days=today.weekday() + weeks_ago * 7)
        ts = datetime(d.year, d.month, d.day, 10, 0, 0).astimezone()
        commits.append(Commit("h", "T", "t@t", ts, "s", 10, 5, 1))
    ws = compute_workday_split(commits)
    assert ws.weekday_commits == 4
    assert ws.weekend_commits == 0
    assert ws.weekday_pct == 100.0


def test_workday_split_percentages_sum():
    commits = [_make_commit(i) for i in range(14)]
    ws = compute_workday_split(commits)
    total = ws.weekday_commits + ws.weekend_commits
    assert total == 14
    assert abs(ws.weekday_pct + ws.weekend_pct - 100.0) < 0.1


# --- File Hotspots ---

def test_file_hotspots_empty():
    result = compute_file_hotspots([])
    assert result == []


def test_file_hotspots_prefixes_repo_name():
    fc = FileChange("hash1", datetime.now(timezone.utc), "src/main.py", ".py", 200, 50)
    repo = _make_repo_with_file_changes("myrepo", [fc])
    hotspots = compute_file_hotspots([repo])
    assert hotspots[0].path == "myrepo/src/main.py"


def test_file_hotspots_sorted_by_churn():
    fc1 = FileChange("h1", datetime.now(timezone.utc), "big.py", ".py", 1000, 500)
    fc2 = FileChange("h2", datetime.now(timezone.utc), "small.py", ".py", 10, 5)
    repo = _make_repo_with_file_changes("r", [fc1, fc2])
    hotspots = compute_file_hotspots([repo])
    assert hotspots[0].path == "r/big.py"
    assert hotspots[0].churn > hotspots[1].churn


def test_file_hotspots_counts_unique_touches():
    fc1 = FileChange("hash1", datetime.now(timezone.utc), "hot.py", ".py", 100, 0)
    fc2 = FileChange("hash2", datetime.now(timezone.utc), "hot.py", ".py", 200, 0)
    repo = _make_repo_with_file_changes("r", [fc1, fc2])
    hotspots = compute_file_hotspots([repo])
    assert hotspots[0].touches == 2
    assert hotspots[0].churn == 300


def test_file_hotspots_respects_top_n():
    changes = [
        FileChange(f"h{i}", datetime.now(timezone.utc), f"file{i}.py", ".py", i * 10, 0)
        for i in range(20)
    ]
    repo = _make_repo_with_file_changes("r", changes)
    hotspots = compute_file_hotspots([repo], top_n=5)
    assert len(hotspots) == 5
