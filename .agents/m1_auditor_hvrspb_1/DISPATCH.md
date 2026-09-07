## 2026-09-04T19:29:42Z

You are the Forensic Auditor for Milestone 1: Integrity Forensics.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_auditor_hvrspb_1
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Worker Handoff: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_hvrspb/handoff.md

TASK & AUDIT CHECKS:
1. Conduct an exhaustive forensic integrity audit of `user_data/strategies/WolfBreakout_HVRSPB.py` and `tests/test_wolfbreakout_hvrspb.py`:
   - Cheating detection: Check for hardcoded test results, mocked indicators that return fixed outputs, dummy logic, or test bypasses.
   - Lookahead bias: Audit all `.shift()`, `.rolling()`, and indicator joins (especially informative pair merging) to guarantee no future data leaks into current signals.
   - Fee avoidance: Verify that Kraken trading fees are not bypassed or artificially reduced.
   - Genuine implementation: Confirm all mathematical formulas (Parkinson Volatility, Relative Strength excess return, Donchian, Keltner) are authentically calculated from raw OHLCV.
2. Conclude with a binary verdict: CLEAN or INTEGRITY VIOLATION in `.agents/m1_auditor_hvrspb_1/handoff.md` and send message to orchestrator.
