## 2026-09-04T19:37:23Z
You are Fix Explorer 2 for Milestone 1 Iteration 2.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_2
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Reviewer 2 Feedback: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/handoff.md

CONTEXT & FAILURE REPORT:
Reviewer 2 found a major defect in the exit logic timing:
In `populate_exit_trend` (lines 396–403), `exit_long = 1` is triggered whenever `close < donchian_mid`. This causes trades to exit immediately on candle 1, 2, or 3, completely nullifying the 4-candle invalidation grace period specified in `PROJECT.md` and intended by `custom_exit`.

TASK:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/m1_reviewer_hvrspb_2/handoff.md`.
2. Inspect `user_data/strategies/WolfBreakout_HVRSPB.py` exit mechanics (`populate_exit_trend` vs `custom_exit`).
3. Formulate the optimal strategy to ensure trades have the intended 4-candle breathing room:
   - Should midline breakdown be handled exclusively by `custom_exit` with duration gating, or should `populate_exit_trend` leave exit_long to 0 unless emergency indicator signals occur?
   - How to ensure clean exit behavior without signal conflicts.
4. Provide exact code diff recommendations for Worker. Do NOT modify strategy code yourself.
5. Write handoff to `.agents/m1_fix_explorer_2/handoff.md` and send message to orchestrator.
