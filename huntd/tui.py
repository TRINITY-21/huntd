"""Textual TUI dashboard — interactive git analytics viewer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Static
from textual_plotext import PlotextPlot

from huntd.analytics import (
    DAYS,
    Analytics,
    build_analytics,
)
from huntd.git import RepoInfo, scan_repo
from huntd.scanner import find_repos


class OverviewPanel(Static):
    """Stats overview card."""

    def update_data(self, analytics: Analytics) -> None:
        s = analytics.streaks
        a = analytics.activity
        hour = f"{a.busiest_hour}:00" if a.busiest_hour < 12 else f"{a.busiest_hour - 12 or 12}pm"
        if a.busiest_hour < 12:
            hour = f"{a.busiest_hour or 12}am"

        text = Text()
        text.append("  Repos: ", style="dim")
        text.append(f"{analytics.total_repos}", style="bold cyan")
        text.append("    Commits: ", style="dim")
        text.append(f"{analytics.total_commits:,}", style="bold cyan")
        text.append("    Languages: ", style="dim")
        text.append(f"{analytics.total_languages}", style="bold cyan")
        text.append("\n")
        text.append("  Current streak: ", style="dim")
        text.append(f"{s.current} days", style="bold green")
        text.append("    Longest: ", style="dim")
        text.append(f"{s.longest} days", style="bold yellow")
        text.append("\n")
        text.append("  Most active: ", style="dim")
        text.append(f"{a.busiest_day}s at {hour}", style="bold magenta")
        text.append("    Avg: ", style="dim")
        text.append(f"{a.avg_commits_per_day}/day", style="bold")

        self.update(text)


class HeatmapPanel(PlotextPlot):
    """GitHub-style contribution heatmap."""

    def update_data(self, analytics: Analytics) -> None:
        plt = self.plt
        plt.clear_figure()
        plt.theme("dark")

        matrix = analytics.heatmap
        if not matrix or not any(any(row) for row in matrix):
            plt.title("No commit data")
            self.refresh()
            return

        # Reverse rows so Monday is at top
        display = list(reversed(matrix))
        plt.matrix_plot(display)
        plt.title("Contributions (last 52 weeks)")
        plt.xlabel("")
        plt.ylabel("")
        self.refresh()


class LanguagePanel(PlotextPlot):
    """Language breakdown bar chart."""

    def update_data(self, analytics: Analytics) -> None:
        plt = self.plt
        plt.clear_figure()
        plt.theme("dark")

        langs = analytics.languages
        if not langs:
            plt.title("No language data")
            self.refresh()
            return

        # Top 8 languages
        items = list(langs.items())[:8]
        names = [n for n, _ in reversed(items)]
        values = [v for _, v in reversed(items)]

        plt.bar(names, values, orientation="horizontal", color="cyan")
        plt.title("Lines Changed by Language")
        plt.xlabel("")
        self.refresh()


class ActivityPanel(PlotextPlot):
    """Activity by hour of day."""

    def update_data(self, analytics: Analytics) -> None:
        plt = self.plt
        plt.clear_figure()
        plt.theme("dark")

        hours = analytics.activity.commits_by_hour
        if not any(hours):
            plt.title("No activity data")
            self.refresh()
            return

        labels = [str(h) for h in range(24)]
        plt.bar(labels, hours, color="green")
        plt.title("Commits by Hour")
        plt.xlabel("Hour of Day")
        self.refresh()


class RepoTable(DataTable):
    """Scrollable repo rankings table."""

    def update_data(self, analytics: Analytics) -> None:
        self.clear(columns=True)
        self.add_columns("Repo", "Commits", "Language", "Health", "+Lines", "-Lines")
        for r in analytics.repo_rankings[:50]:
            health_bar = _health_bar(r.health_score)
            self.add_row(
                r.name,
                f"{r.commits:,}",
                r.primary_language,
                health_bar,
                f"+{r.lines_added:,}",
                f"-{r.lines_removed:,}",
            )


def _health_bar(score: int) -> str:
    """Render a small health bar: ████░░░░ 75"""
    filled = score // 10
    empty = 10 - filled
    return f"{'█' * filled}{'░' * empty} {score}"


class HuntdApp(App):
    """huntd — your coding fingerprint."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-gutter: 1;
        grid-rows: auto 1fr 1fr;
    }

    #overview {
        column-span: 2;
        height: auto;
        min-height: 5;
        border: solid $accent;
        padding: 0 1;
    }

    #heatmap {
        border: solid $secondary;
        min-height: 12;
    }

    #languages {
        border: solid $secondary;
        min-height: 12;
    }

    #repos {
        border: solid $secondary;
        min-height: 10;
    }

    #activity {
        border: solid $secondary;
        min-height: 10;
    }

    #loading {
        column-span: 2;
        row-span: 3;
        content-align: center middle;
        text-align: center;
        height: 100%;
    }

    .panel-title {
        dock: top;
        padding: 0 1;
        background: $boost;
    }
    """

    TITLE = "huntd"
    SUB_TITLE = "your coding fingerprint"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next Panel"),
        Binding("shift+tab", "focus_previous", "Prev Panel"),
    ]

    def __init__(self, scan_path: str) -> None:
        super().__init__()
        self.scan_path = scan_path
        self.analytics: Optional[Analytics] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("  Scanning repos...", id="loading")
        yield Footer()

    def on_mount(self) -> None:
        self.run_scan()

    @work(thread=True)
    def run_scan(self) -> None:
        """Scan repos in a background thread."""
        repo_paths = find_repos(self.scan_path)
        if not repo_paths:
            self.call_from_thread(self._show_no_repos)
            return

        # Update loading text
        self.call_from_thread(
            self._update_loading, f"  Found {len(repo_paths)} repos. Scanning..."
        )

        # Parallel scan
        repos: list[RepoInfo] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(scan_repo, p): p for p in repo_paths}
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    repos.append(future.result())
                except Exception:
                    pass
                self.call_from_thread(
                    self._update_loading,
                    f"  Scanning repo {i}/{len(repo_paths)}..."
                )

        analytics = build_analytics(repos)
        self.analytics = analytics
        self.call_from_thread(self._render_dashboard, analytics)

    def _update_loading(self, text: str) -> None:
        try:
            loading = self.query_one("#loading", Label)
            loading.update(text)
        except Exception:
            pass

    def _show_no_repos(self) -> None:
        try:
            loading = self.query_one("#loading", Label)
            loading.update("  No git repos found. Try: huntd ~/code")
        except Exception:
            pass

    def _render_dashboard(self, analytics: Analytics) -> None:
        """Remove loading screen and mount dashboard widgets."""
        try:
            self.query_one("#loading").remove()
        except Exception:
            pass

        overview = OverviewPanel(id="overview")
        heatmap = HeatmapPanel(id="heatmap")
        languages = LanguagePanel(id="languages")
        repos = RepoTable(id="repos")
        activity = ActivityPanel(id="activity")

        self.mount(overview, before=self.query_one(Footer))
        self.mount(heatmap, before=self.query_one(Footer))
        self.mount(languages, before=self.query_one(Footer))
        self.mount(repos, before=self.query_one(Footer))
        self.mount(activity, before=self.query_one(Footer))

        overview.update_data(analytics)
        heatmap.update_data(analytics)
        languages.update_data(analytics)
        repos.update_data(analytics)
        activity.update_data(analytics)


def run_tui(scan_path: str) -> None:
    """Launch the huntd TUI dashboard."""
    app = HuntdApp(scan_path)
    app.run()
