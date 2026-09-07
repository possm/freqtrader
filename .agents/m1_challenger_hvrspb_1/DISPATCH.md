## 2026-09-04T19:29:42Z
You are Challenger 1 for Milestone 1: Empirical & Robustness Verification.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_challenger_hvrspb_1
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Worker Handoff: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_hvrspb/handoff.md

TASK & CRITERIA:
1. Adversarially stress test `user_data/strategies/WolfBreakout_HVRSPB.py`.
2. Create and run stress tests (can write temporary test scripts in your working directory):
   - Sudden flash crashes (-50% single candle).
   - Massive volatility spikes (PVR > 10.0).
   - Zero volume / flat candles / zero high-low range (division by zero / log of zero in Parkinson).
   - Completely missing BTC informative pair data (verify benchmark-neutral fallback).
   - Startup NaN propagation.
3. Verify whether any scenario causes unhandled crashes, infinite loops, or invalid orders.
4. Conclude with a clear verdict: APPROVE or REJECT in `.agents/m1_challenger_hvrspb_1/handoff.md` and send message to orchestrator.
