"""Analytics engine — compute streaks, heatmaps, language stats, and more."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from huntd.git import Commit, FileChange, RepoInfo


@dataclass
class Streaks:
    current: int = 0
    longest: int = 0
    today_commits: int = 0


@dataclass
class ActivityPattern:
    busiest_day: str = ""           # e.g. "Tuesday"
    busiest_hour: int = 0           # 0-23
    avg_commits_per_day: float = 0.0
    commits_by_hour: list[int] = field(default_factory=lambda: [0] * 24)
    commits_by_dow: list[int] = field(default_factory=lambda: [0] * 7)


@dataclass
class RepoRanking:
    name: str
    path: str
    commits: int
    primary_language: str
    health_score: int
    lines_added: int
    lines_removed: int
    last_commit: Optional[datetime] = None


@dataclass
class Analytics:
    total_repos: int = 0
    total_commits: int = 0
    total_languages: int = 0
    streaks: Streaks = field(default_factory=Streaks)
    heatmap: list[list[int]] = field(default_factory=list)  # 7 rows x N cols
    languages: dict[str, int] = field(default_factory=dict)
    repo_rankings: list[RepoRanking] = field(default_factory=list)
    activity: ActivityPattern = field(default_factory=ActivityPattern)


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# File extensions to readable language names
EXT_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "React JSX", ".tsx": "React TSX",
    ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".java": "Java", ".kt": "Kotlin", ".swift": "Swift",
    ".c": "C", ".cpp": "C++", ".h": "C/C++ Header",
    ".cs": "C#", ".php": "PHP", ".dart": "Dart",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".xml": "XML",
    ".md": "Markdown", ".txt": "Text",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL", ".r": "R", ".lua": "Lua",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".zig": "Zig", ".nim": "Nim", ".v": "V",
    ".sol": "Solidity", ".vue": "Vue", ".svelte": "Svelte",
}


def compute_streaks(all_commits: list[Commit]) -> Streaks:
    """Compute current and longest coding streaks from commit dates."""
    if not all_commits:
        return Streaks()

    # Get unique dates (in local time)
    dates: set[date] = set()
    for c in all_commits:
        if c.timestamp.tzinfo:
            d = c.timestamp.astimezone().date()
        else:
            d = c.timestamp.date()
        dates.add(d)

    if not dates:
        return Streaks()

    sorted_dates = sorted(dates)
    today = date.today()

    # Count today's commits
    today_commits = sum(
        1 for c in all_commits
        if (c.timestamp.astimezone().date() if c.timestamp.tzinfo else c.timestamp.date()) == today
    )

    # Compute longest streak
    longest = 1
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if sorted_dates[i] - sorted_dates[i - 1] == timedelta(days=1):
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    # Compute current streak (counting back from today or yesterday)
    current = 0
    check = today
    # Allow streak to start from yesterday if no commits today
    if check not in dates:
        check = today - timedelta(days=1)

    while check in dates:
        current += 1
        check -= timedelta(days=1)

    return Streaks(current=current, longest=longest, today_commits=today_commits)


def compute_heatmap(all_commits: list[Commit], weeks: int = 52) -> list[list[int]]:
    """Build a 7×N matrix of commit counts (Mon=0 to Sun=6 × weeks).

    Returns a list of 7 rows, each with `weeks` columns.
    """
    today = date.today()
    # Align to start of the week (Monday)
    start = today - timedelta(days=today.weekday(), weeks=weeks - 1)

    # Count commits per date
    counts: Counter[date] = Counter()
    for c in all_commits:
        d = c.timestamp.astimezone().date() if c.timestamp.tzinfo else c.timestamp.date()
        counts[d] += 1

    # Build matrix
    matrix = [[0] * weeks for _ in range(7)]
    for week in range(weeks):
        for dow in range(7):
            day = start + timedelta(weeks=week, days=dow)
            if day <= today:
                matrix[dow][week] = counts.get(day, 0)

    return matrix


def compute_languages(all_file_changes: list[FileChange]) -> dict[str, int]:
    """Aggregate lines changed by language (file extension)."""
    ext_counts: Counter[str] = Counter()
    for fc in all_file_changes:
        lang = EXT_MAP.get(fc.ext, fc.ext)
        ext_counts[lang] += fc.added + fc.removed

    # Sort by lines changed, descending
    return dict(ext_counts.most_common())


def compute_repo_rankings(repos: list[RepoInfo]) -> list[RepoRanking]:
    """Rank repos by commit count, compute primary language and health score."""
    rankings: list[RepoRanking] = []
    for repo in repos:
        # Primary language = most lines changed
        ext_counts: Counter[str] = Counter()
        for fc in repo.file_changes:
            lang = EXT_MAP.get(fc.ext, fc.ext)
            ext_counts[lang] += fc.added + fc.removed
        primary = ext_counts.most_common(1)[0][0] if ext_counts else "—"

        lines_added = sum(c.insertions for c in repo.commits)
        lines_removed = sum(c.deletions for c in repo.commits)
        health = compute_health_score(repo)

        rankings.append(RepoRanking(
            name=repo.name,
            path=repo.path,
            commits=len(repo.commits),
            primary_language=primary,
            health_score=health,
            lines_added=lines_added,
            lines_removed=lines_removed,
            last_commit=repo.last_commit,
        ))

    rankings.sort(key=lambda r: r.commits, reverse=True)
    return rankings


def compute_activity_patterns(all_commits: list[Commit]) -> ActivityPattern:
    """Compute when you code most — by hour and day of week."""
    if not all_commits:
        return ActivityPattern()

    by_hour = [0] * 24
    by_dow = [0] * 7

    for c in all_commits:
        local = c.timestamp.astimezone() if c.timestamp.tzinfo else c.timestamp
        by_hour[local.hour] += 1
        by_dow[local.weekday()] += 1

    busiest_hour = by_hour.index(max(by_hour))
    busiest_dow = by_dow.index(max(by_dow))

    # Average commits per day (from first commit to today)
    dates = set()
    for c in all_commits:
        d = c.timestamp.astimezone().date() if c.timestamp.tzinfo else c.timestamp.date()
        dates.add(d)
    if dates:
        span = (date.today() - min(dates)).days or 1
        avg = len(all_commits) / span
    else:
        avg = 0

    return ActivityPattern(
        busiest_day=DAYS[busiest_dow],
        busiest_hour=busiest_hour,
        avg_commits_per_day=round(avg, 1),
        commits_by_hour=by_hour,
        commits_by_dow=by_dow,
    )


def compute_health_score(repo: RepoInfo) -> int:
    """Compute a 0-100 health score for a repo.

    Factors:
    - Commit recency (40 pts): last commit within 7d=40, 30d=30, 90d=20, 365d=10, else 0
    - Total commits (20 pts): 100+=20, 50+=15, 10+=10, 1+=5
    - Has README (15 pts)
    - Branch hygiene (15 pts): 1-5 branches=15, 6-10=10, 11+=5
    - Not dirty (10 pts)
    """
    score = 0

    # Commit recency
    if repo.last_commit:
        now = datetime.now(timezone.utc)
        last = repo.last_commit if repo.last_commit.tzinfo else repo.last_commit.replace(tzinfo=timezone.utc)
        days_ago = (now - last).days
        if days_ago <= 7:
            score += 40
        elif days_ago <= 30:
            score += 30
        elif days_ago <= 90:
            score += 20
        elif days_ago <= 365:
            score += 10

    # Total commits
    if repo.total_commits >= 100:
        score += 20
    elif repo.total_commits >= 50:
        score += 15
    elif repo.total_commits >= 10:
        score += 10
    elif repo.total_commits >= 1:
        score += 5

    # README
    if repo.has_readme:
        score += 15

    # Branch hygiene
    if 1 <= repo.branch_count <= 5:
        score += 15
    elif 6 <= repo.branch_count <= 10:
        score += 10
    elif repo.branch_count > 10:
        score += 5

    # Clean working tree (only counts if repo has commits)
    if not repo.is_dirty and repo.total_commits > 0:
        score += 10

    return score


def build_analytics(repos: list[RepoInfo]) -> Analytics:
    """Build full analytics from a list of scanned repos."""
    all_commits: list[Commit] = []
    all_file_changes: list[FileChange] = []
    for repo in repos:
        all_commits.extend(repo.commits)
        all_file_changes.extend(repo.file_changes)

    languages = compute_languages(all_file_changes)

    return Analytics(
        total_repos=len(repos),
        total_commits=len(all_commits),
        total_languages=len(languages),
        streaks=compute_streaks(all_commits),
        heatmap=compute_heatmap(all_commits),
        languages=languages,
        repo_rankings=compute_repo_rankings(repos),
        activity=compute_activity_patterns(all_commits),
    )
