# Lesson Learned: Strategy Overfitting vs Pair Filtering (Oct 2026)

## Context
When trying to optimize a macro-breakout strategy (`WolfBreakout_Daily`) to catch recent explosive bull-runs (like AAVE and RENDER in Sept/Oct 2026), hyperopt aggressively relaxed the `buy_vol_multiplier` (from 1.8x to 0.79x) and `donchian_period` (from 7 to 2), and widened the `trailing_stop` (from 7.9% to 32%). 

While this created massive simulated profits (+20% in 1 month) during the trending period, a full Year-To-Date (YTD) backtest revealed it was severely **overfitted**:
- **Strict Original:** +66.9% profit, 70.1% winrate, **-3.8% drawdown** (survived choppy months beautifully).
- **Relaxed/Overfitted:** +9.8% profit, 42.7% winrate, **-23.8% drawdown** (destroyed by fake-outs in choppy months).

## The Core Lesson
1. **Never relax entry criteria to catch anomalies:** In crypto, choppy and sideways markets account for 80% of the year. A strict breakout strategy protects capital during these periods. Loosening criteria to catch a recent missed run will invariably result in catastrophic fake-out losses during the rest of the year. 
2. **Optimize via Pair Blacklisting, not Strategy Weakening:** The most effective and safest way to boost an already robust strategy is by identifying specific pairs that consistently drag down performance (e.g., highly volatile fake-out coins like `RENDER` or low-volatility dead coins like `TRX`) and removing them from the whitelist. Doing so instantly increased the YTD winrate from 70.1% to 73.6% and bumped total profit without increasing drawdown.

## Guideline
When the user asks to "sharpen" or "catch more runs" for an already robust strategy (SQN > 3), **do not default to modifying core entry/exit logic**. Instead, run a YTD analysis, identify underperforming pairs via the Freqtrade backtest analysis, and propose blacklisting them. Only modify core parameters if a YTD backtest explicitly proves it doesn't harm the maximum drawdown.
