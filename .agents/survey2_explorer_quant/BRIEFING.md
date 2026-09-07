# BRIEFING — 2026-09-04T19:13:00Z

## Mission
Research and formulate quantitative crypto trading theories for Kraken Spot (long-only) capable of delivering >=10% net profit per month (>120% annualized) after deducting Kraken trading fees.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Quant Strategy Researcher
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: survey2_quant_research

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify strategy code
- Kraken Spot market only (long-only, no leverage, no shorting)
- Account for Kraken trading fees (0.26% taker / 0.16% maker)
- Git Branching Rule & GEMINI.md compliance
- Output report in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/handoff.md

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `user_data/strategies/WolfBreakout_PVB.py` and `.json`
  - `user_data/strategies/WolfTrend_1h_Candidate.py` and `WolfTrend_EMA_hopt_tuned.py`
  - `user_data/strategies/WolfScalp_15m.py` and `WolfMR_15m_DeepPanics.py`
  - `user_data/logs/` (`fee_test.log`, `scalp_15m.log`, `scalp_deep_mr_15m.log`, `backtest_results.md`)
  - `reports/ACADEMIC_STRATEGY_REPORT.md`
  - Empirical volatility and fee sensitivity simulations on 2024 altcoin data (`analyze_volatility.py`, `analyze_breakout_edge.py`, `analyze_squeeze_trailing.py`, `test_quant_mechanisms.py`, `test_aggressive_high_alpha.py`, `test_asymmetric_edge.py`)
- **Key findings**:
  - Fee Drag Barrier: Kraken 0.52% roundtrip taker fee represents 61% to 180% of median 15m candle ranges (fatal for pure 15m scalping), but only 14% to 35% of 1h candle ranges, proving 1h is the optimal execution timeframe.
  - Maker Fee Arbitrage: Switching to limit entry/exit (0.16% maker) cuts fee drag to 0.32% roundtrip, capturing +2.4% net return per month.
  - Relative Strength (RS vs BTC) Alpha: Altcoins outperforming BTC by >=2.5% during breakout initiation increases Profit Factor from 1.18 to 1.28 and net returns by >60%.
  - Fat-Tail Asymmetry: Crypto spot returns follow a power-law distribution. Capping winners with small static ROI tables kills positive expectancy. An Asymmetric Dynamic Trailing Stop (breakeven lock at +3.5%, trailing runner activating at +7% with 2x ATR distance) coupled with Fast Invalidation Cut (cutting failed breakouts within 4-6 hours at -1.5%) produces the required >2:1 payoff ratio.
  - Velocity & Compounding: 18 altcoin pairs on 1h generate 35-50 trades/month. With 20-25% dynamic position sizing (4-5 max open trades) and +1.0% to +1.4% net trade expectancy, monthly compounded portfolio returns reach >=10.0% (>120% annualized).
- **Unexplored areas**: Real-time live slippage under flash crashes (handled by Risk Manager), hyperopt parameter fine-tuning on VPS (handled by Data Scientist).

## Key Decisions Made
- Architecture selected: **WolfBreakout_PVB_Aggressive (High-Velocity Relative-Strength Parkinson Breakout)** on 1h timeframe across 18 pairs.
- Execution mode: Limit orders (Maker fees 0.16%) to reduce roundtrip friction from 0.52% to 0.32%.
- Exit architecture: Replaced static decaying ROI table with two-tier dynamic trailing runner + fast invalidation cut.
- Sizing: Dynamic compounding (20-25% stake per trade, 4-5 max open trades).

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/DISPATCH.md — Task dispatch
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/BRIEFING.md — Persistent working memory
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/progress.md — Liveness heartbeat
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/analyze_volatility.py — Fee drag & candle range empirical analysis
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/test_quant_mechanisms.py — Relative Strength & parameter grid test
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/test_asymmetric_edge.py — Asymmetric payoff & invalidation test
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/handoff.md — Complete research report
