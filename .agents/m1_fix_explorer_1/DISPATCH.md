## 2026-09-04T19:37:23Z

You are Fix Explorer 1 for Milestone 1 Iteration 2.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_1
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Reviewer 2 Feedback: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/handoff.md

CONTEXT & FAILURE REPORT:
Reviewer 2 issued REQUEST_CHANGES due to critical defects in hyperopt parameter spaces:
1. `hard_stoploss` is declared with `space="stoploss"`, but is never used in the strategy logic (dead-code facade). When running hyperopt with `--spaces stoploss`, Freqtrade's engine expects only `'stoploss'`, crashing with `KeyError: 'hard_stoploss'`.
2. Custom trailing runner parameters (`be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, `trailing_runner_distance`) are declared with `space="trailing"`. In Freqtrade, `space="trailing"` is reserved for native trailing parameters. Running `--spaces trailing` crashes with `KeyError: 'be_lock_margin'`.

TASK:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and `.agents/m1_reviewer_hvrspb_2/handoff.md`.
2. Inspect `user_data/strategies/WolfBreakout_HVRSPB.py` and Freqtrade's hyperopt mechanics.
3. Formulate the precise architectural fix for the parameter spaces:
   - How `hard_stoploss` should be removed or restructured so Freqtrade native `stoploss = -0.06` or custom `stoploss_space()` functions without KeyError.
   - How the custom trailing parameters should be moved to `space="sell"`.
4. Provide exact code diff recommendations for Worker. Do NOT modify strategy code yourself.
5. Write handoff to `.agents/m1_fix_explorer_1/handoff.md` and send message to orchestrator.
