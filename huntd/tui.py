"""Textual TUI dashboard — interactive git analytics viewer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from rich.style import Style
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Label, LoadingIndicator, Static
from textual_plotext import PlotextPlot

from huntd.analytics import Analytics, build_analytics
from huntd.git import RepoInfo, scan_repo
from huntd.scanner import find_repos
from huntd.theme import (
    ACCENT_ACTIVITY,
    ACCENT_HEATMAP,
    ACCENT_LANGUAGES,
    ACCENT_REPOS,
    BANNER,
    BG,
    BORDER,
    CYAN,
    GREEN,
    MUTED,
    ORANGE,
    PURPLE,
    RED,
    SURFACE,
    TAGLINE,
    YELLOW,
    health_bar,
    health_color,
    render_heatmap,
    sparkline,
)


class BannerWidget(Static):
    """ASCII art banner at the top of the dashboard."""

    def render(self) -> Text:
        text = Text(justify="center")
        for line in BANNER.strip().split("\n"):
            text.append(line + "\n", style=Style(color=GREEN, bold=True))
        text.append(f"  {TAGLINE}", style=Style(color=MUTED, italic=True))
        return text


class OverviewPanel(Static):
    """Stats overview card."""

    def update_data(self, analytics: Analytics) -> None:
        s = analytics.streaks
        a = analytics.activity

        if a.busiest_hour == 0:
            hour = "12am"
        elif a.busiest_hour < 12:
            hour = f"{a.busiest_hour}am"
        elif a.busiest_hour == 12:
            hour = "12pm"
        else:
            hour = f"{a.busiest_hour - 12}pm"

        text = Text()

        # Row 1: counts
        text.append("  📦 ", style=Style(color=MUTED))
        text.append(f"{analytics.total_repos}", style=Style(color=CYAN, bold=True))
        text.append(" repos", style=Style(color=MUTED))
        text.append("    📝 ", style=Style(color=MUTED))
        text.append(f"{analytics.total_commits:,}", style=Style(color=CYAN, bold=True))
        text.append(" commits", style=Style(color=MUTED))
        text.append("    🔤 ", style=Style(color=MUTED))
        text.append(f"{analytics.total_languages}", style=Style(color=CYAN, bold=True))
        text.append(" languages", style=Style(color=MUTED))

        # Row 2: streaks
        text.append("\n  🔥 ", style=Style(color=MUTED))
        text.append(f"{s.current}", style=Style(color=GREEN, bold=True))
        text.append(" day streak", style=Style(color=MUTED))
        text.append("    🏆 ", style=Style(color=MUTED))
        text.append(f"{s.longest}", style=Style(color=YELLOW, bold=True))
        text.append(" longest", style=Style(color=MUTED))

        # Row 3: activity
        text.append("\n  📅 ", style=Style(color=MUTED))
        text.append(f"{a.busiest_day}s", style=Style(color=PURPLE, bold=True))
        text.append(f" at {hour}", style=Style(color=MUTED))
        text.append("    ⚡ ", style=Style(color=MUTED))
        text.append(f"{a.avg_commits_per_day}", style=Style(color=GREEN, bold=True))
        text.append("/day", style=Style(color=MUTED))

        # Row 4: weekly sparkline
        week_data = a.commits_by_dow if hasattr(a, "commits_by_dow") else []
        if week_data and any(week_data):
            spark = sparkline(week_data)
            text.append("\n  📊 ", style=Style(color=MUTED))
            text.append(spark, style=Style(color=GREEN, bold=True))
            text.append("  Mon→Sun", style=Style(color=MUTED))

        self.update(text)


class HeatmapPanel(Static):
    """GitHub-style contribution heatmap using colored block characters."""

    def update_data(self, analytics: Analytics) -> None:
        matrix = analytics.heatmap
        if not matrix or not any(any(row) for row in matrix):
            self.update(Text("  No commit data", style=Style(color=MUTED)))
            return

        heatmap_text = render_heatmap(matrix)
        self.update(heatmap_text)


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

        # Cycle through accent colors
        color_cycle = [
            (57, 211, 83),    # green
            (88, 166, 255),   # cyan
            (188, 140, 255),  # purple
            (227, 179, 65),   # yellow
            (57, 211, 83),
            (88, 166, 255),
            (188, 140, 255),
            (227, 179, 65),
        ]
        colors = list(reversed(color_cycle[:len(items)]))

        plt.bar(names, values, orientation="horizontal", color=colors)
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

        # Color each bar based on intensity
        max_val = max(hours) or 1
        colors = []
        for h in hours:
            ratio = h / max_val
            if ratio > 0.75:
                colors.append((57, 211, 83))    # bright green
            elif ratio > 0.5:
                colors.append((38, 166, 65))    # medium green
            elif ratio > 0.25:
                colors.append((0, 109, 50))     # dark green
            else:
                colors.append((14, 68, 41))     # very dark green

        plt.bar(labels, hours, color=colors)
        plt.title("Commits by Hour")
        plt.xlabel("Hour of Day")
        self.refresh()


class RepoTable(DataTable):
    """Scrollable repo rankings table."""

    def update_data(self, analytics: Analytics) -> None:
        self.clear(columns=True)
        self.add_columns("Repo", "Commits", "Language", "Health", "+Lines", "-Lines")
        for r in analytics.repo_rankings[:50]:
            hbar = health_bar(r.health_score)
            self.add_row(
                Text(r.name, style=Style(color=CYAN, bold=True)),
                Text(f"{r.commits:,}", style=Style(color=GREEN, bold=True)),
                Text(r.primary_language, style=Style(color=YELLOW)),
                hbar,
                Text(f"+{r.lines_added:,}", style=Style(color=GREEN)),
                Text(f"-{r.lines_removed:,}", style=Style(color=RED)),
            )


class CodeVelocityPanel(PlotextPlot):
    """Weekly commit count bar chart."""

    def update_data(self, analytics: Analytics) -> None:
        plt = self.plt
        plt.clear_figure()
        plt.theme("dark")

        cv = analytics.code_velocity
        if not cv.commits_by_week:
            plt.title("No velocity data")
            self.refresh()
            return

        weeks = sorted(cv.commits_by_week.keys())[-16:]
        values = [cv.commits_by_week[w] for w in weeks]
        labels = [w.split("-W")[1] if "-W" in w else w for w in weeks]

        if cv.trend == "up":
            color = (57, 211, 83)
        elif cv.trend == "down":
            color = (248, 81, 73)
        else:
            color = (88, 166, 255)

        plt.bar(labels, values, color=color)
        plt.title(f"Weekly Commits ({cv.trend})")
        plt.xlabel("ISO Week")
        self.refresh()


class LanguageEvolutionPanel(PlotextPlot):
    """Language mix over time — multi-line chart."""

    def update_data(self, analytics: Analytics) -> None:
        plt = self.plt
        plt.clear_figure()
        plt.theme("dark")

        le = analytics.language_evolution
        if not le.monthly or not le.top_languages:
            plt.title("No language evolution data")
            self.refresh()
            return

        month_keys = sorted(le.monthly.keys())[-12:]
        color_map = [
            (57, 211, 83), (88, 166, 255), (188, 140, 255), (227, 179, 65),
            (248, 81, 73), (240, 136, 62), (57, 211, 83), (88, 166, 255),
        ]

        for i, lang in enumerate(le.top_languages[:6]):
            values = [le.monthly[mk].get(lang, 0) for mk in month_keys]
            if any(values):
                plt.plot(month_keys, values, label=lang, color=color_map[i % len(color_map)])

        plt.title("Language Lines Changed")
        plt.xlabel("Month")
        self.refresh()


class FocusScorePanel(Static):
    """Focus score display."""

    def update_data(self, analytics: Analytics) -> None:
        fs = analytics.focus_score
        text = Text()

        if fs.avg_repos_per_day == 0:
            text.append("  No focus data", style=Style(color=MUTED))
            self.update(text)
            return

        if fs.interpretation == "deep focus":
            score_color = GREEN
        elif fs.interpretation == "balanced":
            score_color = YELLOW
        else:
            score_color = RED

        text.append("  Avg repos/day: ", style=Style(color=MUTED))
        text.append(f"{fs.avg_repos_per_day}", style=Style(color=CYAN, bold=True))
        text.append(f"  [{fs.interpretation}]", style=Style(color=score_color, bold=True))
        text.append("\n  Most focused:   ", style=Style(color=MUTED))
        text.append(fs.most_focused_day, style=Style(color=GREEN, bold=True))
        text.append("\n  Most scattered: ", style=Style(color=MUTED))
        text.append(fs.most_scattered_day, style=Style(color=YELLOW, bold=True))

        self.update(text)


class WorkdaySplitPanel(Static):
    """Weekday vs weekend commit split."""

    def update_data(self, analytics: Analytics) -> None:
        ws = analytics.workday_split
        text = Text()

        total = ws.weekday_commits + ws.weekend_commits
        if total == 0:
            text.append("  No split data", style=Style(color=MUTED))
            self.update(text)
            return

        text.append("  Weekday: ", style=Style(color=MUTED))
        text.append(f"{ws.weekday_pct}%", style=Style(color=GREEN, bold=True))
        text.append(f"  {ws.weekday_commits:,} commits", style=Style(color=MUTED))
        text.append(f"\n  Weekend: ", style=Style(color=MUTED))
        text.append(f"{ws.weekend_pct}%", style=Style(color=PURPLE, bold=True))
        text.append(f"  {ws.weekend_commits:,} commits", style=Style(color=MUTED))

        self.update(text)


class HotspotTable(DataTable):
    """Most-churned files table."""

    def update_data(self, analytics: Analytics) -> None:
        self.clear(columns=True)
        self.add_columns("File", "Churn", "Touches")
        for h in analytics.file_hotspots[:15]:
            self.add_row(
                Text(h.path, style=Style(color=CYAN)),
                Text(f"{h.churn:,}", style=Style(color=RED, bold=True)),
                Text(str(h.touches), style=Style(color=YELLOW)),
            )


class HuntdApp(App):
    """huntd — your coding fingerprint."""

    CSS = f"""
    Screen {{
        background: {BG};
        color: {MUTED};
        layout: grid;
        grid-size: 2 7;
        grid-gutter: 1;
        grid-rows: auto auto 1fr 1fr 1fr 1fr 1fr;
    }}

    Header {{
        background: {SURFACE};
        color: {GREEN};
    }}

    Footer {{
        background: {SURFACE};
        color: {MUTED};
    }}

    #banner {{
        column-span: 2;
        height: auto;
        content-align: center middle;
        background: {BG};
    }}

    #overview {{
        column-span: 2;
        height: auto;
        min-height: 6;
        border: round {BORDER};
        background: {SURFACE};
        padding: 1 2;
    }}

    #heatmap {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 12;
        padding: 0 1;
        overflow-y: auto;
    }}

    #languages {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 12;
    }}

    #repos {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 10;
    }}

    #activity {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 10;
    }}

    #velocity {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 10;
    }}

    #lang-evolution {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 10;
    }}

    #focus {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 6;
        padding: 1 2;
    }}

    #workday {{
        border: round {BORDER};
        background: {SURFACE};
        min-height: 6;
        padding: 1 2;
    }}

    #hotspots {{
        column-span: 2;
        border: round {BORDER};
        background: {SURFACE};
        min-height: 10;
    }}

    #loading-container {{
        column-span: 2;
        row-span: 4;
        content-align: center middle;
        text-align: center;
        height: 100%;
        background: {BG};
    }}

    LoadingIndicator {{
        color: {GREEN};
    }}

    #loading-text {{
        color: {MUTED};
        text-align: center;
        margin-top: 1;
    }}

    DataTable {{
        background: {SURFACE};
    }}

    DataTable > .datatable--header {{
        background: {BG};
        color: {CYAN};
        text-style: bold;
    }}

    DataTable > .datatable--cursor {{
        background: {BORDER};
        color: {GREEN};
    }}
    """

    TITLE = "🐺 huntd"
    SUB_TITLE = "your coding fingerprint"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("tab", "focus_next", "Next Panel"),
        Binding("shift+tab", "focus_previous", "Prev Panel"),
    ]

    def __init__(
        self,
        scan_path: str,
        *,
        since: str | None = None,
        until: str | None = None,
        author: str | None = None,
    ) -> None:
        super().__init__()
        self.scan_path = scan_path
        self.since = since
        self.until = until
        self.author = author
        self.analytics: Optional[Analytics] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="loading-container")
        yield Footer()

    def on_mount(self) -> None:
        container = self.query_one("#loading-container")
        container.mount(LoadingIndicator())
        container.mount(Label("  Scanning repos...", id="loading-text"))
        self.run_scan()

    def action_refresh(self) -> None:
        """Re-scan repos."""
        # Remove existing dashboard widgets
        for wid in ["#banner", "#overview", "#heatmap", "#languages", "#repos", "#activity",
                    "#velocity", "#lang-evolution", "#focus", "#workday", "#hotspots"]:
            try:
                self.query_one(wid).remove()
            except Exception:
                pass

        # Show loading again
        container = Static(id="loading-container")
        self.mount(container, before=self.query_one(Footer))
        container.mount(LoadingIndicator())
        container.mount(Label("  Scanning repos...", id="loading-text"))
        self.run_scan()

    @work(thread=True)
    def run_scan(self) -> None:
        """Scan repos in a background thread."""
        repo_paths = find_repos(self.scan_path)
        if not repo_paths:
            self.call_from_thread(self._show_no_repos)
            return

        self.call_from_thread(
            self._update_loading, f"  Found {len(repo_paths)} repos. Scanning..."
        )

        # Parallel scan
        repos: list[RepoInfo] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    scan_repo, p,
                    since=self.since, until=self.until, author=self.author,
                ): p
                for p in repo_paths
            }
            for i, future in enumerate(as_completed(futures), 1):
                try:
                    repos.append(future.result())
                except Exception:
                    pass
                name = futures[future].split("/")[-1]
                self.call_from_thread(
                    self._update_loading,
                    f"  [{i}/{len(repo_paths)}] {name}"
                )

        analytics = build_analytics(repos)
        self.analytics = analytics
        self.call_from_thread(self._render_dashboard, analytics)

    def _update_loading(self, text: str) -> None:
        try:
            loading = self.query_one("#loading-text", Label)
            loading.update(text)
        except Exception:
            pass

    def _show_no_repos(self) -> None:
        try:
            loading = self.query_one("#loading-text", Label)
            loading.update("  No git repos found. Try: huntd ~/code")
        except Exception:
            pass

    def _render_dashboard(self, analytics: Analytics) -> None:
        """Remove loading screen and mount dashboard widgets."""
        try:
            self.query_one("#loading-container").remove()
        except Exception:
            pass

        footer = self.query_one(Footer)

        banner = BannerWidget(id="banner")
        overview = OverviewPanel(id="overview")
        heatmap = HeatmapPanel(id="heatmap")
        languages = LanguagePanel(id="languages")
        repos = RepoTable(id="repos")
        activity = ActivityPanel(id="activity")

        velocity = CodeVelocityPanel(id="velocity")
        lang_evo = LanguageEvolutionPanel(id="lang-evolution")
        focus = FocusScorePanel(id="focus")
        workday = WorkdaySplitPanel(id="workday")
        hotspots = HotspotTable(id="hotspots")

        self.mount(banner, before=footer)
        self.mount(overview, before=footer)
        self.mount(heatmap, before=footer)
        self.mount(languages, before=footer)
        self.mount(repos, before=footer)
        self.mount(activity, before=footer)
        self.mount(velocity, before=footer)
        self.mount(lang_evo, before=footer)
        self.mount(focus, before=footer)
        self.mount(workday, before=footer)
        self.mount(hotspots, before=footer)

        # Set border titles with accents
        overview.border_title = "🐺 Overview"
        heatmap.border_title = "📊 Contributions"
        languages.border_title = "🔤 Languages"
        repos.border_title = "📦 Repositories"
        activity.border_title = "⚡ Activity"
        velocity.border_title = "📈 Velocity"
        lang_evo.border_title = "📈 Language Evolution"
        focus.border_title = "🎯 Focus Score"
        workday.border_title = "📅 Weekday vs Weekend"
        hotspots.border_title = "🔥 File Hotspots"

        overview.update_data(analytics)
        heatmap.update_data(analytics)
        languages.update_data(analytics)
        repos.update_data(analytics)
        activity.update_data(analytics)
        velocity.update_data(analytics)
        lang_evo.update_data(analytics)
        focus.update_data(analytics)
        workday.update_data(analytics)
        hotspots.update_data(analytics)


def run_tui(
    scan_path: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> None:
    """Launch the huntd TUI dashboard."""
    app = HuntdApp(scan_path, since=since, until=until, author=author)
    app.run()
