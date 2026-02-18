"""Tests for the achievement system."""

from datetime import date, datetime, timedelta, timezone

from huntd.achievements import Achievement, compute_achievements
from huntd.analytics import (
    ActivityPattern,
    Analytics,
    CodeVelocity,
    FocusScore,
    LanguageEvolution,
    RepoRanking,
    Streaks,
    WorkdaySplit,
)


def _base_analytics(**overrides) -> Analytics:
    """Build a minimal Analytics with sensible defaults, overriding fields as needed."""
    defaults = dict(
        total_repos=1,
        total_commits=10,
        total_languages=1,
        streaks=Streaks(current=1, longest=1, today_commits=1),
        heatmap=[[0] * 52 for _ in range(7)],
        languages={"Python": 500},
        activity=ActivityPattern(
            busiest_day="Monday",
            busiest_hour=14,
            avg_commits_per_day=1.0,
            commits_by_hour=[0] * 24,
            commits_by_dow=[0] * 7,
        ),
        repo_rankings=[],
        language_evolution=LanguageEvolution(),
        code_velocity=CodeVelocity(),
        focus_score=FocusScore(),
        workday_split=WorkdaySplit(),
        file_hotspots=[],
    )
    defaults.update(overrides)
    return Analytics(**defaults)


# --- Basic ---

def test_compute_achievements_returns_list():
    a = _base_analytics()
    badges = compute_achievements(a)
    assert isinstance(badges, list)
    assert len(badges) == 10
    assert all(isinstance(b, Achievement) for b in badges)


def test_all_locked_by_default():
    a = _base_analytics()
    badges = compute_achievements(a)
    unlocked = [b for b in badges if b.unlocked]
    assert len(unlocked) == 0


# --- Streak achievements ---

def test_century_unlocked():
    a = _base_analytics(streaks=Streaks(current=100, longest=100, today_commits=1))
    badges = compute_achievements(a)
    century = next(b for b in badges if b.name == "Century")
    assert century.unlocked is True


def test_marathon_unlocked():
    a = _base_analytics(streaks=Streaks(current=365, longest=365, today_commits=1))
    badges = compute_achievements(a)
    marathon = next(b for b in badges if b.name == "Marathon")
    assert marathon.unlocked is True


def test_marathon_locked_at_364():
    a = _base_analytics(streaks=Streaks(current=364, longest=364, today_commits=1))
    badges = compute_achievements(a)
    marathon = next(b for b in badges if b.name == "Marathon")
    assert marathon.unlocked is False


# --- Commit volume ---

def test_prolific_unlocked():
    a = _base_analytics(total_commits=1000)
    badges = compute_achievements(a)
    prolific = next(b for b in badges if b.name == "Prolific")
    assert prolific.unlocked is True


def test_prolific_locked_under_1000():
    a = _base_analytics(total_commits=999)
    badges = compute_achievements(a)
    prolific = next(b for b in badges if b.name == "Prolific")
    assert prolific.unlocked is False


# --- Time-of-day ---

def test_night_owl_unlocked():
    hours = [0] * 24
    hours[2] = 100  # 2am dominance
    a = _base_analytics(activity=ActivityPattern(
        busiest_day="Monday", busiest_hour=2, avg_commits_per_day=1.0,
        commits_by_hour=hours, commits_by_dow=[0] * 7,
    ))
    badges = compute_achievements(a)
    owl = next(b for b in badges if b.name == "Night Owl")
    assert owl.unlocked is True


def test_early_bird_unlocked():
    hours = [0] * 24
    hours[6] = 100  # 6am dominance
    a = _base_analytics(activity=ActivityPattern(
        busiest_day="Monday", busiest_hour=6, avg_commits_per_day=1.0,
        commits_by_hour=hours, commits_by_dow=[0] * 7,
    ))
    badges = compute_achievements(a)
    bird = next(b for b in badges if b.name == "Early Bird")
    assert bird.unlocked is True


# --- Weekend warrior ---

def test_weekend_warrior_unlocked():
    a = _base_analytics(workday_split=WorkdaySplit(
        weekday_commits=60, weekend_commits=40,
        weekday_pct=60.0, weekend_pct=40.0,
        weekday_lines=0, weekend_lines=0,
    ))
    badges = compute_achievements(a)
    warrior = next(b for b in badges if b.name == "Weekend Warrior")
    assert warrior.unlocked is True


def test_weekend_warrior_locked_under_40():
    a = _base_analytics(workday_split=WorkdaySplit(
        weekday_commits=70, weekend_commits=30,
        weekday_pct=70.0, weekend_pct=30.0,
        weekday_lines=0, weekend_lines=0,
    ))
    badges = compute_achievements(a)
    warrior = next(b for b in badges if b.name == "Weekend Warrior")
    assert warrior.unlocked is False


# --- Language diversity ---

def test_polyglot_unlocked():
    langs = {f"Lang{i}": 200 for i in range(5)}
    a = _base_analytics(languages=langs, total_languages=5)
    badges = compute_achievements(a)
    poly = next(b for b in badges if b.name == "Polyglot")
    assert poly.unlocked is True


def test_polyglot_locked_few_languages():
    langs = {"Python": 500, "JS": 200}
    a = _base_analytics(languages=langs, total_languages=2)
    badges = compute_achievements(a)
    poly = next(b for b in badges if b.name == "Polyglot")
    assert poly.unlocked is False


# --- Repo achievements ---

def test_diversified_unlocked():
    a = _base_analytics(total_repos=10)
    badges = compute_achievements(a)
    div = next(b for b in badges if b.name == "Diversified")
    assert div.unlocked is True


def test_monorepo_monster_unlocked():
    ranking = RepoRanking(path="/fake/bigrepo", name="bigrepo", commits=500,
                          primary_language="Python", health_score=80,
                          lines_added=5000, lines_removed=1000)
    a = _base_analytics(repo_rankings=[ranking])
    badges = compute_achievements(a)
    mono = next(b for b in badges if b.name == "Monorepo Monster")
    assert mono.unlocked is True


# --- Health ---

def test_clean_freak_unlocked():
    rankings = [
        RepoRanking(path="/a", name="a", commits=10, primary_language="Py", health_score=90, lines_added=100, lines_removed=10),
        RepoRanking(path="/b", name="b", commits=20, primary_language="Py", health_score=85, lines_added=200, lines_removed=20),
    ]
    a = _base_analytics(repo_rankings=rankings)
    badges = compute_achievements(a)
    clean = next(b for b in badges if b.name == "Clean Freak")
    assert clean.unlocked is True


def test_clean_freak_locked_low_health():
    rankings = [
        RepoRanking(path="/a", name="a", commits=10, primary_language="Py", health_score=90, lines_added=100, lines_removed=10),
        RepoRanking(path="/b", name="b", commits=20, primary_language="Py", health_score=50, lines_added=200, lines_removed=20),
    ]
    a = _base_analytics(repo_rankings=rankings)
    badges = compute_achievements(a)
    clean = next(b for b in badges if b.name == "Clean Freak")
    assert clean.unlocked is False
