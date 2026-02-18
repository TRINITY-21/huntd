"""CLI entry point for huntd."""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from huntd import __version__
from huntd.analytics import DAYS, build_analytics
from huntd.git import RepoInfo, scan_repo
from huntd.scanner import find_repos


def _scan_all(
    scan_path: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> list[RepoInfo]:
    """Find and scan all repos under scan_path with progress output."""
    repo_paths = find_repos(scan_path)
    if not repo_paths:
        return []

    print(f"  Found {len(repo_paths)} repos. Scanning...", file=sys.stderr)

    repos: list[RepoInfo] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(scan_repo, p, since=since, until=until, author=author): p
            for p in repo_paths
        }
        for i, future in enumerate(as_completed(futures), 1):
            try:
                repos.append(future.result())
            except Exception:
                pass
            name = futures[future].split("/")[-1]
            print(f"\r  [{i}/{len(repo_paths)}] {name:<30}", end="", file=sys.stderr)

    print(file=sys.stderr)
    return repos


def _format_hour(h: int) -> str:
    """Format 24h hour as readable string."""
    if h == 0:
        return "12am"
    if h < 12:
        return f"{h}am"
    if h == 12:
        return "12pm"
    return f"{h - 12}pm"


def _filter_label(
    since: str | None,
    until: str | None,
    author: str | None,
) -> str | None:
    """Build a filter description string, or None if no filters."""
    parts = []
    if since:
        parts.append(f"since {since}")
    if until:
        parts.append(f"until {until}")
    if author:
        parts.append(f"author: {author}")
    return " | ".join(parts) if parts else None


def print_summary(
    scan_path: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> None:
    """Print a one-shot Rich summary to stdout."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.table import Table
    from rich.text import Text

    from huntd.theme import (
        ACCENT_ACTIVITY,
        ACCENT_HEATMAP,
        ACCENT_LANGUAGES,
        ACCENT_REPOS,
        CYAN,
        GREEN,
        MUTED,
        PURPLE,
        RED,
        SURFACE,
        YELLOW,
        gradient_bar,
        health_bar,
        health_color,
        render_banner,
        render_heatmap,
        sparkline,
    )

    console = Console()

    # Banner
    console.print(render_banner())

    # Filter indicator
    flabel = _filter_label(since, until, author)
    if flabel:
        console.print(f"  [dim]Filtered:[/dim] [{CYAN}]{flabel}[/{CYAN}]\n")

    repos = _scan_all(scan_path, since=since, until=until, author=author)
    if not repos:
        console.print(f"[{RED}]No git repos found.[/{RED}] Try: huntd ~/code")
        return

    analytics = build_analytics(repos)
    s = analytics.streaks
    a = analytics.activity
    hour = _format_hour(a.busiest_hour)

    # Overview panel
    overview = Text()
    overview.append(f"  {analytics.total_repos}", style=f"bold {CYAN}")
    overview.append(" repos", style=f"{MUTED}")
    overview.append(f"    {analytics.total_commits:,}", style=f"bold {CYAN}")
    overview.append(" commits", style=f"{MUTED}")
    overview.append(f"    {analytics.total_languages}", style=f"bold {CYAN}")
    overview.append(" languages", style=f"{MUTED}")

    overview.append(f"\n  🔥 {s.current}", style=f"bold {GREEN}")
    overview.append(" day streak", style=f"{MUTED}")
    overview.append(f"    🏆 {s.longest}", style=f"bold {YELLOW}")
    overview.append(" longest", style=f"{MUTED}")

    overview.append(f"\n  📅 {a.busiest_day}s", style=f"bold {PURPLE}")
    overview.append(f" at {hour}", style=f"{MUTED}")
    overview.append(f"    ⚡ {a.avg_commits_per_day}", style=f"bold {GREEN}")
    overview.append("/day", style=f"{MUTED}")

    # Weekly sparkline
    week_data = a.commits_by_dow if hasattr(a, "commits_by_dow") else []
    if week_data:
        spark = sparkline(week_data)
        overview.append(f"\n  📊 ", style=f"{MUTED}")
        overview.append(spark, style=f"bold {GREEN}")
        overview.append("  Mon→Sun", style=f"{MUTED}")

    console.print(Panel(
        overview,
        title=f"[bold {GREEN}]🐺 huntd[/bold {GREEN}]",
        border_style=GREEN,
        padding=(1, 1),
    ))

    # Heatmap
    if analytics.heatmap:
        console.print(Rule(f"[bold {ACCENT_HEATMAP}]📊 Contributions[/bold {ACCENT_HEATMAP}]", style=ACCENT_HEATMAP))
        heatmap_text = render_heatmap(analytics.heatmap)
        console.print(heatmap_text)
        console.print()

    # Top repos table
    console.print(Rule(f"[bold {ACCENT_REPOS}]📦 Repositories[/bold {ACCENT_REPOS}]", style=ACCENT_REPOS))
    table = Table(border_style=SURFACE, show_edge=True, pad_edge=True)
    table.add_column("Repo", style=f"bold {CYAN}")
    table.add_column("Commits", justify="right", style=f"bold {GREEN}")
    table.add_column("Language", style=YELLOW)
    table.add_column("Health", justify="right", no_wrap=True)
    table.add_column("+Lines", justify="right", style=GREEN)
    table.add_column("-Lines", justify="right", style=RED)

    for r in analytics.repo_rankings[:15]:
        hbar = health_bar(r.health_score)
        table.add_row(
            r.name,
            f"{r.commits:,}",
            r.primary_language,
            hbar,
            f"+{r.lines_added:,}",
            f"-{r.lines_removed:,}",
        )

    console.print(table)
    console.print()

    # Languages
    if analytics.languages:
        console.print(Rule(f"[bold {ACCENT_LANGUAGES}]🔤 Languages[/bold {ACCENT_LANGUAGES}]", style=ACCENT_LANGUAGES))
        lang_table = Table(border_style=SURFACE, show_edge=True, pad_edge=True)
        lang_table.add_column("Language", style=f"bold {CYAN}")
        lang_table.add_column("Lines Changed", justify="right", style=f"bold {GREEN}")
        lang_table.add_column("", min_width=24, no_wrap=True)

        total = sum(analytics.languages.values()) or 1
        lang_items = list(analytics.languages.items())[:10]
        top_val = lang_items[0][1] if lang_items else 1
        colors_cycle = [GREEN, CYAN, PURPLE, YELLOW, GREEN, CYAN, PURPLE, YELLOW, GREEN, CYAN]

        for idx, (lang, lines) in enumerate(lang_items):
            pct = lines / total * 100
            bar = gradient_bar(lines, top_val, width=20, colors=[colors_cycle[idx]])
            bar.append(f" {pct:.0f}%", style=f"bold {MUTED}")
            lang_table.add_row(lang, f"{lines:,}", bar)

        console.print(lang_table)
        console.print()

    # Activity
    console.print(Rule(f"[bold {ACCENT_ACTIVITY}]⚡ Activity[/bold {ACCENT_ACTIVITY}]", style=ACCENT_ACTIVITY))
    hourly_spark = sparkline(a.commits_by_hour) if a.commits_by_hour else ""
    activity = Text()
    activity.append(f"  📅 Busiest day:  ", style=f"{MUTED}")
    activity.append(f"{a.busiest_day}", style=f"bold {PURPLE}")
    activity.append(f"    ⏰ Busiest hour: ", style=f"{MUTED}")
    activity.append(f"{hour}", style=f"bold {YELLOW}")
    activity.append(f"    ⚡ Avg: ", style=f"{MUTED}")
    activity.append(f"{a.avg_commits_per_day}/day", style=f"bold {GREEN}")
    if hourly_spark:
        activity.append(f"\n  📊 Hourly: ", style=f"{MUTED}")
        activity.append(hourly_spark, style=f"bold {CYAN}")
        activity.append("  0h→23h", style=f"{MUTED}")

    console.print(Panel(activity, border_style=ACCENT_ACTIVITY, padding=(0, 1)))
    console.print()


def print_json(
    scan_path: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> None:
    """Dump analytics as JSON to stdout."""
    repos = _scan_all(scan_path, since=since, until=until, author=author)
    if not repos:
        print(json.dumps({"error": "No repos found"}))
        return

    analytics = build_analytics(repos)
    data = {
        "total_repos": analytics.total_repos,
        "total_commits": analytics.total_commits,
        "total_languages": analytics.total_languages,
        "filters": {
            "since": since,
            "until": until,
            "author": author,
        },
        "streaks": {
            "current": analytics.streaks.current,
            "longest": analytics.streaks.longest,
            "today_commits": analytics.streaks.today_commits,
        },
        "activity": {
            "busiest_day": analytics.activity.busiest_day,
            "busiest_hour": analytics.activity.busiest_hour,
            "avg_commits_per_day": analytics.activity.avg_commits_per_day,
            "commits_by_hour": analytics.activity.commits_by_hour,
            "commits_by_dow": analytics.activity.commits_by_dow,
        },
        "heatmap": analytics.heatmap,
        "languages": analytics.languages,
        "repos": [
            {
                "name": r.name,
                "commits": r.commits,
                "primary_language": r.primary_language,
                "health_score": r.health_score,
                "lines_added": r.lines_added,
                "lines_removed": r.lines_removed,
            }
            for r in analytics.repo_rankings
        ],
    }
    print(json.dumps(data, indent=2))


def compare_summary(
    path1: str,
    path2: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> None:
    """Print side-by-side comparison of two directories."""
    from rich.columns import Columns
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    from huntd.theme import CYAN, GREEN, MUTED, YELLOW, render_banner

    console = Console()
    console.print(render_banner())

    repos1 = _scan_all(path1, since=since, until=until, author=author)
    repos2 = _scan_all(path2, since=since, until=until, author=author)

    def _make_panel(repos: list[RepoInfo], label: str) -> Panel:
        if not repos:
            return Panel(f"[{MUTED}]No repos found[/{MUTED}]", title=f"[bold {CYAN}]{label}[/bold {CYAN}]", border_style=CYAN)

        a = build_analytics(repos)
        s = a.streaks
        t = Text()
        t.append(f"  📦 {a.total_repos}", style=f"bold {CYAN}")
        t.append(" repos\n", style=MUTED)
        t.append(f"  📝 {a.total_commits:,}", style=f"bold {GREEN}")
        t.append(" commits\n", style=MUTED)
        t.append(f"  🔤 {a.total_languages}", style=f"bold {YELLOW}")
        t.append(" languages\n", style=MUTED)
        t.append(f"  🔥 {s.current}", style=f"bold {GREEN}")
        t.append(" day streak\n", style=MUTED)
        t.append(f"  🏆 {s.longest}", style=f"bold {YELLOW}")
        t.append(" longest\n", style=MUTED)

        if a.languages:
            top_lang = next(iter(a.languages))
            t.append(f"  🥇 {top_lang}", style=f"bold {CYAN}")
            t.append(" top language\n", style=MUTED)

        return Panel(t, title=f"[bold {CYAN}]{label}[/bold {CYAN}]", border_style=CYAN, padding=(1, 1))

    p1 = _make_panel(repos1, path1.rstrip("/").split("/")[-1])
    p2 = _make_panel(repos2, path2.rstrip("/").split("/")[-1])
    console.print(Columns([p1, p2], equal=True, expand=True))


def compare_json(
    path1: str,
    path2: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> None:
    """Dump comparison of two directories as JSON."""
    def _build(scan_path: str) -> dict:
        repos = _scan_all(scan_path, since=since, until=until, author=author)
        if not repos:
            return {"error": "No repos found", "path": scan_path}
        a = build_analytics(repos)
        return {
            "path": scan_path,
            "total_repos": a.total_repos,
            "total_commits": a.total_commits,
            "total_languages": a.total_languages,
            "streaks": {"current": a.streaks.current, "longest": a.streaks.longest},
            "languages": a.languages,
        }

    data = {
        "compare": [_build(path1), _build(path2)],
        "filters": {"since": since, "until": until, "author": author},
    }
    print(json.dumps(data, indent=2))


def main() -> None:
    """Entry point for the huntd CLI."""
    parser = argparse.ArgumentParser(
        prog="huntd",
        description="Your coding fingerprint — local git analytics dashboard.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan for git repos (default: current directory)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a one-shot summary (no TUI)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output analytics as JSON",
    )
    parser.add_argument(
        "--since",
        metavar="DATE",
        help="Filter commits from this date (e.g. 2025-01-01, '3 months ago')",
    )
    parser.add_argument(
        "--until",
        metavar="DATE",
        help="Filter commits up to this date",
    )
    parser.add_argument(
        "--author",
        metavar="NAME",
        help="Filter by author name or email (substring match)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar="PATH",
        help="Compare two directories side by side (use with --summary or --json)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"huntd {__version__}",
    )

    args = parser.parse_args()
    filters = dict(since=args.since, until=args.until, author=args.author)

    # Compare mode
    if args.compare:
        if args.json_output:
            compare_json(args.compare[0], args.compare[1], **filters)
        else:
            compare_summary(args.compare[0], args.compare[1], **filters)
        return

    # Normal mode
    if args.json_output:
        print_json(args.path, **filters)
    elif args.summary:
        print_summary(args.path, **filters)
    else:
        from huntd.tui import run_tui
        run_tui(args.path, **filters)


if __name__ == "__main__":
    main()
