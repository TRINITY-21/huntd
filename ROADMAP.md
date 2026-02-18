# huntd Roadmap

## v0.1.1 (SHIPPED)

Core CLI + TUI dashboard. Multi-repo scanning, streaks, heatmaps, language breakdown, health scores, activity patterns. Three output modes: interactive TUI, `--summary`, `--json`. Published on PyPI and GitHub.

---

## v0.2 — Filters, Date Ranges & Visual Glow-Up

**Goal:** Make huntd queryable AND make it look sick. Current design is too basic — needs a techy, lively aesthetic.

### Filters

| Feature | Flag | Description |
|---------|------|-------------|
| Date range | `--since 2025-01-01 --until 2025-12-31` | Filter commits to a time window |
| Author filter | `--author "Joe"` | Filter by committer name/email |
| Compare mode | `--compare ~/work ~/personal` | Side-by-side analytics for two directories |

### Visual Overhaul (TUI + Summary)

| Upgrade | Description |
|---------|-------------|
| Color scheme | Neon/cyber palette — purple, cyan, green accents on dark background |
| ASCII art header | Stylized huntd wolf banner on launch |
| Gradient bars | Health scores and language bars with color gradients instead of plain blocks |
| Sparklines | Mini inline charts for velocity/activity instead of flat numbers |
| Animated scan | Loading animation with spinner + repo names flying by during scan |
| Panel borders | Rounded/double-line borders with accent colors per section |
| Icons/glyphs | Nerd Font glyphs for languages, stats, streaks (with fallback for basic terminals) |
| Heatmap colors | Green gradient like GitHub (grey → light green → dark green → bright green) |
| Summary mode | Same glow-up for `--summary` Rich output — not just tables, make it pop |

**What changes:**
- `cli.py` — new argparse flags for filters
- `git.py` — pass `--since`/`--until`/`--author` to `git log` calls
- `analytics.py` — no changes needed (already works on filtered commit lists)
- `tui.py` — full visual redesign: new CSS theme, gradient widgets, animated loading
- `cli.py` — `--summary` visual overhaul with Rich styling, panels, colors

---

## v0.3 — Deeper Insights

**Goal:** New analytics that no other tool provides.

| Feature | Description |
|---------|-------------|
| Language evolution | Monthly breakdown — how your language mix shifts over time |
| Code velocity | Commits/lines per week. Trending up or slowing down? |
| Focus score | Unique repos touched per day. 1 = deep work, 8 = scattered |
| Weekend vs weekday | Split activity by work days vs weekends |
| File hotspots | Most-churned files across all repos (find your messiest code) |

**What changes:**
- `analytics.py` — new compute functions: `compute_language_evolution()`, `compute_velocity()`, `compute_focus_score()`, `compute_weekday_split()`, `compute_hotspots()`
- `tui.py` — new panels for each insight
- `cli.py` — add to `--summary` and `--json` output

---

## v0.4 — Achievements & Gamification

**Goal:** Keep devs coming back. Make coding stats feel like unlocking badges.

| Achievement | Condition |
|-------------|-----------|
| Night Owl | 50%+ commits after midnight |
| Early Bird | 50%+ commits before 9am |
| Weekend Warrior | 40%+ commits on Sat/Sun |
| Polyglot | 5+ languages with 100+ lines each |
| Century | 100-day streak |
| Marathon | 365-day streak |
| Prolific | 1000+ total commits |
| Monorepo Monster | Single repo with 500+ commits |
| Clean Freak | All repos have health score 80+ |
| Diversified | 10+ active repos |

**What changes:**
- New module: `achievements.py` — check conditions against analytics data
- `tui.py` — achievements panel with badge icons
- `cli.py` — show unlocked achievements in `--summary` and `--json`

---

## v0.5 — Wrapped & Sharing

**Goal:** Shareable output. The viral feature.

| Feature | Description |
|---------|-------------|
| `--wrapped` | Generate a Spotify Wrapped-style image card (PNG/SVG) |
| `--report` | Export a clean markdown report (Notion, blog, performance reviews) |
| Dynamic badge | SVG badge for GitHub profile READMEs (streak count, top language) |

**Wrapped card includes:**
- Year in review: total commits, repos, languages
- Top language, top repo
- Current & longest streak
- Busiest hour & day
- Achievements unlocked
- Styled with huntd branding

**Tech:** Pillow for PNG generation or Rich export-to-SVG.

---

## v0.6 — Live Mode

**Goal:** Real-time dashboard that updates as you code.

| Feature | Description |
|---------|-------------|
| `--watch` | Auto-refresh TUI dashboard on file system changes |
| Refresh interval | Configurable poll interval (default: 30s) |
| Git hook | Optional post-commit hook that triggers refresh |

**Tech:** `watchdog` library for filesystem events, or simple polling loop.

---

## v0.7 — VS Code Extension

**Goal:** huntd inside the editor.

| Surface | What it shows |
|---------|--------------|
| Status bar | Streak counter — always visible (e.g. "14d streak") |
| Sidebar | Tree view: streaks, repos, languages, activity |
| Webview panel | Full dashboard with heatmap, charts, repo table |
| Commands | `Huntd: Open Dashboard`, `Huntd: Refresh Analytics` |

**Tech:** TypeScript, VS Code Extension API, shells out to `huntd --json`.

**Prereq:** Add heatmap matrix to `--json` output (one-line change in `cli.py`).

---

## Build Order

```
v0.2 (filters)  →  v0.3 (insights)  →  v0.4 (achievements)
                                              ↓
v0.7 (vscode)  ←  v0.6 (watch)  ←  v0.5 (wrapped)
```

Each version builds on the previous. Filters first (quick win), then deeper analytics, then the fun stuff.
