"""Achievement system — unlock badges based on coding stats."""

from __future__ import annotations

from dataclasses import dataclass

from huntd.analytics import Analytics


@dataclass
class Achievement:
    name: str
    icon: str
    description: str
    unlocked: bool = False


def compute_achievements(analytics: Analytics) -> list[Achievement]:
    """Check all achievement conditions against analytics data."""
    achievements: list[Achievement] = []

    # --- Streak achievements ---
    achievements.append(Achievement(
        name="Century",
        icon="💯",
        description="100-day coding streak",
        unlocked=analytics.streaks.longest >= 100,
    ))
    achievements.append(Achievement(
        name="Marathon",
        icon="🏅",
        description="365-day coding streak",
        unlocked=analytics.streaks.longest >= 365,
    ))

    # --- Commit volume ---
    achievements.append(Achievement(
        name="Prolific",
        icon="📝",
        description="1,000+ total commits",
        unlocked=analytics.total_commits >= 1000,
    ))

    # --- Time-of-day achievements ---
    by_hour = analytics.activity.commits_by_hour
    total = sum(by_hour) or 1
    night_commits = sum(by_hour[0:6])  # midnight to 5am
    morning_commits = sum(by_hour[5:9])  # 5am to 8am

    achievements.append(Achievement(
        name="Night Owl",
        icon="🦉",
        description="50%+ commits after midnight",
        unlocked=(night_commits / total) >= 0.5,
    ))
    achievements.append(Achievement(
        name="Early Bird",
        icon="🐦",
        description="50%+ commits before 9am",
        unlocked=(morning_commits / total) >= 0.5,
    ))

    # --- Weekend warrior ---
    ws = analytics.workday_split
    achievements.append(Achievement(
        name="Weekend Warrior",
        icon="🗡️",
        description="40%+ commits on weekends",
        unlocked=ws.weekend_pct >= 40,
    ))

    # --- Language diversity ---
    langs_with_100_plus = sum(1 for lines in analytics.languages.values() if lines >= 100)
    achievements.append(Achievement(
        name="Polyglot",
        icon="🌍",
        description="5+ languages with 100+ lines each",
        unlocked=langs_with_100_plus >= 5,
    ))

    # --- Repo achievements ---
    achievements.append(Achievement(
        name="Diversified",
        icon="📦",
        description="10+ active repos",
        unlocked=analytics.total_repos >= 10,
    ))

    monorepo = any(r.commits >= 500 for r in analytics.repo_rankings)
    achievements.append(Achievement(
        name="Monorepo Monster",
        icon="🐙",
        description="Single repo with 500+ commits",
        unlocked=monorepo,
    ))

    # --- Health ---
    all_healthy = (
        len(analytics.repo_rankings) > 0
        and all(r.health_score >= 80 for r in analytics.repo_rankings)
    )
    achievements.append(Achievement(
        name="Clean Freak",
        icon="✨",
        description="All repos have health score 80+",
        unlocked=all_healthy,
    ))

    return achievements
