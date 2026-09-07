# BRIEFING — 2026-09-04T19:43:40Z

## Mission
Investigate test suite gaps in `tests/test_wolfbreakout_hvrspb.py` regarding Hyperopt parameter resolution, custom exit/trailing spaces, dead-code parameters, and 4-candle grace period, and provide exact test recommendations.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_3
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Milestone 1 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT modify tests or source code yourself
- Provide exact test code recommendations for Worker
- All investigations backed by direct observation and complete evidence chain

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: 2026-09-04T19:43:40Z

## Investigation State
- **Explored paths**:
  - `tests/test_wolfbreakout_hvrspb.py`
  - `user_data/strategies/WolfBreakout_HVRSPB.py`
  - `.agents/m1_reviewer_hvrspb_2/handoff.md`
  - `freqtrade/optimize/hyperopt/hyperopt_auto.py`, `hyperopt_optimizer.py`, `freqtrade/strategy/hyper.py`
- **Key findings**:
  1. `hard_stoploss` is dead code (never accessed on `self`) and crashes hyperopt with `KeyError: 'hard_stoploss'` when stoploss space is activated because `HyperOptAuto.stoploss_space()` creates only `stoploss`.
  2. Trailing parameters (`be_lock_margin`, `be_profit_threshold`, `trailing_runner_offset`, `trailing_runner_distance`) in `space="trailing"` crash hyperopt with `KeyError` because `HyperOptAuto.trailing_space()` only creates native trailing dimensions (`trailing_stop`, etc.). Moving them to `space="sell"` aligns them with `HyperOptAuto.get_indicator_space("sell")`.
  3. `populate_exit_trend` triggered exit on `close < donchian_mid` unconditionally, nullifying the 4-candle grace period in `custom_exit`. Midline exit must be handled in `custom_exit` gated by `self.exit_donchian_mid.value` after 4 candles.
  4. Unit test `test_hyperopt_spaces_presence` was enforcing the bug by asserting `hard_stoploss.space == "stoploss"` and trailing parameters `space == "trailing"`.
  5. An AST-based test reliably detects dead-code parameters (`param_names - used_attrs`) and catches facade parameters.
- **Unexplored areas**: None. Full test suite design and code recommendations synthesized.

## Key Decisions Made
- Designed 4 targeted test enhancements/additions for `tests/test_wolfbreakout_hvrspb.py`:
  1. Full hyperopt parameter resolution simulation across spaces (`buy`, `sell`, `stoploss`, `trailing`, `all`, `default`) using `HyperOptAuto`.
  2. Strict assertion that custom exit and trailing parameters belong to `space="sell"` and no parameters exist in reserved spaces.
  3. AST-based automated dead-code detection ensuring every declared `BaseParameter` is accessed on `self` in strategy logic.
  4. Multi-stage grace period test verifying zero exits during candles 1-3, followed by midline and adverse loss invalidation after candle 4, gated by `exit_donchian_mid` and `invalidation_candles`.

## Artifact Index
- DISPATCH.md — Initial dispatch message
- BRIEFING.md — Persistent working memory
- progress.md — Liveness heartbeat
- handoff.md — Final 5-component handoff report
