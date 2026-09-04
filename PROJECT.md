# Project: Aggressive Crypto Strategy for Freqtrade (>=10% Net Profit/Month)

## Architecture
- Module/package boundaries, data flow, shared interfaces:
  - Strategy Module: `user_data/strategies/WolfBreakout_HVRSPB.py` (High-Velocity Relative-Strength Parkinson Breakout).
    - Parkinson Volatility Ratio (PVR > threshold) for volatility expansion detection.
    - Relative Strength vs. BTC (24h excess return > 2.5%) for market leadership selection.
    - Donchian & Keltner dynamic breakout triggers with ADX / volume confirmation.
    - Asymmetric Payoff Engine: fast invalidation (-1.5% to -2.0% within 4-6h) and aggressive trailing profit runner (+3.5% breakeven lock, trailing high gains).
    - Maker fee priority (Limit orders) and explicit fee deduction (`--fee 0.0026`).
  - Risk & Capital Allocation Module:
    - 1h timeframe on liquid Kraken pairs.
    - `max_open_trades = 4`, 25% stake allocation per trade (`stake_amount = "unlimited"` or dynamic $W / 4$) to achieve 100% active capital deployment during market trends.
    - Drawdown governance: Risk Manager approved drawdown ceiling of 30.0% - 35.0% for spot crypto.
    - Circuit Breakers: MaxDrawdown (30% / 48h halt) and StoplossGuard (4 stops / 24h halt).
  - Infrastructure & VPS Execution:
    - Execution on `vps-matthijs-trader`.
    - Hyperopt using `ProfitDrawDownHyperOptLoss` with `-j 1` on Binance/Kraken 1h data (2024 to present) with `--fee 0.0026`.
    - Dedicated backtest verification verifying >=10% monthly net profit.
    - Zero disruption to live production bot on port 8080.
  - Reporting Module:
    - `reports/10PERCENT_MONTH_REPORT.md` justifying theory, timeframe, fee hurdle, and Risk Manager drawdown acceptance.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Git Feature Branch | Dedicated branch `feat/aggressive-10pct-monthly-strategy` | M1 | User Rules |
| 2 | Relative Strength vs BTC Filter | 24h excess return vs BTC (>2.5%) to select momentum leaders | M1 | Quant Survey |
| 3 | Parkinson Volatility Expansion | Continuous range variance estimator (PVR) for volatility breakout | M1 | Quant Survey |
| 4 | Donchian/Keltner Breakout & Momentum | Channel breakout with volume and ADX momentum confirmation | M1 | Quant Survey |
| 5 | Asymmetric Payoff Engine | Fast invalidation exit + two-tier trailing runner (+3.5% lock, trailing runner) | M1 | Quant Survey |
| 6 | Unit Test Suite | Comprehensive unit tests for indicators, RS calculation, and edge cases | M1 | SWE Standards |
| 7 | VPS Hyperopt Infrastructure | Hyperopt script using `ProfitDrawDownHyperOptLoss`, `-j 1`, `--fee 0.0026` | M2 | Data Scientist Survey |
| 8 | Parameter Optimization on VPS | Optimize buy, roi, stoploss, and trailing spaces over 2024 historical data | M2 | Data Scientist Survey |
| 9 | Fee-Adjusted Backtest Verification | Verify >=10% net profit per month after Kraken fees (0.26% taker) | M2 | Acceptance Criteria |
| 10 | Risk Management & Drawdown Audit | Audit risk parameters against the 30-35% drawdown mandate | M3 | Risk Manager Survey |
| 11 | Challenger & Adversarial Stress Tests | Edge-case simulation, flash crash test, extreme fee sensitivity | M3 | SWE Standards |
| 12 | Forensic Integrity Audit | Independent check for lookahead bias, dummy facades, and fee bypassing | M3 | Audit Standards |
| 13 | Risk Manager Markdown Report | `reports/10PERCENT_MONTH_REPORT.md` explaining theory and risk justification | M4 | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Strategy Implementation & Local Unit Tests | Implement `WolfBreakout_HVRSPB.py` and unit tests in `tests/test_wolfbreakout_hvrspb.py` | Survey | IN_PROGRESS |
| 2 | VPS Hyperopt & Fee-Adjusted Backtest (>10%/mo) | Sync to VPS, run hyperopt with `-j 1` and `--fee 0.0026`, backtest verifying >=10%/month net profit | M1 | PLANNED |
| 3 | Risk Governance, Stress Tests & Forensic Audit | Reviewer check, Challenger stress tests, Forensic Auditor integrity check | M2 | PLANNED |
| 4 | Risk Manager Report & Documentation | Complete `reports/10PERCENT_MONTH_REPORT.md`, verify zero errors, commit cleanly | M3 | PLANNED |

## Interface Contracts
### Strategy ↔ Freqtrade Engine
- Class Name: `WolfBreakout_HVRSPB` in `user_data/strategies/WolfBreakout_HVRSPB.py`
- Base Class: `IStrategy`
- Timeframe: `1h`
- Informative Pairs: `('BTC/EUR', '1h')` or `('BTC/USDT', '1h')` for Relative Strength benchmarking.
- Entry Logic: Long entry when:
  1. Altcoin 24h return exceeds BTC 24h return by threshold (`rs_excess_threshold`, default > 0.025).
  2. Parkinson Volatility Ratio > threshold (`pvr_threshold`, default > 1.15).
  3. Close > Donchian Upper (`donchian_upper`) or Keltner Upper.
  4. Volume > Volume SMA20 * `volume_factor` (default > 1.2).
- Exit Logic:
  1. Time/Volatility invalidation: Close < Entry EMA or Donchian Mid after 4 candles.
  2. Asymmetric trailing stop: Breakeven lock at +3.5%, trailing stop for runner trends.
  3. Hard stoploss: -0.06 (-6.0%).
- Order Types: Limit orders (`use_custom_stoploss = False` or dynamic custom stoploss, limit entry and exit where possible for maker fee savings).

### Code Layout
- `user_data/strategies/WolfBreakout_HVRSPB.py` — High-Velocity Relative-Strength Parkinson Breakout strategy
- `tests/test_wolfbreakout_hvrspb.py` — Unit test suite for strategy logic, indicators, and edge cases
- `reports/10PERCENT_MONTH_REPORT.md` — Comprehensive Risk Manager and Quant rationale report
