# BRIEFING — 2026-09-04T15:23:00Z

## Mission
Conduct literature research on academic quantitative theories for altcoin trading, design a primary and alternative strategy capable of beating Kraken fees with >10% net profit, and hand off specifications to the team.

## 🔒 My Identity
- Archetype: explorer
- Roles: Academic Quant Researcher, Survey Explorer
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3
- Original parent: 90978f93-4bda-450d-89cf-eb27ba874681
- Milestone: M1 Literature Research & Strategy Formulation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Only write metadata/reports in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/
- Strategy must account for Kraken taker fees (0.26% - 0.40%)
- Target >10% net profit after fees
- Formulate 1 primary strategy + 1 alternative fallback strategy
- Use 5-component handoff format

## Current Parent
- Conversation ID: 90978f93-4bda-450d-89cf-eb27ba874681
- Updated: 2026-09-04T15:23:00Z

## Investigation State
- **Explored paths**: ORIGINAL_REQUEST.md, orchestrator/DISPATCH.md, survey_explorer_3/DISPATCH.md, config_kraken_dryrun.json, config_backtest.json, docker-compose.yml, academic papers (Parkinson 1980, Garman-Klass 1980, HAR-RV crypto 2024-2026, Ornstein-Uhlenbeck 1930, Mandelbrot 1963).
- **Key findings**:
  1. Parkinson (1980) range-based volatility estimator outperforms Garman-Klass in 24/7 crypto due to microstructure noise in Open/Close timestamps.
  2. Kraken taker fees (0.26%-0.40% per side -> 0.52%-0.80% roundtrip + slippage) make 15m timeframes mathematically non-viable for altcoin spot trading.
  3. 1h timeframe offers optimal balance: average winning swings of +4.5% to +9.5% easily clear the 0.65%-0.80% fee hurdle.
  4. Primary strategy: WolfBreakout-PVB (Parkinson Volatility Breakout with Donchian/Keltner channels, ATR Chandelier exit, and BTC macro gate).
  5. Fallback strategy: Wolf-OUMR (Ornstein-Uhlenbeck Mean Reversion with rolling Hurst exponent H < 0.45 anti-persistence gate).
- **Unexplored areas**: None for survey explorer; ready for implementation and hyperopt tuning by Data Scientist.

## Key Decisions Made
- Selected WolfBreakout-PVB (Parkinson Volatility Breakout) as the primary academic quantitative strategy.
- Selected 1h timeframe as primary (justified by fee hurdle analysis vs 15m and 4h).
- Designed Wolf-OUMR (Ornstein-Uhlenbeck with Hurst Exponent < 0.45) as fallback alternative.
- Formulated comprehensive parameter bounds and search spaces for hyperopt tuning on VPS.

## Artifact Index
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/handoff.md — Final academic research & strategy specification report (5-component format)
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/progress.md — Execution heartbeat and progress tracking
- /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/BRIEFING.md — Situational awareness working memory

