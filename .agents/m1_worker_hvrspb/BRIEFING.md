# BRIEFING — 2026-09-04T19:29:00Z

## Mission
Implement `WolfBreakout_HVRSPB.py` strategy and its comprehensive unit test suite `tests/test_wolfbreakout_hvrspb.py` for Milestone 1.

## 🔒 My Identity
- Archetype: Strategy Implementation Worker
- Roles: implementer, qa, specialist
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_hvrspb
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Milestone 1 - High-Volatility Breakout Strategy (WolfBreakout_HVRSPB)

## 🔒 Key Constraints
- Exclusive write access: `user_data/strategies/WolfBreakout_HVRSPB.py`, `tests/test_wolfbreakout_hvrspb.py`, and `.agents/m1_worker_hvrspb/`.
- No cheats, no dummy implementations. Real indicators and genuine math.
- Branch `feat/aggressive-10pct-monthly-strategy`, do not commit to main/master.
- Never git push without user authorization.
- Limit orders for maker fee capture (0.16% vs 0.26%).
- Robust handling of missing informative pair data.

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: 2026-09-04T19:29:00Z

## Task Summary
- **What to build**: `WolfBreakout_HVRSPB` strategy with Parkinson Volatility Ratio, Relative Strength vs BTC, Donchian + Keltner channels, asymmetric exit/trailing stop, hyperopt parameters, maker limit orders, and comprehensive pytest test suite.
- **Success criteria**: 100% pytest pass, clean python import, complete handoff report.
- **Interface contracts**: `freqtrade.strategy.IStrategy`, `PROJECT.md`
- **Code layout**: Strategy in `user_data/strategies/`, tests in `tests/`.

## Key Decisions Made
- Implemented Parkinson Volatility Ratio (PVR): continuous high-low range estimator over 20 periods vs 20-period EMA of Parkinson volatility. Safe clipping on low/high and +1e-9 epsilon prevent any zero-division errors.
- Implemented Relative Strength (RS vs BTC): 24h rolling return difference ($R_{asset} - R_{BTC}$). When BTC informative pair is absent or empty, gracefully falls back to benchmark-neutral ($R_{BTC} = 0.0$).
- Implemented Dual Breakout: Donchian 20-period high (strictly shifted by 1 candle to prevent lookahead) and Keltner Channel (20 EMA + 1.5 ATR).
- Asymmetric risk engine: Fast invalidation in populate_exit_trend (Close < Donchian Mid) and custom_exit after 4 candles; two-tier asymmetric trailing stop in custom_stoploss (+3.5% profit locks in +0.8% breakeven stop, +8.0% profit activates trailing runner with 4.0% distance).
- Strict Limit order types for maker fee capture (0.16% maker vs 0.26% taker).
- Verified full compatibility with `freqtrade list-strategies` (shows OK, Hyperoptable: Yes, 6 buy, 2 sell, 4 trailing, 1 stoploss).

## Artifact Index
- `DISPATCH.md` — Assignment instructions
- `BRIEFING.md` — Working state and identity
- `progress.md` — Execution status
- `handoff.md` — Complete handoff report
- `user_data/strategies/WolfBreakout_HVRSPB.py` — Production strategy implementation
- `tests/test_wolfbreakout_hvrspb.py` — Comprehensive unit test suite (36 tests)

## Change Tracker
- **Files modified**:
  - `user_data/strategies/WolfBreakout_HVRSPB.py` — High-Velocity Relative-Strength Parkinson Breakout strategy
  - `tests/test_wolfbreakout_hvrspb.py` — Comprehensive unit test suite (36 tests)
- **Build status**: PASS (36/36 tests passing in pytest and unittest, 109/109 in full test suite)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 36 passed in 2.20s (pytest) / 0.192s (unittest). 0 failures, 0 errors.
- **Lint status**: Clean Python syntax verified via py_compile and Docker import.
- **Tests added/modified**: 36 new unit tests in `tests/test_wolfbreakout_hvrspb.py`.

## Loaded Skills
- None
