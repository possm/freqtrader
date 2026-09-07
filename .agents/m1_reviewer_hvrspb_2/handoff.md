# Reviewer 2 & Adversarial Critic Report: Milestone 1 Verification

**Agent**: `m1_reviewer_hvrspb_2` (Reviewer 2 / Adversarial Critic)  
**Assigned Review Scope**: `user_data/strategies/WolfBreakout_HVRSPB.py` (focus: Risk Management, Exit Logic, Custom Stoploss, Fast Invalidation, Hyperopt Spaces, Unit Tests)  
**Working Directory**: `.agents/m1_reviewer_hvrspb_2/`  
**Date**: September 4, 2026  
**Verdict**: **REQUEST_CHANGES**

---

## Executive Review Summary

| Evaluation Dimension | Assessment | Status |
|---|---|---|
| **Core Indicator Mathematics** | Parkinson Continuous Volatility (PVR), RS vs BTC, Donchian, Keltner | **PASS** |
| **Lookahead Bias Prevention** | Strict `.shift(1)` on Donchian channel | **PASS** |
| **Two-Tier Stoploss Math** | +3.5% open profit locks +0.8% breakeven; +8.0% open profit trails 4.0% | **PASS** |
| **Local Test Execution** | `pytest tests/test_wolfbreakout_hvrspb.py -v` (36 passed in 2.38s) | **PASS** |
| **Fast Invalidation Architecture** | `populate_exit_trend` vs `custom_exit` holding period | **MAJOR ISSUE** |
| **Hyperopt Spaces & Integrity** | `hard_stoploss` is dead code; `space="trailing"` and `space="stoploss"` fatally crash Freqtrade Hyperopt | **CRITICAL / INTEGRITY VIOLATION** |

---

## Review Findings

### [Critical / INTEGRITY VIOLATION] Finding 1: Dead-Code Parameter Facade `hard_stoploss` Triggers Fatal `KeyError: 'hard_stoploss'` in Hyperopt
- **What**: `WolfBreakout_HVRSPB.py` declares a hyperoptable parameter:
  ```python
  hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
  ```
  This parameter is completely unused anywhere in the strategy logic. Furthermore, when running `freqtrade hyperopt --spaces stoploss` or `--spaces all`, Freqtrade immediately crashes with `KeyError: 'hard_stoploss'`.
- **Where**: `user_data/strategies/WolfBreakout_HVRSPB.py:145`
- **Why**: 
  1. *Integrity Violation*: `hard_stoploss` is a dummy parameter facade. It creates the appearance of a hyperoptable stoploss parameter (and the unit test `test_hyperopt_spaces_presence` passes by merely checking `hard_stoploss.space == "stoploss"`), but the strategy never reads `self.hard_stoploss.value`. In `custom_stoploss`, below the breakeven threshold, the function simply executes `return None` (line 446), falling back to the class attribute `stoploss = -0.06`.
  2. *Fatal Hyperopt Crash*: In Freqtrade's engine (`freqtrade/optimize/hyperopt/hyperopt_optimizer.py:241`), the `stoploss` space natively creates a single dimension named `"stoploss"`, which directly updates `self.backtesting.strategy.stoploss = params_dict["stoploss"]`. However, because `hard_stoploss` is declared with `space="stoploss"`, `freqtrade/strategy/hyper.py:136` marks `hard_stoploss.in_space = True`. During trial evaluation (`hyperopt_optimizer.py:274-276`), Freqtrade executes:
     ```python
     for attr_name, attr in self.backtesting.strategy.enumerate_parameters():
         if attr.in_space and attr.optimize:
             attr.value = params_dict[attr_name]
     ```
     Because `params_dict` only contains `'stoploss'`, looking up `params_dict['hard_stoploss']` raises a fatal `KeyError: 'hard_stoploss'`.
- **Suggestion**:
  - Remove `hard_stoploss = DecimalParameter(...)` completely and rely on Freqtrade's native `stoploss` space (or provide a `stoploss_space()` override if custom bounds `[-0.12, -0.04]` are desired).
  - Alternatively, if `hard_stoploss` is retained, move it to `space="sell"` and ensure `custom_stoploss` actually returns `float(self.hard_stoploss.value)` instead of `None`.

---

### [Critical] Finding 2: Custom Trailing Runner Parameters Declared in Reserved `space="trailing"` Crash Hyperopt with `KeyError: 'be_lock_margin'`
- **What**: Lines 148–151 declare:
  ```python
  be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="trailing", optimize=True)
  be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="trailing", optimize=True)
  trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="trailing", optimize=True)
  trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="trailing", optimize=True)
  ```
  Running `freqtrade hyperopt --spaces trailing` or `--spaces all` raises a fatal `KeyError: 'be_lock_margin'` and crashes.
- **Where**: `user_data/strategies/WolfBreakout_HVRSPB.py:148-151`
- **Why**:
  1. In Freqtrade, `space="trailing"` is a hardcoded built-in space reserved strictly for Freqtrade's native trailing engine (`trailing_stop`, `trailing_stop_positive`, `trailing_stop_positive_offset_p1`, `trailing_only_offset_is_reached`).
  2. Because `WolfBreakout_HVRSPB` uses `use_custom_stoploss = True` and `trailing_stop = False`, the trailing runner is a custom strategy exit mechanism.
  3. When running hyperopt with `--spaces trailing` or `--spaces all`, `HyperOptAuto.trailing_space()` creates dimensions for Freqtrade's built-in parameters, while `_ft_set_param` flags `be_lock_margin.in_space = True`. In `_evaluate_epoch`, accessing `params_dict['be_lock_margin']` immediately raises `KeyError: 'be_lock_margin'`.
  4. Conversely, when running standard hyperopt (`--spaces default` or `--spaces buy sell`), parameters with `space="trailing"` are ignored and never optimized.
- **Suggestion**:
  - In Freqtrade, all custom exit/trailing parameters belonging to `custom_stoploss` and `custom_exit` must be placed in `space="sell"` (exactly as done in `WolfCustomSwing_Hyper.py`).
  - Change `space="trailing"` to `space="sell"` for `be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, and `trailing_runner_distance`.
  - Update `tests/test_wolfbreakout_hvrspb.py:765-768` to assert these parameters belong to `space="sell"`.

---

### [Major] Finding 3: Premature Midline Exit in `populate_exit_trend` Nullifies 4-Candle Invalidation Grace Period in `custom_exit`
- **What**: In `populate_exit_trend` (lines 396–403):
  ```python
  if self.exit_donchian_mid.value and "donchian_mid" in dataframe.columns:
      exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])
  ```
  This triggers `exit_long = 1` unconditionally on any candle where `close < donchian_mid`.
- **Where**: `user_data/strategies/WolfBreakout_HVRSPB.py:396-403` vs `WolfBreakout_HVRSPB.py:478-486`
- **Why**:
  1. `PROJECT.md` line 61 explicitly specifies: *"Exit Logic: 1. Time/Volatility invalidation: Close < Entry EMA or Donchian Mid after 4 candles."*
  2. `custom_exit` correctly gates the midline check behind `if duration_hours >= float(self.invalidation_candles.value):` (giving the breakout position a 4-hour breathing room to absorb retest volatility).
  3. However, because `use_exit_signal = True`, an exit signal generated by `populate_exit_trend` on candles 1, 2, or 3 immediately terminates the trade at the candle close, completely nullifying the 4-candle breathing window intended by `custom_exit`.
- **Suggestion**:
  - Centralize midline breakdown exit logic into `custom_exit` where trade duration is known, and let `populate_exit_trend` handle pure indicator-level macro breakdown, OR remove midline exit from `populate_exit_trend` so `custom_exit` has exclusive authority over time-gated invalidation.

---

## 5-Component Handoff Protocol

### 1. Observation
1. **Pytest execution**:
   Command: `docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint sh freqtradeorg/freqtrade:stable -c "pip install pytest -q && pytest tests/test_wolfbreakout_hvrspb.py -o addopts='' -v"`
   Result: 36 passed in 2.38s.
2. **Repository regression test**:
   Command: `docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v`
   Result: Ran 109 tests, exit code 0, OK.
3. **Dead-Code Search in `WolfBreakout_HVRSPB.py`**:
   `grep -n "hard_stoploss" user_data/strategies/WolfBreakout_HVRSPB.py`
   Output:
   ```
   145:    hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
   ```
   Zero other references exist in the entire file. In `custom_stoploss`:
   ```python
   445:        # Below breakeven threshold: hard stoploss governs
   446:        return None
   ```
4. **Hyperopt KeyError Reproduction**:
   Executed command inside Docker:
   ```python
   strat = WolfBreakout_HVRSPB({'stake_currency': 'EUR', 'spaces': ['stoploss', 'trailing']})
   strat.ft_load_hyper_params(hyperopt=True)
   # Simulating Freqtrade HyperOptimizer._evaluate_epoch()
   for attr_name, attr in strat.enumerate_parameters():
       if attr.in_space and attr.optimize:
           val = params_dict[attr_name]
   ```
   Verbatim output:
   ```
   KeyError: 'hard_stoploss'
   KeyError: 'be_lock_margin'
   ```

### 2. Logic Chain
1. *Observation 3* proves that `hard_stoploss` is defined as a parameter in `space="stoploss"`, but is never referenced anywhere in `custom_stoploss` or any other method in `WolfBreakout_HVRSPB.py`.
2. *Observation 4* demonstrates that when Freqtrade initializes hyperopt with `--spaces stoploss`, `params_dict` only receives keys generated by `HyperOptAuto.stoploss_space()`, which contains only `'stoploss'`.
3. Because `_ft_set_param` flags `hard_stoploss.in_space = True`, `_evaluate_epoch` attempts to read `params_dict['hard_stoploss']` and crashes immediately with `KeyError: 'hard_stoploss'`.
4. The same failure mode occurs for `be_lock_margin`, `be_profit_threshold`, `trailing_runner_offset`, and `trailing_runner_distance`: because their space is `"trailing"`, Freqtrade's `trailing_space()` generates keys `['trailing_stop', 'trailing_stop_positive', 'trailing_stop_positive_offset_p1', 'trailing_only_offset_is_reached']`, causing a fatal `KeyError: 'be_lock_margin'`.
5. Therefore, `WolfBreakout_HVRSPB.py` cannot be hyperoptimized under the spaces prescribed in Milestone 2 (`stoploss` and `trailing`), and contains a dummy parameter facade.

### 3. Caveats
- The core mathematical calculations (Parkinson Continuous Volatility Ratio, 24h Relative Strength vs BTC, and Donchian lookahead-free `.shift(1)`) are genuinely and elegantly implemented.
- The unit test suite in `tests/test_wolfbreakout_hvrspb.py` is well-written for indicator values and entry triggers, but suffered from blind spots regarding Freqtrade's hyperopt parameter resolution mechanics.

### 4. Conclusion
The implementation of `WolfBreakout_HVRSPB.py` fails quality and adversarial review criteria due to:
1. **INTEGRITY VIOLATION**: Dead-code facade parameter `hard_stoploss`.
2. **CRITICAL DEFECT**: Fatal `KeyError` crashes when hyperoptimizing `stoploss` and `trailing` spaces.
3. **MAJOR DEFECT**: Signal conflict between `populate_exit_trend` and `custom_exit` 4-candle grace period.

**Verdict: REQUEST_CHANGES**. The worker must fix the parameter spaces and dead code before Milestone 2 can proceed.

### 5. Verification Method
To independently reproduce this finding:
1. Run the reproduction script:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
   from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
   config = {'stake_currency': 'EUR', 'spaces': ['stoploss', 'trailing']}
   strat = WolfBreakout_HVRSPB(config)
   strat.ft_load_hyper_params(hyperopt=True)
   params_dict = {'stoploss': -0.05, 'trailing_stop': True, 'trailing_stop_positive': 0.02, 'trailing_stop_positive_offset_p1': 0.01, 'trailing_only_offset_is_reached': False}
   for name, p in strat.enumerate_parameters():
       if p.in_space and p.optimize:
           val = params_dict[name]
   "
   ```
   *Expected Output*: Fails with `KeyError: 'be_lock_margin'` or `KeyError: 'hard_stoploss'`.
2. Verify resolution:
   After worker moves custom exit/trailing parameters to `space="sell"` and cleans up `hard_stoploss`, the above script will complete with exit code 0.
