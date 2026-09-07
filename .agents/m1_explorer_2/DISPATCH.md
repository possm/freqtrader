# Dispatch for Milestone 1 Explorer 2 (Strategy Architecture & API Conformance)

## Mission
Analyze existing production strategies and define the exact architecture for `WolfBreakout_PVB.py`.

## Instructions
1. Read `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md`, `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md`, `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md`, and `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/handoff.md`.
2. Inspect existing production strategies (e.g. `user_data/strategies/WolfTrend_1h_Candidate.py`, `WolfQuantEdge.py`, and `kraken_slippage.py`).
3. Define the exact Python class structure for `WolfBreakout_PVB`:
   - `IStrategy` inheritance, `INTERFACE_VERSION = 3`
   - `timeframe = '1h'`
   - `informative_pairs()` for BTC trend filter (`BTC/EUR` or `BTC/USDT`)
   - `populate_indicators()`, `populate_entry_trend()`, `populate_exit_trend()`
   - Hyperoptable parameters (`IntParameter`, `DecimalParameter`)
   - Stoploss, trailing stop, and minimal ROI table
4. Deliver your findings in `handoff.md` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2/handoff.md`.

## 2026-09-04T15:27:40Z
<USER_REQUEST>
You are Milestone 1 Explorer 2 (Strategy Architecture).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/handoff.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2/DISPATCH.md.

Tasks:
1. Analyze existing strategies (WolfTrend_1h_Candidate.py, WolfQuantEdge.py, kraken_slippage.py) for class structure, IStrategy requirements, informative pairs, and hyperopt parameter definitions.
2. Formulate the precise architectural blueprint for user_data/strategies/WolfBreakout_PVB.py.
3. Write your report in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2/handoff.md.
4. Send a completion message to the parent orchestrator.
</USER_REQUEST>
