# BRIEFING — 2026-09-04T19:12:36Z

## Mission
Investigate VPS environment (`vps-matthijs-trader`), available market data, timeframe options, and Hyperopt optimization infrastructure on the VPS to prepare for achieving >=10% net monthly return after fees.

## 🔒 My Identity
- Archetype: explorer
- Roles: Data Scientist, VPS Environment Explorer
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_datascientist
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Survey & Preparation for >=10% monthly return

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Inspection only. Do NOT overwrite existing live databases or configs.
- Follow GEMINI.md and Git rules.

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: not yet

## Investigation State
- **Explored paths**:
  - VPS specs: 2 vCPUs, 3.8 GiB RAM (2.2 GiB free), 58 GB SSD (40 GB free), load average ~0.20.
  - Active containers: `freqtrade-wolf-academic-dryrun` (port 8082), `freqtrade-wolf-hopt-live` (port 8080), `freqtrader-dash` (port 80), `code-server-agy` (port 8443).
  - Software: Freqtrade 2026.4, Python 3.14.3, CCXT 4.5.50 on Linux 6.8.0-136-generic.
  - Kraken Data: 18 liquid EUR pairs in `.feather` format (15m, 1h, 4h from March–May 2026 / 4h to August 2026). Kraken REST API rejects historical klines download (`Historic klines not available for Kraken`).
  - Binance Data: 17 matching liquid pairs on USDT in `.feather` spanning 5.4 years (2021-01-01 to 2026-05-22 on 5m, 15m, 1h, 4h).
  - Loss Functions: Inspected Python source code for `ProfitDrawDownHyperOptLoss`, `SortinoHyperOptLossDaily`, `SharpeHyperOptLossDaily`, `CalmarHyperOptLoss`, `OnlyProfitHyperOptLoss`.
  - Hyperopt Engine: Optuna with NSGAIIISampler. Discovered Python 3.14 `_pickle.PicklingError` with `-j 2` multiprocessing; `-j 1` runs flawlessly without pickling overhead (2 epochs / second).
  - Fee Accounting: `--fee 0.0026` successfully applied and verified in backtesting/hyperopt.
- **Key findings**:
  - For >10%/month target, 1h timeframe is optimal (30-60 trades/month; fee drag ~1.7%/month; average win 4-12%).
  - `ProfitDrawDownHyperOptLoss` is mathematically superior for aggressive targets where drawdown tolerance is relaxed by Risk Manager.
  - Python 3.14 joblib issue requires `-j 1` for Hyperopt execution on VPS.
- **Unexplored areas**: None. All questions from mission fully investigated.

## Key Decisions Made
- Recommend 1h timeframe for strategy implementation to balance trade frequency with Kraken fee drag.
- Recommend `ProfitDrawDownHyperOptLoss` (or `SortinoHyperOptLossDaily`) over `SharpeHyperOptLoss` to avoid penalizing positive volatility spikes.
- Recommend `-j 1` on Hyperopt commands on VPS to prevent Python 3.14 serialization crash.
- Enforce `--fee 0.0026` and `--disable-param-export` during hyperopt exploration.

## Artifact Index
- DISPATCH.md — Initial dispatch instructions
- progress.md — Liveness & task execution tracker
- handoff.md — Comprehensive 5-component handoff report
