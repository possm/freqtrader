# BRIEFING — 2026-09-07T13:32:00Z

## Mission
Analyze architecture, Docker setups, and Freqtrade configurations across 4 repos to design a consolidated monorepo Docker and user_data architecture.

## 🔒 My Identity
- Archetype: explorer
- Roles: Architecture, Docker & Freqtrade Environment Specialist Explorer
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/
- Original parent: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Milestone: Monorepo Architecture & Docker Consolidation Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Write only inside working directory /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/
- Verification command: docker compose config must pass without syntax/validation errors
- Produce survey_arch_report.md and handoff.md

## Current Parent
- Conversation ID: 12ebc45b-1687-46e5-a9f5-8ac053b58478
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `docker-compose.yml` in all 4 repositories + VPS inspection (`docker ps`, live directories)
  - `freqtrader-dash` codebase (`nginx.conf`, `Dockerfile`, `app.jsx`, `api.jsx`, `views.jsx`, `components.jsx`)
  - `user_data` structures across `freqtrade-breakout`, `freqtrade-grid`, and `freqtrade-trend`
  - All JSON configs across all repos (root and `user_data/`)
  - All strategy files in `user_data/strategies/` across all repos
- **Key findings**:
  - `freqtrader-dash`: Pure client-side React 18 / Babel-standalone + Nginx reverse proxy. Does NOT connect to SQLite or WebSockets; polls REST `/api/v1/*` every 5s. Proxies `/api/` to port 8080 by default; connects directly via browser fetch + CORS for other bot ports (8081, 8082).
  - Port & IP bindings: `192.168.2.4` is WireGuard `wg0` interface on VPS `vps-matthijs-trader`. Port allocation: 80 (Dash), 8080 (Trend live), 8081 (Grid), 8082 (Breakout academic dryrun), 8083 (Breakout daily macro).
  - Strategy unification: 174 strategies total (StepGrid.py from grid + 173 from breakout). Breakout strategies are a strict superset of trend. No naming conflicts.
  - Config unification: Root configs (`config_trend_hopt.json`, `config_academic_dryrun.json`, etc.) can be consolidated directly into `user_data/`. `freqtrade-grid/user_data/config.json` must be renamed to `user_data/config_grid.json` to prevent conflict with root `config.json`.
  - Database collision resolved: Grid used generic `tradesv3.sqlite` which collided with Wolf legacy `tradesv3.sqlite`. Isolated to `tradesv3_grid.sqlite`.
  - Verified Docker Compose: Created test-compose.yml, validated with `docker compose config` passing cleanly.
- **Unexplored areas**: None. Complete architectural survey finished.

## Key Decisions Made
- Consolidate all configs into shared `user_data/` so no individual root file mounts are needed in compose.
- Retain dedicated database URLs and log files per bot service to ensure total isolation.
- Unify environment credentials in a single `.env` at monorepo root.

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/DISPATCH.md — Incoming task dispatch
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/progress.md — Liveness heartbeat and progress tracking
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/BRIEFING.md — Situational awareness
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/test-compose.yml — Validated compose draft
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/survey_arch_report.md — Architectural survey and consolidation design report
- /Users/matthijsdrenth/IdeaProjects/freqtrade-breakout/.agents/survey_monorepo_explorer_2/handoff.md — 5-component handoff report
