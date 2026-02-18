"""Export utilities — wrapped SVG card, markdown report, and badge SVG."""

from __future__ import annotations

from datetime import date

from huntd.achievements import compute_achievements
from huntd.analytics import Analytics
from huntd.theme import BG, CYAN, GREEN, MUTED, PURPLE, RED, SURFACE, YELLOW


# ── Wrapped SVG Card ──────────────────────────────────────────────────

def generate_wrapped_svg(analytics: Analytics) -> str:
    """Generate a Spotify Wrapped-style SVG card from analytics data."""
    s = analytics.streaks
    a = analytics.activity

    top_lang = next(iter(analytics.languages), "—")
    top_repo = analytics.repo_rankings[0].name if analytics.repo_rankings else "—"
    top_repo_commits = analytics.repo_rankings[0].commits if analytics.repo_rankings else 0

    badges = compute_achievements(analytics)
    unlocked = [b for b in badges if b.unlocked]
    badge_text = ", ".join(b.name for b in unlocked[:5]) if unlocked else "None yet"

    if a.busiest_hour == 0:
        hour = "12am"
    elif a.busiest_hour < 12:
        hour = f"{a.busiest_hour}am"
    elif a.busiest_hour == 12:
        hour = "12pm"
    else:
        hour = f"{a.busiest_hour - 12}pm"

    year = date.today().year

    # Build heatmap mini-grid (7 rows x last 20 weeks)
    heatmap_rects = ""
    matrix = analytics.heatmap
    if matrix and any(any(row) for row in matrix):
        max_val = max(max(row) for row in matrix) or 1
        heat_colors = [SURFACE, "#0e4429", "#006d32", "#26a641", GREEN]
        cols = min(len(matrix[0]), 20)
        start_col = len(matrix[0]) - cols
        for row_idx in range(7):
            for col_idx in range(cols):
                val = matrix[row_idx][start_col + col_idx]
                ratio = val / max_val if val > 0 else 0
                if ratio == 0:
                    ci = 0
                elif ratio < 0.25:
                    ci = 1
                elif ratio < 0.5:
                    ci = 2
                elif ratio < 0.75:
                    ci = 3
                else:
                    ci = 4
                x = 40 + col_idx * 14
                y = 350 + row_idx * 14
                heatmap_rects += (
                    f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" '
                    f'fill="{heat_colors[ci]}" />\n'
                )

    # Language bars (top 5)
    lang_bars = ""
    lang_items = list(analytics.languages.items())[:5]
    if lang_items:
        top_val = lang_items[0][1] or 1
        bar_colors = [GREEN, CYAN, PURPLE, YELLOW, RED]
        for i, (lang, lines) in enumerate(lang_items):
            y = 530 + i * 30
            bar_w = max(10, int((lines / top_val) * 250))
            lang_bars += (
                f'<text x="40" y="{y + 14}" fill="{MUTED}" '
                f'font-size="13" font-family="monospace">{lang}</text>\n'
                f'<rect x="160" y="{y + 2}" width="{bar_w}" height="16" rx="3" '
                f'fill="{bar_colors[i % len(bar_colors)]}" opacity="0.85" />\n'
                f'<text x="{165 + bar_w}" y="{y + 14}" fill="{MUTED}" '
                f'font-size="11" font-family="monospace">{lines:,}</text>\n'
            )

    card_height = 720 if lang_items else 550

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{card_height}" viewBox="0 0 480 {card_height}">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{BG}" />
      <stop offset="100%" style="stop-color:{SURFACE}" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="480" height="{card_height}" rx="16" fill="url(#bg-grad)" />
  <rect width="480" height="{card_height}" rx="16" fill="none" stroke="{GREEN}" stroke-width="1.5" opacity="0.4" />

  <!-- Header -->
  <text x="40" y="50" fill="{GREEN}" font-size="28" font-weight="bold" font-family="monospace">huntd</text>
  <text x="142" y="50" fill="{MUTED}" font-size="14" font-family="monospace">wrapped {year}</text>

  <!-- Divider -->
  <line x1="40" y1="65" x2="440" y2="65" stroke="{GREEN}" stroke-width="0.5" opacity="0.3" />

  <!-- Stats Grid -->
  <text x="40" y="100" fill="{MUTED}" font-size="12" font-family="monospace">TOTAL COMMITS</text>
  <text x="40" y="125" fill="{CYAN}" font-size="24" font-weight="bold" font-family="monospace">{analytics.total_commits:,}</text>

  <text x="260" y="100" fill="{MUTED}" font-size="12" font-family="monospace">REPOSITORIES</text>
  <text x="260" y="125" fill="{CYAN}" font-size="24" font-weight="bold" font-family="monospace">{analytics.total_repos}</text>

  <text x="40" y="165" fill="{MUTED}" font-size="12" font-family="monospace">LANGUAGES</text>
  <text x="40" y="190" fill="{CYAN}" font-size="24" font-weight="bold" font-family="monospace">{analytics.total_languages}</text>

  <text x="260" y="165" fill="{MUTED}" font-size="12" font-family="monospace">CURRENT STREAK</text>
  <text x="260" y="190" fill="{GREEN}" font-size="24" font-weight="bold" font-family="monospace">{s.current} days</text>

  <!-- Highlights -->
  <text x="40" y="235" fill="{MUTED}" font-size="12" font-family="monospace">TOP LANGUAGE</text>
  <text x="40" y="258" fill="{PURPLE}" font-size="20" font-weight="bold" font-family="monospace">{top_lang}</text>

  <text x="260" y="235" fill="{MUTED}" font-size="12" font-family="monospace">TOP REPO</text>
  <text x="260" y="258" fill="{PURPLE}" font-size="20" font-weight="bold" font-family="monospace">{top_repo}</text>

  <text x="40" y="295" fill="{MUTED}" font-size="12" font-family="monospace">BUSIEST</text>
  <text x="40" y="318" fill="{YELLOW}" font-size="20" font-weight="bold" font-family="monospace">{a.busiest_day}s at {hour}</text>

  <text x="260" y="295" fill="{MUTED}" font-size="12" font-family="monospace">LONGEST STREAK</text>
  <text x="260" y="318" fill="{YELLOW}" font-size="20" font-weight="bold" font-family="monospace">{s.longest} days</text>

  <!-- Heatmap -->
  <text x="40" y="345" fill="{MUTED}" font-size="11" font-family="monospace">RECENT ACTIVITY</text>
  {heatmap_rects}

  <!-- Languages -->
  <text x="40" y="520" fill="{MUTED}" font-size="11" font-family="monospace">TOP LANGUAGES</text>
  {lang_bars}

  <!-- Achievements -->
  <text x="40" y="{card_height - 40}" fill="{MUTED}" font-size="11" font-family="monospace">ACHIEVEMENTS ({len(unlocked)}/{len(badges)})</text>
  <text x="40" y="{card_height - 20}" fill="{GREEN}" font-size="13" font-family="monospace">{badge_text}</text>
</svg>"""


# ── Markdown Report ───────────────────────────────────────────────────

def generate_report_md(analytics: Analytics) -> str:
    """Generate a clean markdown report from analytics data."""
    s = analytics.streaks
    a = analytics.activity

    top_lang = next(iter(analytics.languages), "—")

    if a.busiest_hour == 0:
        hour = "12am"
    elif a.busiest_hour < 12:
        hour = f"{a.busiest_hour}am"
    elif a.busiest_hour == 12:
        hour = "12pm"
    else:
        hour = f"{a.busiest_hour - 12}pm"

    year = date.today().year

    lines = [
        f"# huntd Report — {year}",
        "",
        "## Overview",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Repositories | {analytics.total_repos} |",
        f"| Total Commits | {analytics.total_commits:,} |",
        f"| Languages | {analytics.total_languages} |",
        f"| Current Streak | {s.current} days |",
        f"| Longest Streak | {s.longest} days |",
        f"| Busiest Day | {a.busiest_day} |",
        f"| Busiest Hour | {hour} |",
        f"| Avg Commits/Day | {a.avg_commits_per_day} |",
        "",
    ]

    # Top repos
    if analytics.repo_rankings:
        lines.append("## Top Repositories")
        lines.append("")
        lines.append("| Repo | Commits | Language | Health | +Lines | -Lines |")
        lines.append("|------|---------|----------|--------|--------|--------|")
        for r in analytics.repo_rankings[:15]:
            lines.append(
                f"| {r.name} | {r.commits:,} | {r.primary_language} | "
                f"{r.health_score}/100 | +{r.lines_added:,} | -{r.lines_removed:,} |"
            )
        lines.append("")

    # Languages
    if analytics.languages:
        lines.append("## Languages")
        lines.append("")
        lines.append("| Language | Lines Changed |")
        lines.append("|----------|---------------|")
        total = sum(analytics.languages.values()) or 1
        for lang, val in list(analytics.languages.items())[:10]:
            pct = val / total * 100
            lines.append(f"| {lang} | {val:,} ({pct:.1f}%) |")
        lines.append("")

    # Velocity
    cv = analytics.code_velocity
    if cv.commits_by_week:
        lines.append("## Code Velocity")
        lines.append("")
        lines.append(f"- **Trend:** {cv.trend}")
        lines.append(f"- **Peak week:** {cv.peak_week} ({cv.peak_commits} commits)")
        lines.append("")

    # Focus
    fs = analytics.focus_score
    if fs.avg_repos_per_day > 0:
        lines.append("## Focus Score")
        lines.append("")
        lines.append(f"- **Avg repos/day:** {fs.avg_repos_per_day}")
        lines.append(f"- **Interpretation:** {fs.interpretation}")
        lines.append(f"- **Most focused day:** {fs.most_focused_day}")
        lines.append(f"- **Most scattered day:** {fs.most_scattered_day}")
        lines.append("")

    # Workday split
    ws = analytics.workday_split
    if ws.weekday_commits + ws.weekend_commits > 0:
        lines.append("## Weekday vs Weekend")
        lines.append("")
        lines.append(f"| | Commits | Percentage | Lines |")
        lines.append(f"|---|---------|------------|-------|")
        lines.append(f"| Weekday | {ws.weekday_commits:,} | {ws.weekday_pct}% | +{ws.weekday_lines:,} |")
        lines.append(f"| Weekend | {ws.weekend_commits:,} | {ws.weekend_pct}% | +{ws.weekend_lines:,} |")
        lines.append("")

    # File hotspots
    if analytics.file_hotspots:
        lines.append("## File Hotspots")
        lines.append("")
        lines.append("| File | Churn | Touches |")
        lines.append("|------|-------|---------|")
        for h in analytics.file_hotspots[:10]:
            lines.append(f"| {h.path} | {h.churn:,} | {h.touches} |")
        lines.append("")

    # Achievements
    badges = compute_achievements(analytics)
    unlocked = [b for b in badges if b.unlocked]
    lines.append(f"## Achievements ({len(unlocked)}/{len(badges)})")
    lines.append("")
    for b in badges:
        check = "x" if b.unlocked else " "
        lines.append(f"- [{check}] {b.icon} **{b.name}** — {b.description}")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated by [huntd](https://github.com/TRINITY-21/huntd)*")
    lines.append("")

    return "\n".join(lines)


# ── Badge SVG ─────────────────────────────────────────────────────────

def generate_badge_svg(analytics: Analytics) -> str:
    """Generate a shields.io-style SVG badge with streak and top language."""
    s = analytics.streaks
    top_lang = next(iter(analytics.languages), "—")

    label = "huntd"
    value = f"{s.current}d streak | {top_lang}"

    label_w = len(label) * 7 + 12
    value_w = len(value) * 7 + 12
    total_w = label_w + value_w

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="20">
  <linearGradient id="a" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="20" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="20" fill="#555"/>
    <rect x="{label_w}" width="{value_w}" height="20" fill="{GREEN}"/>
    <rect width="{total_w}" height="20" fill="url(#a)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,sans-serif" font-size="11">
    <text x="{label_w / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_w / 2}" y="14">{label}</text>
    <text x="{label_w + value_w / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_w + value_w / 2}" y="14">{value}</text>
  </g>
</svg>"""
