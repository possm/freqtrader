## 2026-09-04T19:23:04Z

You are the Strategy Implementation Worker for Milestone 1.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_hvrspb
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Explorer Research Report: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/handoff.md

WRITE OWNERSHIP:
You have exclusive write access to:
- `user_data/strategies/WolfBreakout_HVRSPB.py`
- `tests/test_wolfbreakout_hvrspb.py`
- Files in your working directory `.agents/m1_worker_hvrspb/`
Do NOT edit other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

GIT & USER RULES:
- The git branch is already set to `feat/aggressive-10pct-monthly-strategy`.
- Do NOT commit to main or master. Commit only to this feature branch if making commits.
- NEVER execute `git push` to remote — awaiting user authorization.

TASK & SPECIFICATIONS:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/handoff.md`.
2. Implement `user_data/strategies/WolfBreakout_HVRSPB.py`:
   - Class `WolfBreakout_HVRSPB` inheriting from `IStrategy`.
   - `timeframe = '1h'`.
   - Define `informative_pairs()` returning `('BTC/EUR', '1h')` and `('BTC/USDT', '1h')`.
   - Implement Parkinson Volatility Ratio (PVR): continuous high-low range estimator over 20 periods vs EMA of Parkinson volatility.
   - Implement Relative Strength (RS vs BTC): calculate 24h rolling return of the asset vs BTC 24h rolling return ($RS = R_{asset, 24h} - R_{BTC, 24h}$).
   - Implement Donchian Channel (20 period) and Keltner Channel (20 period, 1.5 ATR).
   - Entry triggers: RS > rs_threshold (hyperoptable, default 0.025), PVR > pvr_threshold (hyperoptable, default 1.15), Close > Donchian Upper, Volume > Volume SMA20 * volume_factor.
   - Exit & Risk: fast invalidation on trend collapse (exit signal if Close < Donchian Mid after 4 candles), asymmetric trailing stop (+3.5% breakeven lock, trailing runner).
   - Hyperoptable parameters: `CategoricalParameter`, `DecimalParameter`, `IntParameter` for buy, roi, stoploss, trailing spaces.
   - Freqtrade order types: limit orders for entry and exit to capture maker fees (0.16% vs 0.26% taker).
   - Robust error handling: handle missing informative pair data gracefully (fallback to benchmark-neutral if informative pair missing).
3. Implement `tests/test_wolfbreakout_hvrspb.py`:
   - Unit tests verifying:
     - Correct Parkinson Volatility calculation and zero-division handling.
     - Relative Strength calculation against synthetic BTC informative dataframe.
     - Indicator population on synthetic OHLCV data.
     - Entry signal generation on breakout conditions.
     - Exit signal generation on invalidation conditions.
     - Graceful handling of edge cases: empty dataframe, missing columns, NaNs, missing informative pair.
4. Run tests locally:
   - Run `pytest tests/test_wolfbreakout_hvrspb.py -v`.
   - Ensure 100% tests pass.
   - Test that python can import the strategy cleanly (`python3 -c "from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB; print('Loaded successfully')"`).
5. Write handoff report:
   - Document changes, indicator formulas, test results, and commands in `.agents/m1_worker_hvrspb/handoff.md`.
   - Send completion message to parent.
