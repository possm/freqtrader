# Project: Academic Altcoin Strategy for Freqtrade

## Architecture
- Module/package boundaries, data flow, shared interfaces:
  - Strategy Module: `user_data/strategies/WolfBreakout_PVB.py` (inherits `IStrategy`, implements Parkinson Volatility Estimator, Donchian Channel, Keltner Channel, ATR Chandelier stop, BTC macro trend filter).
  - Slippage & Fee Module: `user_data/strategies/kraken_slippage.py` (`KrakenSlippageMixin`) & explicit `--fee 0.0026`.
  - Config Module: `config_academic_dryrun.json` (dry-run mode, 18 Kraken EUR pairs, port 8082, dedicated DB `tradesv3_academic_dryrun.sqlite` and logfile `freqtrade_academic_dryrun.log`).
  - Infrastructure: `docker-compose.yml` (service `freqtrade-academic-dryrun` on port 8082, live bot on 8080 untouched).
  - VPS Execution: `ssh vps-matthijs-trader "cd freqtrade-wolf && docker compose ..."` and `rsync` per GEMINI.md.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Git Feature Branch | Dedicated branch `feat/academic-altcoin-strategy` | M1 | User Rules |
| 2 | Parkinson Volatility Estimator | Continuous range variance estimator (Parkinson 1980) | M1 | Academic Research |
| 3 | Donchian & Keltner Dual Breakout | 20-period Donchian + Keltner ATR expansion channel | M1 | Academic Research |
| 4 | BTC Macro Regime Gate | BTC/EUR (or BTC/USDT) > EMA200 cross-asset filter | M1 | Academic Research |
| 5 | Asymmetric Risk Management | Hard stop-loss (-4.5%), Chandelier ATR trailing stop, ROI table | M1 | Academic Research |
| 6 | Unit Test Suite & Indicator Validation | Static syntax validation and unit tests for indicator calculations | M1 | SWE Standards |
| 7 | Multi-Cycle Dataset & Fee Configuration | 1h timeframe, timerange 20210101- / 20240101-, explicit `--fee 0.0026` | M2 | Survey Explorer 2 |
| 8 | Hyperopt Optimization on VPS | Hyperopt execution targeting stoploss, roi, trailing with Sharpe/Profit loss | M2 | R2 Requirement |
| 9 | Fee-Adjusted Backtest Verification | Backtest verifying >10% net profit after Kraken taker fees | M2 | Acceptance Criteria |
| 10 | Risk Management & Code Audit | Independent audit for fatal bugs, lookahead bias, memory leaks, live bot isolation | M3 | R3 Requirement |
| 11 | E2E Testing Suite | Verification of dry-run container config, sqlite DB, API port 8082, entry/exit logic | M3 | Dual Track |
| 12 | VPS File Synchronization | Safe rsync to `vps-matthijs-trader:~/freqtrade-wolf/` excluding data/logs/sqlite | M4 | GEMINI.md |
| 13 | Docker Compose Dry-Run Service | Container `freqtrade-academic-dryrun` configured on port 8082 | M4 | Survey Explorer 2 |
| 14 | VPS Container Deployment & Verification | Start dry-run container, verify >= 3 heartbeats with state='RUNNING' | M4 | Acceptance Criteria |
| 15 | Academic Strategy Markdown Report | Comprehensive documentation explaining theory, timeframe, and fee hurdle | M5 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Strategy Implementation & Local Testing | Branch creation, `WolfBreakout_PVB.py` strategy implementation, unit tests | Survey | DONE |
| 2 | Data Prep & Hyperopt on VPS | Multi-year Binance/Kraken dataset tuning, hyperopt on VPS, >10% net profit verification | M1 | DONE |
| 3 | Risk Verification & Code Audit | Independent review, challenger stress tests, forensic integrity audit | M2 | DONE |
| 4 | VPS Dry Run Deployment & Heartbeats | Sync to VPS, start container on port 8082, verify >= 3 heartbeats | M3 | DONE |
| 5 | Documentation & Final Reporting | Comprehensive markdown report on theory, timeframe justification, and results | M4 | DONE |

## Interface Contracts
### Strategy ↔ Freqtrade Engine
- Entry: `populate_entry_trend(dataframe, metadata)` sets `enter_long = 1` when Donchian Upper + Keltner Upper + PVR > 1.13 + Volume + BTC EMA200 are satisfied.
- Exit: `populate_exit_trend(dataframe, metadata)` sets `exit_long = 1` when candle closes below Donchian Mid.
- Stoploss: `stoploss = -0.34`, `trailing_stop = True`, `trailing_stop_positive = 0.248`, `trailing_stop_positive_offset = 0.316`.
- Timeframe: `timeframe = '1h'`. Informative pairs: `('BTC/EUR', '1h')` or `('BTC/USDT', '1h')`.

### Dry-Run Service ↔ VPS Environment
- Container name: `freqtrade-wolf-academic-dryrun`
- Compose service: `freqtrade-academic-dryrun`
- Port mapping: `192.168.2.4:8082:8080`
- Config file: `config_academic_dryrun.json` (`"dry_run": true`, `"stake_currency": "EUR"`, `"stake_amount": 75`)
- DB path: `/freqtrade/user_data/tradesv3_academic_dryrun.sqlite`
- Log path: `/freqtrade/user_data/logs/freqtrade_academic_dryrun.log`

## Code Layout
- `user_data/strategies/WolfBreakout_PVB.py` — New academic strategy
- `tests/test_wolfbreakout_pvb.py` — Unit tests for strategy indicators and edge cases
- `config_academic_dryrun.json` — Dedicated dry-run configuration for port 8082
- `docker-compose.yml` — Compose file containing `freqtrade-academic-dryrun` service
- `reports/ACADEMIC_STRATEGY_REPORT.md` — Final documentation report
