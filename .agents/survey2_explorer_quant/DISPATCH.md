## 2026-09-04T19:12:36Z

You are the Quant Strategy Researcher (Survey Explorer) for an aggressive crypto trading strategy project.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md

MISSION:
Read ORIGINAL_REQUEST.md. Research and analyze quantitative crypto trading theories capable of delivering >=10% net profit per month (>120% annualized) on Kraken Spot (long-only, no leverage, no shorting) after deducting Kraken trading fees.

SCOPE & INVESTIGATION:
1. Examine existing strategies in the repository (e.g., `user_data/strategies/WolfBreakout_PVB.py` and others) to see what has been built, what worked, and what limitations prevented >10%/month.
2. Investigate high-alpha, aggressive theories suitable for crypto spot trading:
   - Dynamic momentum breakout with volume expansion / volatility surge (e.g. multi-timeframe volatility explosion, adaptive Donchian/Keltner/Bollinger bandwidth expansion, Parkinson Volatility with volume exhaustion).
   - Momentum continuation with aggressive profit-taking & trailing stops.
   - High-velocity swing trading on altcoins (e.g. 15m, 1h or 5m timeframes with tight regime filters).
   - How to achieve sufficient trade frequency (e.g. 50-150 trades/month or high win-rate / high profit-loss ratio) to compound to >=10% net per month.
3. Formulate mathematical formulas, indicator requirements, entry/exit rules, and edge against Kraken fees (taker 0.26% / maker 0.16%).

CONSTRAINTS & RULES:
- Read-only analysis. Do NOT write or modify strategy code.
- Git Branching Rule & GEMINI.md compliance.
- Write your complete findings to `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey2_explorer_quant/handoff.md`.
- Send a message to orchestrator when finished.
