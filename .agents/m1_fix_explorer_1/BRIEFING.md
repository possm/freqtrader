# BRIEFING — 2026-09-04T19:42:45Z

## Mission
Investigate and formulate precise architectural fixes for hyperopt parameter spaces in WolfBreakout_HVRSPB strategy (resolving KeyError on 'hard_stoploss' in stoploss space and KeyError on custom parameters in trailing space).

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: explorer, investigator, architect
- Working directory: /Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_fix_explorer_1
- Original parent: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Milestone: Milestone 1 Iteration 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code directly
- Propose exact code diffs/recommendations for Worker in handoff report
- Adhere strictly to 5-component handoff protocol
- Write only to .agents/m1_fix_explorer_1/

## Current Parent
- Conversation ID: ba5776fc-3ca4-4ec3-bca6-bdbb099c49c7
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `user_data/strategies/WolfBreakout_HVRSPB.py` (lines 1-498)
  - `tests/test_wolfbreakout_hvrspb.py` (lines 520-785)
  - `.agents/m1_reviewer_hvrspb_2/handoff.md`
  - Freqtrade hyperopt engine internals: `HyperOptAuto`, `IHyperOpt`, `HyperOptimizer.generate_optimizer`, `detect_all_parameters`, `_ft_set_param`
- **Key findings**:
  1. `space="stoploss"` in Freqtrade creates a single dimension `'stoploss'` updating `strategy.stoploss`. Any `BaseParameter` with `space="stoploss"` flags `in_space = True` and triggers fatal `KeyError` when Freqtrade iterates `strategy.enumerate_parameters()`. `hard_stoploss` is dead code (custom_stoploss returns `None`, falling back to `stoploss = -0.06`).
  2. `space="trailing"` is hardcoded for native trailing stop dimensions (`trailing_stop`, `trailing_stop_positive`, `trailing_stop_positive_offset_p1`, `trailing_only_offset_is_reached`). Custom parameters in `space="trailing"` crash with `KeyError` on `--spaces trailing` and are ignored on `--spaces sell`.
  3. Solution: Remove `hard_stoploss` parameter. Implement inner `class HyperOpt: stoploss_space()` returning `[SKDecimal(-0.12, -0.04, decimals=3, name="stoploss")]` to configure custom bounds for native `stoploss`. Move custom trailing parameters (`be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, `trailing_runner_distance`) to `space="sell"`.
  4. Midline exit in `populate_exit_trend` preempts `custom_exit`'s 4-candle grace period; centralized into `custom_exit` gated by `self.exit_donchian_mid.value`.
- **Unexplored areas**: None for M1 Iteration 2 scope.

## Key Decisions Made
- Confirmed inner `HyperOpt` class pattern with `stoploss_space()` as Freqtrade native standard.
- Verified elimination of KeyErrors and full parameter compatibility across `--spaces buy sell stoploss`, `--spaces stoploss trailing`, and `--spaces all`.

## Artifact Index
- `.agents/m1_fix_explorer_1/DISPATCH.md` — Incoming prompt record
- `.agents/m1_fix_explorer_1/BRIEFING.md` — Persistent context & identity
- `.agents/m1_fix_explorer_1/progress.md` — Progress & liveness tracking
- `.agents/m1_fix_explorer_1/handoff.md` — Final handoff report with exact diff recommendations
