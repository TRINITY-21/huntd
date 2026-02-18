"""Shared visual constants and helpers for huntd."""

from __future__ import annotations

from rich.style import Style
from rich.text import Text

# ── Color Palette (GitHub Dark + Neon Accents) ──────────────────────────

BG = "#0d1117"
SURFACE = "#161b22"
BORDER = "#30363d"
BORDER_DIM = "#21262d"
MUTED = "#8b949e"
FG = "#e6edf3"

CYAN = "#58a6ff"
GREEN = "#39d353"
PURPLE = "#bc8cff"
YELLOW = "#e3b341"
RED = "#f85149"
ORANGE = "#f0883e"

# GitHub contribution heatmap scale (5 levels: empty → hot)
HEAT_COLORS = [SURFACE, "#0e4429", "#006d32", "#26a641", GREEN]

# Per-panel accent colors
ACCENT_OVERVIEW = CYAN
ACCENT_HEATMAP = GREEN
ACCENT_LANGUAGES = PURPLE
ACCENT_REPOS = CYAN
ACCENT_ACTIVITY = YELLOW

# ── ASCII Banner ────────────────────────────────────────────────────────

BANNER = r"""
  _                _      _
 | |__  _   _ _ __| |_ __| |
 | '_ \| | | | '_ \ __/ _` |
 | | | | |_| | | | | || (_| |
 |_| |_|\__,_|_| |_|\__\__,_|"""

TAGLINE = "your coding fingerprint"

# ── Language Icons (Universal Unicode — no Nerd Fonts needed) ───────────

LANG_ICONS: dict[str, str] = {
    "Python": "🐍",
    "JavaScript": "📜",
    "TypeScript": "📘",
    "Go": "🔷",
    "Rust": "⚙️",
    "Ruby": "💎",
    "Java": "☕",
    "Kotlin": "🟣",
    "Swift": "🍎",
    "C": "🔧",
    "C++": "🔧",
    "C#": "🟪",
    "PHP": "🐘",
    "Dart": "🎯",
    "HTML": "🌐",
    "CSS": "🎨",
    "Shell": "🐚",
    "SQL": "🗄️",
    "Lua": "🌙",
    "Zig": "⚡",
    "Vue": "💚",
    "Svelte": "🔥",
}

# ── Stat Icons ──────────────────────────────────────────────────────────

ICON_STREAK = "🔥"
ICON_REPOS = "📦"
ICON_COMMITS = "📝"
ICON_LANGS = "🔤"
ICON_CALENDAR = "📅"
ICON_CLOCK = "⏰"
ICON_HEALTH = "💚"
ICON_ACTIVITY = "⚡"

# ── Sparkline Characters ────────────────────────────────────────────────

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int | float]) -> str:
    """Render a list of values as a sparkline string."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    spread = hi - lo or 1
    return "".join(
        SPARK_CHARS[min(int((v - lo) / spread * (len(SPARK_CHARS) - 1)), len(SPARK_CHARS) - 1)]
        for v in values
    )


# ── Gradient Bar ────────────────────────────────────────────────────────

def gradient_bar(
    value: int | float,
    max_val: int | float,
    width: int = 20,
    colors: list[str] | None = None,
) -> Text:
    """Render a gradient progress bar as Rich Text."""
    if colors is None:
        colors = [GREEN, CYAN, PURPLE]

    filled = int((value / max(max_val, 1)) * width)
    text = Text()

    for i in range(width):
        if i < filled:
            color_idx = min(int(i / max(width - 1, 1) * len(colors)), len(colors) - 1)
            text.append("█", style=Style(color=colors[color_idx]))
        else:
            text.append("░", style=Style(color=BORDER))

    return text


def health_bar(score: int, width: int = 10) -> Text:
    """Render a health score bar with color based on score."""
    color = health_color(score)
    filled = score // (100 // width)
    text = Text()
    text.append("█" * filled, style=Style(color=color))
    text.append("░" * (width - filled), style=Style(color=BORDER))
    text.append(f" {score}", style=Style(color=color, bold=True))
    return text


def health_color(score: int) -> str:
    """Return color string based on health score."""
    if score >= 80:
        return GREEN
    if score >= 50:
        return YELLOW
    return RED


# ── Heatmap Rendering ──────────────────────────────────────────────────

def heatmap_block(count: int) -> tuple[str, str]:
    """Return (character, color) for a heatmap cell based on commit count."""
    if count == 0:
        return "░", HEAT_COLORS[0]
    if count <= 2:
        return "▒", HEAT_COLORS[1]
    if count <= 5:
        return "▓", HEAT_COLORS[2]
    if count <= 9:
        return "█", HEAT_COLORS[3]
    return "█", HEAT_COLORS[4]


def render_heatmap(matrix: list[list[int]], day_labels: bool = True) -> Text:
    """Render a 7×N heatmap matrix as Rich Text with GitHub green colors.

    matrix: 7 rows (Mon-Sun) × N cols (weeks, newest on right).
    """
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    text = Text()

    for row_idx, row in enumerate(matrix):
        if day_labels:
            text.append(f" {days[row_idx]} ", style=Style(color=MUTED))

        for count in row:
            char, color = heatmap_block(count)
            text.append(char, style=Style(color=color))

        text.append("\n")

    return text


# ── Banner Rendering ────────────────────────────────────────────────────

def render_banner() -> Text:
    """Render the huntd ASCII banner as styled Rich Text."""
    text = Text(justify="center")
    for line in BANNER.strip().split("\n"):
        text.append(line + "\n", style=Style(color=GREEN, bold=True))
    text.append(f"  {TAGLINE}\n", style=Style(color=MUTED, italic=True))
    return text
