## 2026-09-04T19:37:23Z
You are Fix Explorer 3 for Milestone 1 Iteration 2.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_3
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Reviewer 2 Feedback: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/handoff.md

CONTEXT & FAILURE REPORT:
Reviewer 2 noted that existing tests in `tests/test_wolfbreakout_hvrspb.py` did not catch the hyperopt KeyError because they only tested parameter object attribute presence rather than trial dictionary parameter resolution.

TASK:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/m1_reviewer_hvrspb_2/handoff.md`.
2. Inspect `tests/test_wolfbreakout_hvrspb.py` and Reviewer 2's verification script (lines 146–155 of `handoff.md`).
3. Design tests to be added to `tests/test_wolfbreakout_hvrspb.py`:
   - A test simulating Freqtrade's `ft_load_hyper_params(hyperopt=True)` and parameter assignment across all spaces (`buy`, `sell`, `stoploss`).
   - Assertion that custom exit/trailing parameters belong to `space="sell"`.
   - Assertion that no dead-code parameters exist.
   - Verification that 4-candle grace period is respected before midline exit triggers.
4. Provide exact test code recommendations for Worker. Do NOT modify tests yourself.
5. Write handoff to `.agents/m1_fix_explorer_3/handoff.md` and send message to orchestrator.
