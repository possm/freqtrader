# Project: Freqtrade Monorepo Consolidation

## Mission
Consolidate four separate repositories (`freqtrade-breakout`, `freqtrade-grid`, `freqtrade-trend`, `freqtrader-dash`) into a single, unified monorepo at `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo` with full git history preservation, single root `user_data/`, central `docker-compose.yml`, aggressive cleanup of obsolete files, and strict preservation of AI instructions and context.

## Architecture
- **Root Directory**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`
- **Central Docker Compose**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo/docker-compose.yml`
  - `freqtrader-dash`: Nginx frontend on port 80
  - `freqtrade-hopt-live`: Trend live trading bot on port 8080 (`WolfTrend_1h_Candidate`)
  - `freqtrade-grid`: Grid trading bot on port 8081 (`StepGrid`)
  - `freqtrade-academic-dryrun`: Breakout academic dry-run bot on port 8082 (`WolfBreakout_PVB`)
  - `freqtrade-breakout-daily`: Breakout daily macro bot on port 8083 (`WolfBreakout_Daily`)
- **Shared Freqtrade Data**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo/user_data/`
  - `user_data/strategies/`: 260 unified trading strategies (including StepGrid, Wolf strategies)
  - `user_data/`: Central configurations (`config.json`, `config_grid.json`, `config_academic_dryrun.json`, `config_breakout_daily.json`, `config_grid_backtest.json`, etc.)
  - `user_data/logs/`: Bot-specific log files
- **Web Dashboard**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo/dashboard/`
  - In-browser React 18 / Babel application with Nginx proxy
- **AI Context & Rules**:
  - `GEMINI.md`: Unified user rules (Global Git Branching Rule, multi-service VPS sync)
  - `.cursorrules`: Root IDE assistant rules
  - `.agents/`: Full historical agent workspaces and documentation
  - `.agents/rules/project-specifics.md`: Dashboard and bot operational rules

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | History-Preserving Migration | Multi-remote fetch & unrelated history merge of 4 repos with 100% SHA preservation | M1 | Survey 1 |
| 2 | Uncommitted Assets Preservation | Retain updated StepGrid.py, tuned .json params, untracked strategies | M1 | Survey 1 |
| 3 | Git Branching Setup | Establish main branch and create feature branch `feat/monorepo-consolidation` | M1 | Survey 1 |
| 4 | Central Docker Compose | Single compose file defining 5 services with deconflicted ports (80, 8080, 8081, 8082, 8083) | M2 | Survey 2 |
| 5 | Shared user_data Directory | Single root `user_data` containing all 174+ strategies and distinct bot configs | M2 | Survey 2 |
| 6 | Service DB & Log Partitioning | Isolated sqlite db URLs and log files per bot | M2 | Survey 2 |
| 7 | Obsolete Artifact Cleanup | Remove ~2.02 GB of hyperopt dumps, backtest zips, coverdir, node_modules, stray txts | M3 | Survey 3 |
| 8 | AI Context & Rules Consolidation | Master `.agents/`, unified `GEMINI.md`, root `.cursorrules`, `project-specifics.md` | M3 | Survey 3 |
| 9 | Multi-Tier Verification & Audit | Validate `git log --all`, `docker compose config`, `find` AI rules, and Forensic Audit | M4 | Survey 1-3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | M1: History-Preserving Migration | Create monorepo at `/Users/matthijsdrenth/IdeaProjects/freqtrade-monorepo`, import 4 repositories via multi-remote fetch and preparation branches, merge unrelated histories preserving all 69 commits, preserve uncommitted assets, initialize git branching | None | DONE |
| 2 | M2: Architectural Consolidation | Construct central `docker-compose.yml`, consolidate shared `user_data/` directory with strategies and deconflicted configs, validate via `docker compose config` | M1 | DONE |
| 3 | M3: Cleanup & AI Context Preservation | Prune all obsolete hyperopt, backtest, cache, and coverage files (~2.02 GB); consolidate master `.agents/`, unified `GEMINI.md`, root `.cursorrules` | M2 | IN_PROGRESS |
| 4 | M4: Final Verification & Forensic Audit | Run comprehensive verification suite (`git log --all`, `docker compose config`, AI files check, cleanliness check), independent Reviewers, Challengers, and Forensic Auditor | M3 | PLANNED |

## Interface Contracts
### Dashboard ↔ Freqtrade Bots
- Transport: HTTP REST API via browser fetch (polling every 5s)
- Auth: HTTP Basic / JWT Bearer token
- Ports:
  - 80: Nginx dashboard UI
  - 8080: Trend Live API (proxied via `/api/`)
  - 8081: Grid API
  - 8082: Academic Dry-Run API
  - 8083: Breakout Daily API
- CORS: All bots configured with `CORS_origins: ["http://192.168.2.4", "http://192.168.2.4:80", "http://localhost", "http://127.0.0.1"]`

### Freqtrade Services ↔ Shared user_data
- Single Volume Mount: `./user_data:/freqtrade/user_data`
- Strategies: `/freqtrade/user_data/strategies/`
- Databases:
  - Live: `sqlite:////freqtrade/user_data/tradesv3_hopt_live.sqlite`
  - Grid: `sqlite:////freqtrade/user_data/tradesv3_grid.sqlite`
  - Dry-run: `sqlite:////freqtrade/user_data/tradesv3_academic_dryrun.sqlite`
  - Daily: `sqlite:////freqtrade/user_data/tradesv3_breakout_daily.sqlite`
- Logs: `/freqtrade/user_data/logs/freqtrade_<bot_name>.log`
