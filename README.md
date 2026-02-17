<div align="center">

# huntd

**Your coding fingerprint — local git analytics dashboard for all your repos.**

[![PyPI](https://img.shields.io/pypi/v/huntd?style=flat-square&color=blue)](https://pypi.org/project/huntd/)
[![Downloads](https://img.shields.io/pypi/dm/huntd?style=flat-square&color=green)](https://pypi.org/project/huntd/)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

Scan every git repo on your machine. Get streaks, heatmaps, language trends, project health scores, and more — all in one interactive terminal dashboard.

> WakaTime costs $9/mo. GitHub Wrapped is once a year. **huntd** is free, local, instant, and sees everything.

## Install

```bash
pip install huntd
```

## Quick Start

```bash
# Interactive TUI dashboard
huntd ~/code

# One-shot summary (no TUI)
huntd ~/code --summary

# JSON output (pipe to jq, scripts, etc.)
huntd ~/code --json

# Scan current directory
huntd
```

## What You Get

```
╭────────────────────── huntd — your coding fingerprint ───────────────────────╮
│   Repos: 14    Commits: 4,847    Languages: 8                                │
│   Current streak: 14 days    Longest: 31 days                                │
│   Most active: Tuesdays at 10pm    Avg: 3.2/day                              │
╰──────────────────────────────────────────────────────────────────────────────╯

                                   Top Repos
┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Repo         ┃ Commits ┃ Language  ┃        Health ┃  +Lines ┃ -Lines ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ cloud-dash   │     847 │ Python    │ █████████░ 95 │ +15,847 │ -1,204 │
│ pulse-mobile │     623 │ Go        │ ████████░░ 85 │  +8,619 │   -820 │
│ data-engine  │     412 │ Rust      │ ████████░░ 80 │  +6,074 │   -503 │
│ api-gateway  │     203 │ TypeScript│ ███████░░░ 70 │  +2,876 │   -118 │
└──────────────┴─────────┴───────────┴───────────────┴─────────┴────────┘

                              Languages
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Language   ┃ Lines Changed ┃                           ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Python     │        15,823 │ ██████████████░░░░░░  62% │
│ Go         │         5,628 │ █████░░░░░░░░░░░░░░░  22% │
│ Rust       │         2,519 │ ███░░░░░░░░░░░░░░░░░   9% │
│ TypeScript │           827 │ █░░░░░░░░░░░░░░░░░░░   3% │
└────────────┴───────────────┴───────────────────────────┘
```

## Features

| Feature | Description |
|---------|-------------|
| **Multi-repo scanning** | Recursively finds every git repo under a directory |
| **Coding streaks** | Current and longest streak computed from local commits |
| **Contribution heatmap** | GitHub-style activity grid across all repos (TUI mode) |
| **Language breakdown** | Lines changed per language with trend bars |
| **Project health scores** | 0-100 score based on recency, README, branches, cleanliness |
| **Activity patterns** | Busiest day, busiest hour, average commits per day |
| **Top repos ranking** | Sorted by commit count with language and health |
| **Interactive TUI** | Navigate panels with keyboard (Textual-powered) |
| **Summary mode** | `--summary` for a quick Rich-formatted printout |
| **JSON export** | `--json` for scripting and pipelines |

## How It Works

1. **Scan** — Recursively finds all `.git` directories under the target path
2. **Extract** — Runs optimized `git log` commands in parallel (8 threads) across all repos
3. **Analyze** — Computes streaks, heatmaps, language stats, health scores, and activity patterns
4. **Display** — Renders an interactive dashboard or summary

All data comes from local git history. No API keys. No accounts. No cloud. No cost.

## Output Modes

```bash
# Interactive dashboard (default)
huntd ~/code

# Static summary — great for screenshots
huntd ~/code --summary

# JSON — pipe to jq, save to file, feed to scripts
huntd ~/code --json
huntd ~/code --json | jq '.repos[] | select(.commits > 100)'

# Version
huntd --version
```

## Health Score

Each repo gets a 0-100 health score based on:

| Factor | Points | Criteria |
|--------|--------|----------|
| Commit recency | 0-40 | Last commit within 7d (40), 30d (30), 90d (20), 1yr (10) |
| Total commits | 0-20 | 100+ (20), 50+ (15), 10+ (10), 1+ (5) |
| Has README | 0-15 | README file present in repo root |
| Branch hygiene | 0-15 | 1-5 branches (15), 6-10 (10), 11+ (5) |
| Clean tree | 0-10 | No uncommitted changes |

## Why Not X?

| Tool | Limitation |
|------|-----------|
| **WakaTime** | Cloud-only, $9/mo, tracks editor time not git history |
| **GitHub Wrapped** | Annual only, GitHub repos only, no local/private repos |
| **onefetch** | Single repo snapshot, not interactive |
| **git-quick-stats** | Single repo, text dump, no dashboard |
| **tokei / scc** | Line counting only, no history or trends |

**huntd** is the first tool to combine multi-repo scanning + streaks + heatmaps + language trends + health scores in one interactive dashboard. Free. Local. Instant.

## Development

```bash
git clone https://github.com/TRINITY-21/huntd.git
cd huntd
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Support

If this project is useful to you, consider supporting it.

<a href="https://buymeacoffee.com/trinity_21" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40"></a>

## License

MIT
