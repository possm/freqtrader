# BRIEFING — 2026-09-04T19:40:50Z

## Mission
Investigate and resolve the exit logic timing defect in WolfBreakout_HVRSPB.py where `populate_exit_trend` preempts the 4-candle breathing room intended by `custom_exit`.

## 🔒 My Identity
- Archetype: explorer
- Roles: Fix Explorer 2
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_2
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Milestone 1 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify strategy code
- Provide exact code diff recommendations for Worker
- Produce structured handoff report in .agents/m1_fix_explorer_2/handoff.md
- Communicate findings back via send_message

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `user_data/strategies/WolfBreakout_HVRSPB.py` (exit parameters, `populate_exit_trend`, `custom_exit`, `custom_stoploss`)
  - `tests/test_wolfbreakout_hvrspb.py` (exit unit tests, hyperopt parameter assertions)
  - `freqtrade/strategy/interface.py:1462-1510` (`IStrategy.should_exit()`)
  - `PROJECT.md` & `ORIGINAL_REQUEST.md` (exit specifications and requirements)
- **Key findings**:
  1. In Freqtrade's `IStrategy.should_exit()`, `custom_exit()` is strictly inside the `else:` branch of `if exit_ and not enter:`. If `populate_exit_trend` sets `exit_long = 1`, `custom_exit` is NEVER called for that candle!
  2. Because `populate_exit_trend` sets `exit_long = 1` whenever `close < donchian_mid`, any candle 1, 2, or 3 with price below midline immediately triggers `ExitType.EXIT_SIGNAL` ("trend_invalidation_mid"), completely bypassing the 4-candle breathing window.
  3. Disabling `use_exit_signal = False` would be catastrophic because `IStrategy.should_exit()` wraps BOTH signal exit and `custom_exit` under `if self.use_exit_signal:`. If `use_exit_signal = False`, `custom_exit` is completely disabled.
  4. In `custom_exit`, line 484 currently omitted `self.exit_donchian_mid.value`, meaning setting the hyperoptable parameter to `False` had no effect.
- **Unexplored areas**: None. All exit paths verified empirically inside Docker container.

## Key Decisions Made
- Midline breakdown must be handled EXCLUSIVELY by `custom_exit` with duration gating.
- `populate_exit_trend` must initialize `exit_long = 0` and leave it at 0.
- `use_exit_signal` must remain `True`.
- `custom_exit` must check `self.exit_donchian_mid.value`.
- Unit test `test_exit_signal_on_donchian_mid_break` in `tests/test_wolfbreakout_hvrspb.py` must be updated to expect `exit_long == 0`.

## Artifact Index
- .agents/m1_fix_explorer_2/DISPATCH.md — Dispatch log
- .agents/m1_fix_explorer_2/BRIEFING.md — Persistent briefing state
- .agents/m1_fix_explorer_2/progress.md — Heartbeat and progress log
- .agents/m1_fix_explorer_2/handoff.md — Final handoff report
