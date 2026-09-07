# BRIEFING — 2026-09-04T15:26:50Z

## Mission
Survey VPS infrastructure on `vps-matthijs-trader`: inspect ~/freqtrade-wolf/, docker-compose, containers, data, configs, fees, hyperopt, and dry-run execution.

## 🔒 My Identity
- Archetype: explorer
- Roles: VPS Infrastructure Explorer
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2
- Original parent: 90978f93-4bda-450d-89cf-eb27ba874681
- Milestone: Survey Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify live containers/strategies
- Use SSH to query `vps-matthijs-trader`
- Do not push to remote git
- Keep progress and handoff in `.agents/survey_explorer_2`

## Current Parent
- Conversation ID: 90978f93-4bda-450d-89cf-eb27ba874681
- Updated: 2026-09-04T15:26:50Z

## Investigation State
- **Explored paths**: `vps-matthijs-trader:~/freqtrade-wolf/`, `docker-compose.yml`, `user_data/data/` (kraken & binance), `user_data/scripts/`, `config*.json`, `.env`, running containers, open ports, ccxt fee rates.
- **Key findings**:
  - Live production bot `freqtrade-wolf-hopt-live` is active on port 8080 (`dry_run: false`). Ports 8081 and 8082 are available.
  - Port 8082 should be used for dry-run simulation (`freqtrade-academic-dryrun`).
  - Binance data in `user_data/data/binance/` spans 5.4 years (2021-2026, 4h and 1h) and is ideal for robust multi-cycle hyperopt/backtests.
  - Kraken fee must be explicitly enforced via `--fee 0.0026` (or `0.0040`) when running hyperopt/backtests on Binance data.
  - VPS has 2 vCPUs and 3.8 GiB RAM; Hyperopt should use `-j 2`.
- **Unexplored areas**: None within the VPS survey scope.

## Key Decisions Made
- Confirmed port 8082 and `tradesv3_academic_dryrun.sqlite` as the isolated target for dry-run deployment.
- Identified mandatory `--fee 0.0026` requirement for all hyperopt/backtest runs on Binance data to meet R2.
- Verified Kraken exchange does not support 2h candles; strategy must use 1h (or 4h/15m).

## Artifact Index
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/handoff.md` — Comprehensive VPS infrastructure survey report.
- `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_2/progress.md` — Execution progress log.
