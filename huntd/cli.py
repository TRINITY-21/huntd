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


def _scan_all(scan_path: str) -> list[RepoInfo]:
    """Find and scan all repos under scan_path with progress output."""
    repo_paths = find_repos(scan_path)
    if not repo_paths:
        return []

    print(f"  Found {len(repo_paths)} repos. Scanning...", file=sys.stderr)

    repos: list[RepoInfo] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(scan_repo, p): p for p in repo_paths}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                repos.append(future.result())
            except Exception:
                pass
            print(f"\r  [{i}/{len(repo_paths)}]", end="", file=sys.stderr)

    print(file=sys.stderr)
    return repos


def print_summary(scan_path: str) -> None:
    """Print a one-shot Rich summary to stdout."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    console = Console()

    repos = _scan_all(scan_path)
    if not repos:
        console.print("[red]No git repos found.[/red] Try: huntd ~/code")
        return

    analytics = build_analytics(repos)
    s = analytics.streaks
    a = analytics.activity

    hour = f"{a.busiest_hour}:00" if a.busiest_hour < 12 else f"{a.busiest_hour - 12 or 12}pm"
    if a.busiest_hour < 12:
        hour = f"{a.busiest_hour or 12}am"

    # Overview
    overview = Text()
    overview.append(f"  Repos: {analytics.total_repos}", style="bold cyan")
    overview.append(f"    Commits: {analytics.total_commits:,}", style="bold cyan")
    overview.append(f"    Languages: {analytics.total_languages}", style="bold cyan")
    overview.append(f"\n  Current streak: {s.current} days", style="bold green")
    overview.append(f"    Longest: {s.longest} days", style="bold yellow")
    overview.append(f"\n  Most active: {a.busiest_day}s at {hour}", style="bold magenta")
    overview.append(f"    Avg: {a.avg_commits_per_day}/day", style="bold")

    console.print(Panel(overview, title="[bold]huntd[/bold] — your coding fingerprint", border_style="cyan"))

    # Top repos table
    table = Table(title="Top Repos", border_style="dim")
    table.add_column("Repo", style="cyan")
    table.add_column("Commits", justify="right", style="green")
    table.add_column("Language", style="yellow")
    table.add_column("Health", justify="right")
    table.add_column("+Lines", justify="right", style="green")
    table.add_column("-Lines", justify="right", style="red")

    for r in analytics.repo_rankings[:15]:
        filled = r.health_score // 10
        bar = f"{'█' * filled}{'░' * (10 - filled)} {r.health_score}"
        table.add_row(
            r.name,
            f"{r.commits:,}",
            r.primary_language,
            bar,
            f"+{r.lines_added:,}",
            f"-{r.lines_removed:,}",
        )

    console.print(table)

    # Languages
    if analytics.languages:
        lang_table = Table(title="Languages", border_style="dim")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Lines Changed", justify="right", style="green")
        lang_table.add_column("", min_width=20)

        total = sum(analytics.languages.values()) or 1
        for lang, lines in list(analytics.languages.items())[:10]:
            pct = lines / total * 100
            bar_len = int(pct / 5)
            bar = f"{'█' * bar_len}{'░' * (20 - bar_len)} {pct:.0f}%"
            lang_table.add_row(lang, f"{lines:,}", bar)

        console.print(lang_table)

    # Activity
    console.print(
        Panel(
            f"  Busiest day: [bold]{a.busiest_day}[/bold]    "
            f"Busiest hour: [bold]{hour}[/bold]    "
            f"Avg: [bold]{a.avg_commits_per_day}/day[/bold]",
            title="Activity",
            border_style="dim",
        )
    )


def print_json(scan_path: str) -> None:
    """Dump analytics as JSON to stdout."""
    repos = _scan_all(scan_path)
    if not repos:
        print(json.dumps({"error": "No repos found"}))
        return

    analytics = build_analytics(repos)
    data = {
        "total_repos": analytics.total_repos,
        "total_commits": analytics.total_commits,
        "total_languages": analytics.total_languages,
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
        "--version",
        action="version",
        version=f"huntd {__version__}",
    )

    args = parser.parse_args()

    if args.json_output:
        print_json(args.path)
    elif args.summary:
        print_summary(args.path)
    else:
        from huntd.tui import run_tui
        run_tui(args.path)


if __name__ == "__main__":
    main()
