# BRIEFING — 2026-09-04T15:25:30Z

## Mission
Investigate local repository structure, git status, existing strategies, configs, docker setup, dependencies, and conventions for Freqtrade altcoin strategy development.

## 🔒 My Identity
- Archetype: explorer
- Roles: Codebase & Repo Explorer, Investigator, Synthesizer
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_1
- Original parent: 90978f93-4bda-450d-89cf-eb27ba874681
- Milestone: Repo & Codebase Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT commit or push to git
- All code changes must occur on a dedicated git branch (e.g. feat/academic-altcoin-strategy), never directly on main/master
- Never push autonomously to any remote without explicit user permission
- Write only to our own directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_1

## Current Parent
- Conversation ID: 90978f93-4bda-450d-89cf-eb27ba874681
- Updated: 2026-09-04T15:22:35Z

## Investigation State
- **Explored paths**:
  - Git status, branches, logs, remotes in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend`
  - Repo layout: root configs, scripts, docker-compose.yml, .env, GEMINI.md
  - Strategies: `user_data/strategies/` (250 files; WolfTrend, WolfQuantEdge, WolfMR, kraken_slippage)
  - Configs: `config_trend_hopt.json` (live), `config_kraken_dryrun.json` (dry run), `config_backtest.json`, `user_data/config_binance.json`
  - Data: local Binance feather data (17 altcoins + BTC, 15m/1h/2h/4h), VPS Kraken EUR data
  - VPS: `vps-matthijs-trader:~/freqtrade-wolf`, live container `freqtrade-wolf-hopt-live` running and healthy
- **Key findings**:
  - Current git branch is `feature/early-entry-2h-strategy`. Recommended new branch: `feat/academic-altcoin-strategy`.
  - Kraken DOES NOT natively support 2h candles. Strategies must use supported timeframes (e.g. 1h, 15m, 4h).
  - Production live bot uses `WolfTrend_1h_Candidate` on port 8080 with 15 Kraken EUR pairs.
  - Dry-run container setup is ready in `docker-compose.yml` (`freqtrade-qe-sim` or new dry-run service on port 8082).
  - Slippage and fee modeling already exists via `kraken_slippage.py` (KrakenSlippageMixin) and `--fee 0.0026`.
- **Unexplored areas**: None for codebase survey.

## Key Decisions Made
- Documented full repository architecture, conventions, and operational workflows for Quant, Data Scientist, and Risk Manager.

## Artifact Index
- DISPATCH.md — Dispatch instructions and tasks
- BRIEFING.md — Working memory and status index
- progress.md — Heartbeat and task checklist
- handoff.md — Comprehensive handoff report
