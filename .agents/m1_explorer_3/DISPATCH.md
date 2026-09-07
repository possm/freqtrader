# Dispatch for Milestone 1 Explorer 3 (Unit Test & Verification Plan)

## Mission
Design a rigorous unit test and validation plan for `WolfBreakout_PVB.py`.

## Instructions
1. Read `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md`, `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md`, `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md`, and `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/handoff.md`.
2. Design test cases for `tests/test_wolfbreakout_pvb.py`:
   - Parkinson volatility variance calculation (zero division protection, edge cases where High == Low)
   - Donchian and Keltner band calculation with lookaheads prevented (using `.shift(1)`)
   - Entry signal generation on breakout and suppression when filters fail
   - Exit signal generation on mean reversion / channel midline break
   - Freqtrade integration check (e.g. strategy loading and metadata verification)
3. Deliver your findings in `handoff.md` in `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/handoff.md`.

## 2026-09-04T15:27:41Z
You are Milestone 1 Explorer 3 (Unit Test Plan).
Your working directory is /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3.
Read /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/ORIGINAL_REQUEST.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/orchestrator/DISPATCH.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/PROJECT.md, /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/survey_explorer_3/handoff.md, and /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/DISPATCH.md.

Tasks:
1. Design comprehensive unit tests for tests/test_wolfbreakout_pvb.py covering Parkinson volatility variance formula, Donchian/Keltner bands, lookahead prevention, entry and exit conditions, and edge cases.
2. Write your report in /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_3/handoff.md.
3. Send a completion message to the parent orchestrator.

