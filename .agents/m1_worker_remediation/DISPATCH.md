## 2026-09-04T19:44:26Z
You are the Remediation Worker for Milestone 1 Iteration 2.

Working Directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_worker_remediation
Project Root: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend
Original Request File: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md
Project Plan: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md
Reviewer 2 Findings: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_reviewer_hvrspb_2/handoff.md
Fix Explorer 1 Handoff: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_1/handoff.md
Fix Explorer 2 Handoff: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_2/handoff.md
Fix Explorer 3 Handoff: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_3/handoff.md

WRITE OWNERSHIP:
You have exclusive write access to:
- `user_data/strategies/WolfBreakout_HVRSPB.py`
- `tests/test_wolfbreakout_hvrspb.py`
- Files in your working directory `.agents/m1_worker_remediation/`
Do NOT edit other files.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

GIT & USER RULES:
- Branch is `feat/aggressive-10pct-monthly-strategy`. Do NOT commit to main or master.
- NEVER execute `git push` to remote.

TASK:
1. Read the Reviewer 2 handoff and the 3 Fix Explorer handoffs.
2. Apply the recommended architectural fixes to `user_data/strategies/WolfBreakout_HVRSPB.py`:
   - Remove dead-code facade `hard_stoploss` parameter. Ensure Freqtrade's native `stoploss = -0.06` governs stoploss natively. Provide `stoploss_space()` if custom stoploss range is desired, or let Freqtrade manage native stoploss.
   - Change `space="trailing"` to `space="sell"` for custom trailing parameters (`be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, `trailing_runner_distance`).
   - In `populate_exit_trend`, initialize `dataframe["exit_long"] = 0` so that `custom_exit` has full authority over exit timing.
   - In `custom_exit`, gate midline breakdown strictly behind `if duration_hours >= float(self.invalidation_candles.value):` and `self.exit_donchian_mid.value`, ensuring the 4-candle breathing room.
3. Update and harden `tests/test_wolfbreakout_hvrspb.py`:
   - Update parameter space assertions to check that custom trailing/exit parameters belong to `space="sell"`.
   - Add unit tests verifying trial dictionary parameter resolution across all hyperopt spaces (`['buy', 'sell']`, `['stoploss']`, `['trailing']`, `['all']`) without KeyError.
   - Add AST dead-code check ensuring every declared parameter is actively used in strategy logic.
   - Add test verifying 4-candle breathing room before midline exit.
4. Run tests:
   - `pytest tests/test_wolfbreakout_hvrspb.py -v`.
   - Run full test suite (`pytest` or `unittest discover`) to verify 0 regressions across all tests.
   - Run the reproduction script from Reviewer 2 / Fix Explorer 1 to verify that `KeyError: 'hard_stoploss'` and `KeyError: 'be_lock_margin'` are completely eliminated.
5. Write detailed handoff report to `.agents/m1_worker_remediation/handoff.md` and send message to orchestrator.
