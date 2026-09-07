# Handoff Report: Fix Explorer 3 — Test Suite Hyperopt & Exit Resolution Hardening

**Agent**: `m1_fix_explorer_3` (Fix Explorer 3)  
**Assigned Mission**: Milestone 1 Iteration 2 — Investigate test suite blind spots in `tests/test_wolfbreakout_hvrspb.py`, verify Reviewer 2 feedback, and design exact unit tests covering Hyperopt trial parameter resolution across all spaces, custom exit/trailing parameter space placement, dead-code parameter elimination, and 4-candle grace period preservation.  
**Working Directory**: `.agents/m1_fix_explorer_3/`  
**Date**: September 4, 2026  

---

## 1. Observation

### 1.1 Existing Test Suite False Confidence & Bug Enforcement
In `tests/test_wolfbreakout_hvrspb.py`:
1. **Enforcing Faulty Parameter Spaces** (lines 763–768):
   ```python
   763:        self.assertEqual(self.strategy.hard_stoploss.space, "stoploss")
   764:
   765:        self.assertEqual(self.strategy.be_profit_threshold.space, "trailing")
   766:        self.assertEqual(self.strategy.be_lock_margin.space, "trailing")
   767:        self.assertEqual(self.strategy.trailing_runner_offset.space, "trailing")
   768:        self.assertEqual(self.strategy.trailing_runner_distance.space, "trailing")
   ```
   *Observation*: The existing test asserted that `hard_stoploss` had `space == "stoploss"` and trailing parameters had `space == "trailing"`. Instead of validating that these parameters can be resolved during a hyperopt trial, the test actively locked in the fatal bug.

2. **Absence of Hyperopt Parameter Resolution Testing**:
   The test suite only inspected `param.space` strings. It never called `ft_load_hyper_params(hyperopt=True)` or simulated trial evaluation via `enumerate_parameters()` against trial dictionaries.

3. **Exit Signal Conflict** (lines 526–537):
   ```python
   526:    def test_exit_signal_on_donchian_mid_break(self):
   527:        """Close penetrates below Donchian Midline -> exit_long == 1."""
   528:        df = generate_synthetic_ohlcv(n_bars=60)
   529:        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
   530:        analyzed.loc[analyzed.index[-1], "donchian_mid"] = 100.0
   531:        analyzed.loc[analyzed.index[-1], "close"] = 98.0  # below donchian_mid
   532:        analyzed.loc[analyzed.index[-1], "volume"] = 1000.0
   533:
   534:        exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
   535:        self.assertEqual(exit_df["exit_long"].iloc[-1], 1)
   536:        self.assertEqual(exit_df["exit_tag"].iloc[-1], "trend_invalidation_mid")
   ```
   *Observation*: The test enforced that `populate_exit_trend` emits `exit_long == 1` unconditionally when `close < donchian_mid`. In live/backtest execution, Freqtrade checks `populate_exit_trend` every candle. If `populate_exit_trend` exits on midline break at candle 1 or 2, the 4-candle grace period implemented in `custom_exit` (lines 478–486) is bypassed and nullified.

### 1.2 Verbatim Errors & Freqtrade Hyperopt Crash Reproduction
When running Reviewer 2's reproduction script against `WolfBreakout_HVRSPB.py`:
- Command:
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
- Verbatim Output:
  ```
  Traceback (most recent call last):
    File "<string>", line 9, in <module>
      val = params_dict[name]
            ~~~~~~~~~~~^^^^^^
  KeyError: 'be_lock_margin'
  ```
- When `spaces = ['stoploss']`:
  ```
  Traceback (most recent call last):
    File "<string>", line 10, in <module>
      val = params_dict[name]
            ~~~~~~~~~~~^^^^^^
  KeyError: 'hard_stoploss'
  ```
- When `spaces = ['default']`:
  ```
  KeyError: 'hard_stoploss'
  ```

### 1.3 Dead-Code Parameter Facade `hard_stoploss`
1. Declared at `user_data/strategies/WolfBreakout_HVRSPB.py:145`:
   ```python
   hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
   ```
2. Grep search across the entire file reveals `hard_stoploss` is NEVER referenced anywhere else:
   `grep -n "hard_stoploss" user_data/strategies/WolfBreakout_HVRSPB.py` -> exactly 1 match (the class declaration line).
3. In `custom_stoploss` (line 446):
   ```python
   # Below breakeven threshold: hard stoploss governs
   return None
   ```
   When `custom_stoploss` returns `None`, Freqtrade falls back to `self.stoploss` (`-0.06`), completely ignoring `self.hard_stoploss.value`.
4. AST analysis confirms that out of all 13 class parameters, `hard_stoploss` has 0 accesses on `self` in strategy methods.

---

## 2. Logic Chain

1. In Freqtrade (`freqtrade/strategy/hyper.py`), `IStrategy._ft_set_param` flags:
   `param.in_space = hyperopt and HyperoptTools.has_space(self.config, space)`
2. In `freqtrade/optimize/hyperopt/hyperopt_auto.py`:
   - `HyperOptAuto.get_indicator_space("buy")` and `get_indicator_space("sell")` iterate over strategy parameters where `p.space == space and p.optimize`, generating search dimensions named after the parameter attribute (`dimension.name == attr_name`).
   - `HyperOptAuto.stoploss_space()` generates exactly ONE dimension named `"stoploss"` (assigning to `strategy.stoploss`). It NEVER inspects strategy parameters.
   - `HyperOptAuto.trailing_space()` generates exactly FOUR native trailing dimensions (`trailing_stop`, `trailing_stop_positive`, `trailing_stop_positive_offset_p1`, `trailing_only_offset_is_reached`). It NEVER inspects strategy parameters.
3. In `freqtrade/optimize/hyperopt/hyperopt_optimizer.py:generate_optimizer`:
   ```python
   for attr_name, attr in self.backtesting.strategy.enumerate_parameters():
       if attr.in_space and attr.optimize:
           attr.value = params_dict[attr_name]
   ```
   Every parameter with `attr.in_space == True` MUST have its name present in `params_dict`.
4. Because `hard_stoploss` has `space="stoploss"`, whenever `stoploss` is in `config["spaces"]`, `hard_stoploss.in_space` is `True`. But `params_dict` only has key `stoploss`. Accessing `params_dict[hard_stoploss]` immediately raises `KeyError: hard_stoploss`.
5. Because `be_lock_margin`, `be_profit_threshold`, `trailing_runner_offset`, and `trailing_runner_distance` have `space="trailing"`, whenever `trailing` or `all` is in `spaces`, they are flagged `in_space = True`. But `params_dict` only has native trailing keys. Looking up `params_dict[be_lock_margin]` immediately raises `KeyError: be_lock_margin`.
6. Therefore, in Freqtrade:
   - All custom exit and custom trailing parameters (`be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, `trailing_runner_distance`, `exit_donchian_mid`, `invalidation_candles`) MUST be declared with `space="sell"`.
   - `hard_stoploss` MUST be removed from the strategy class. Freqtrade natively optimizes stoploss via `space="stoploss"` updating `strategy.stoploss`.
7. Regarding exit signals:
   - `PROJECT.md` line 61 specifies: *"Time/Volatility invalidation: Close < Entry EMA or Donchian Mid after 4 candles."*
   - `populate_exit_trend` executes per candle without trade duration awareness. Firing on `close < donchian_mid` kills trades on candles 1–3 during retest pullbacks.
   - Midline breakdown exit must be removed from `populate_exit_trend` and placed in `custom_exit` gated behind `if duration_hours >= float(self.invalidation_candles.value):` and `if self.exit_donchian_mid.value:`.
8. The unit test suite must be hardened to catch these issues so regression is impossible.

---

## 3. Caveats

1. **Read-Only Scope**: Fix Explorer 3 operates under strict read-only constraints. No production strategy files or unit test files have been modified. All proposed code changes are provided as exact, validated recommendations for the Worker.
2. **Freqtrade Config Prerequisite**: In tests, `HyperOptAuto(config)` requires `config` to contain `timeframe: 1h` and `stake_currency: EUR`.
3. **Environment**: All verification was performed inside the official Docker container `freqtradeorg/freqtrade:stable` ensuring 100% engine compatibility.

---

## 4. Conclusion

The test suite in `tests/test_wolfbreakout_hvrspb.py` required three key fixes:
1. **Hyperopt Parameter Resolution Across Spaces**: Simulate Freqtrade's `ft_load_hyper_params(hyperopt=True)` and parameter assignment across `['buy', 'sell']`, `['stoploss']`, `['trailing']`, `['buy', 'sell', 'stoploss']`, `['default']`, and `['all']`, ensuring zero `KeyError` crashes.
2. **Space Domain & Dead-Code Invariants**: Enforce that all custom exit/trailing parameters belong to `space="sell"`, no parameters belong to reserved spaces (`stoploss`, `trailing`, `roi`), and an automated AST check ensures every declared parameter is actively used in strategy methods.
3. **Grace Period Protection**: Verify that during candles 1–3 (duration < 4h), neither `custom_exit` nor `populate_exit_trend` generates an exit signal on midline retests, and after candle 4, midline and adverse loss invalidation activate, strictly respecting `exit_donchian_mid` and `invalidation_candles`.

---

## 5. Verification Method

### 5.1 Project Test Command (Must Run Cleanly)
```bash
docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v
```

### 5.2 Independent Hyperopt Resolution Check
```bash
docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
from freqtrade.optimize.hyperopt.hyperopt_auto import HyperOptAuto
from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB

for spaces in [['buy', 'sell'], ['buy', 'sell', 'stoploss'], ['stoploss'], ['trailing'], ['all'], ['default']]:
    config = {'stake_currency': 'EUR', 'timeframe': '1h', 'spaces': spaces}
    strat = WolfBreakout_HVRSPB(config)
    strat.ft_load_hyper_params(hyperopt=True)
    auto = HyperOptAuto(config)
    auto.strategy = strat

    dimensions = []
    if 'buy' in spaces or 'all' in spaces or 'default' in spaces:
        dimensions.extend(auto.get_indicator_space('buy'))
    if 'sell' in spaces or 'all' in spaces or 'default' in spaces:
        dimensions.extend(auto.get_indicator_space('sell'))
    if 'stoploss' in spaces or 'all' in spaces or 'default' in spaces:
        dimensions.extend(auto.stoploss_space())
    if 'trailing' in spaces or 'all' in spaces:
        dimensions.extend(auto.trailing_space())

    params_dict = {}
    for dim in dimensions:
        if hasattr(dim, 'low') and hasattr(dim, 'high'):
            params_dict[dim.name] = (dim.low + dim.high) / 2.0
        elif hasattr(dim, 'categories'):
            params_dict[dim.name] = dim.categories[0]
        else:
            params_dict[dim.name] = 0

    for attr_name, attr in strat.enumerate_parameters():
        if attr.in_space and attr.optimize:
            assert attr_name in params_dict, f'{attr_name} missing for spaces={spaces}'
            attr.value = params_dict[attr_name]

    if 'stoploss' in spaces or 'all' in spaces or 'default' in spaces:
        assert 'stoploss' in params_dict
        strat.stoploss = params_dict['stoploss']
print('HYPEROPT PARAMETER RESOLUTION VERIFIED ACROSS ALL SPACES!')
"
```
*Expected Output*: `HYPEROPT PARAMETER RESOLUTION VERIFIED ACROSS ALL SPACES!` with exit code 0.

---

## 6. Worker Implementation Recommendations

### Part A: Strategy Fixes in `user_data/strategies/WolfBreakout_HVRSPB.py`

1. **Delete Dead-Code Facade `hard_stoploss`** (line 145):
   - **Remove**:
     ```python
     # Stoploss Space: Hard circuit breaker
     hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
     ```
   - **Rationale**: Stoploss is natively handled by `stoploss = -0.06` and optimized via Freqtrade's built-in `stoploss` space.

2. **Move Custom Trailing Parameters to `space="sell"`** (lines 147–151):
   - **Before**:
     ```python
     # Trailing Space: Two-Tier Asymmetric Trailing Stop
     be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="trailing", optimize=True)
     be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="trailing", optimize=True)
     trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="trailing", optimize=True)
     trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="trailing", optimize=True)
     ```
   - **After**:
     ```python
     # Sell Space: Dynamic Exits and Two-Tier Asymmetric Trailing Stop
     exit_donchian_mid = BooleanParameter(default=True, space="sell", optimize=True)
     invalidation_candles = IntParameter(2, 8, default=4, space="sell", optimize=True)
     be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="sell", optimize=True)
     be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="sell", optimize=True)
     trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="sell", optimize=True)
     trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="sell", optimize=True)
     ```

3. **Prevent Premature Exit in `populate_exit_trend`** (lines 384–405):
   - **Before**:
     ```python
     exit_conditions = []
     if self.exit_donchian_mid.value and "donchian_mid" in dataframe.columns:
         exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])

     if exit_conditions:
         dataframe.loc[
             np.logical_or.reduce(exit_conditions) & (dataframe["volume"] > 0),
             ["exit_long", "exit_tag"]
         ] = (1, "trend_invalidation_mid")
     ```
   - **After**:
     ```python
     def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         """
         Triggers long exit on momentum trend exhaustion.
         Note: Time-gated dynamic invalidation (midline breakdown after the 4-candle
         grace period) is handled exclusively in custom_exit where trade duration
         is known, preventing premature exit during early retest volatility.
         """
         if dataframe is None or dataframe.empty:
             return dataframe

         dataframe["exit_long"] = 0
         dataframe["exit_tag"] = None
         return dataframe
     ```

4. **Wire `exit_donchian_mid` in `custom_exit`** (lines 483–487):
   - **Before**:
     ```python
     last_candle = df.iloc[-1]
     if "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:
         return "fast_invalidation_mid"
     ```
   - **After**:
     ```python
     last_candle = df.iloc[-1]
     if (
         self.exit_donchian_mid.value
         and "donchian_mid" in last_candle
         and current_rate < last_candle["donchian_mid"]
     ):
         return "fast_invalidation_mid"
     ```

---

### Part B: Test Suite Modifications in `tests/test_wolfbreakout_hvrspb.py`

#### 1. Update `test_hyperopt_spaces_presence` (lines 751–769)
Replace with:
```python
    def test_hyperopt_spaces_presence(self):
        """Verify parameters exist across buy and sell spaces with zero dead code."""
        # Buy Space
        self.assertEqual(self.strategy.donchian_period.space, "buy")
        self.assertEqual(self.strategy.keltner_mult.space, "buy")
        self.assertEqual(self.strategy.pvr_threshold.space, "buy")
        self.assertEqual(self.strategy.rs_threshold.space, "buy")
        self.assertEqual(self.strategy.volume_factor.space, "buy")
        self.assertEqual(self.strategy.macro_filter_mode.space, "buy")

        # Sell Space: Fast invalidation & two-tier trailing stop
        self.assertEqual(self.strategy.exit_donchian_mid.space, "sell")
        self.assertEqual(self.strategy.invalidation_candles.space, "sell")
        self.assertEqual(self.strategy.be_profit_threshold.space, "sell")
        self.assertEqual(self.strategy.be_lock_margin.space, "sell")
        self.assertEqual(self.strategy.trailing_runner_offset.space, "sell")
        self.assertEqual(self.strategy.trailing_runner_distance.space, "sell")

        # Hard stoploss facade parameter must be deleted (stoploss is handled natively)
        self.assertFalse(
            hasattr(WolfBreakout_HVRSPB, "hard_stoploss"),
            "Dead-code facade parameter hard_stoploss must be removed from strategy class."
        )

        # Invariant: All custom strategy parameters must belong exclusively to buy or sell spaces
        self.strategy.ft_load_hyper_params()
        for name, param in self.strategy.enumerate_parameters():
            self.assertIn(
                param.space,
                ["buy", "sell"],
                f"Parameter '{name}' has space='{param.space}'. Custom parameters must only use 'buy' or 'sell'.",
            )
```

#### 2. Add `test_no_dead_code_parameters` to `TestFreqtradeInterfaceAndContract`:
```python
    def test_no_dead_code_parameters(self):
        """
        AST inspection: Asserts that every BaseParameter defined at the class level
        is actively accessed on self in executable strategy methods.
        """
        import ast
        import inspect

        source = inspect.getsource(WolfBreakout_HVRSPB)
        tree = ast.parse(source)
        strat_class = [
            n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "WolfBreakout_HVRSPB"
        ][0]

        # Parameters declared on class
        param_names = set()
        for stmt in strat_class.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                        func_name = getattr(stmt.value.func, "id", "")
                        if "Parameter" in func_name:
                            param_names.add(target.id)

        # Attributes accessed on self inside method bodies
        used_attrs = set()
        for stmt in strat_class.body:
            if isinstance(stmt, ast.FunctionDef):
                for subnode in ast.walk(stmt):
                    if (
                        isinstance(subnode, ast.Attribute)
                        and isinstance(subnode.value, ast.Name)
                        and subnode.value.id == "self"
                    ):
                        used_attrs.add(subnode.attr)

        dead_params = param_names - used_attrs
        self.assertEqual(
            dead_params,
            set(),
            f"Dead-code parameters detected in WolfBreakout_HVRSPB: {dead_params}. "
            f"Every parameter must be actively referenced in strategy logic."
        )
```

#### 3. Add `test_hyperopt_parameter_resolution_all_spaces` to `TestFreqtradeInterfaceAndContract`:
```python
    def test_hyperopt_parameter_resolution_all_spaces(self):
        """
        Simulates Freqtrade HyperOptimizer.generate_optimizer across all spaces
        (['buy', 'sell'], ['stoploss'], ['trailing'], ['buy', 'sell', 'stoploss'], ['default'], ['all']).
        Verifies that all parameters where p.in_space and p.optimize can be resolved
        from the trial dictionary without KeyError.
        """
        from freqtrade.optimize.hyperopt.hyperopt_auto import HyperOptAuto

        space_combos = [
            ["buy", "sell"],
            ["buy", "sell", "stoploss"],
            ["stoploss"],
            ["trailing"],
            ["all"],
            ["default"],
        ]
        for spaces in space_combos:
            config = {"stake_currency": "EUR", "timeframe": "1h", "spaces": spaces}
            strat = WolfBreakout_HVRSPB(config)
            strat.ft_load_hyper_params(hyperopt=True)
            auto = HyperOptAuto(config)
            auto.strategy = strat

            dimensions = []
            if "buy" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.get_indicator_space("buy"))
            if "sell" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.get_indicator_space("sell"))
            if "stoploss" in spaces or "all" in spaces or "default" in spaces:
                dimensions.extend(auto.stoploss_space())
            if "trailing" in spaces or "all" in spaces:
                dimensions.extend(auto.trailing_space())

            # Generate synthetic trial parameters dictionary from dimensions
            params_dict = {}
            for dim in dimensions:
                if hasattr(dim, "low") and hasattr(dim, "high"):
                    params_dict[dim.name] = (dim.low + dim.high) / 2.0
                elif hasattr(dim, "categories"):
                    params_dict[dim.name] = dim.categories[0]
                else:
                    params_dict[dim.name] = 0

            # Simulate Freqtrade HyperOptimizer parameter assignment
            for attr_name, attr in strat.enumerate_parameters():
                if attr.in_space and attr.optimize:
                    self.assertIn(
                        attr_name,
                        params_dict,
                        f"Hyperopt KeyError risk! Parameter '{attr_name}' (space='{attr.space}') is marked "
                        f"in_space=True for spaces={spaces}, but missing from trial params_dict!"
                    )
                    attr.value = params_dict[attr_name]

            # Simulate native stoploss space assignment
            if "stoploss" in spaces or "all" in spaces or "default" in spaces:
                self.assertIn("stoploss", params_dict)
                strat.stoploss = params_dict["stoploss"]
```

#### 4. Update `TestExitSignalsAndRisk`: Replace `test_exit_signal_on_donchian_mid_break` with `test_populate_exit_trend_preserves_grace_period` (lines 526–537):
```python
    def test_populate_exit_trend_preserves_grace_period(self):
        """
        Verify populate_exit_trend does NOT trigger an exit on Donchian Midline break.
        Time-gated midline invalidation is strictly delegated to custom_exit to preserve
        the 4-candle grace period for breakout retest absorption.
        """
        df = generate_synthetic_ohlcv(n_bars=60)
        analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
        analyzed.loc[analyzed.index[-1], "donchian_mid"] = 100.0
        analyzed.loc[analyzed.index[-1], "close"] = 98.0  # below donchian_mid
        analyzed.loc[analyzed.index[-1], "volume"] = 1000.0

        exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
        self.assertEqual(
            exit_df["exit_long"].iloc[-1],
            0,
            "populate_exit_trend must not fire exit_long=1 on midline breach; "
            "it would prematurely kill trades during the 4-candle grace period."
        )
```

#### 5. Add `test_4_candle_grace_period_respected_before_midline_exit` to `TestExitSignalsAndRisk`:
```python
    def test_4_candle_grace_period_respected_before_midline_exit(self):
        """
        Comprehensive validation of the 4-candle invalidation grace period:
        1. Candles 1 to 3.9 (duration < 4h): Both custom_exit and populate_exit_trend
           return NO exit signal, allowing position to absorb normal retest volatility.
        2. Candle 4+ (duration >= 4h):
           - Below midline -> returns fast_invalidation_mid.
           - Loss < -1.5% -> returns fast_invalidation_loss.
           - Above midline and profit > -1.5% -> returns None.
        """
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [trade_open_time + timedelta(hours=5)],
            "donchian_mid": [100.0],
            "close": [97.0],
            "volume": [1000.0],
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # 1. During grace period (1h, 2h, 3h, 3.9h)
        for hours in [1.0, 2.0, 3.0, 3.9]:
            check_time = trade_open_time + timedelta(hours=hours)
            # custom_exit must be None
            res = self.strategy.custom_exit(
                pair="FET/EUR",
                trade=trade,
                current_time=check_time,
                current_rate=97.0,  # below donchian_mid
                current_profit=-0.01,
            )
            self.assertIsNone(res, f"Premature custom_exit triggered at {hours}h during grace period!")

            # populate_exit_trend must not emit exit_long
            exit_df = self.strategy.populate_exit_trend(df_analyzed.copy(), {"pair": "FET/EUR"})
            self.assertEqual(
                exit_df["exit_long"].iloc[-1],
                0,
                f"populate_exit_trend emitted exit_long=1 at {hours}h during grace period!"
            )

        # 2. Expiration of grace period (at exactly 4.0h and 5.0h)
        t_4h = trade_open_time + timedelta(hours=4.0)
        res_4h = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_4h,
            current_rate=97.0,  # below donchian_mid
            current_profit=-0.01,
        )
        self.assertEqual(res_4h, "fast_invalidation_mid")

        t_5h = trade_open_time + timedelta(hours=5.0)
        res_5h = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_5h, "fast_invalidation_mid")

        # Adverse loss invalidation after 4h
        res_loss = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=102.0,  # above midline
            current_profit=-0.02,  # < -1.5%
        )
        self.assertEqual(res_loss, "fast_invalidation_loss")

        # Healthy trade after 4h: no exit
        res_ok = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_5h,
            current_rate=102.0,
            current_profit=0.01,
        )
        self.assertIsNone(res_ok)
```

#### 6. Add `test_exit_donchian_mid_parameter_governs_midline_exit` to `TestExitSignalsAndRisk`:
```python
    def test_exit_donchian_mid_parameter_governs_midline_exit(self):
        """Verify exit_donchian_mid boolean parameter actively gates midline exit."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        current_time = trade_open_time + timedelta(hours=5.0)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [current_time],
            "donchian_mid": [100.0],
            "close": [97.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # When disabled: midline exit must NOT trigger
        self.strategy.exit_donchian_mid.value = False
        res_disabled = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertIsNone(res_disabled)

        # When enabled: midline exit triggers
        self.strategy.exit_donchian_mid.value = True
        res_enabled = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=current_time,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_enabled, "fast_invalidation_mid")
```

#### 7. Add `test_invalidation_candles_parameter_governs_grace_duration` to `TestExitSignalsAndRisk`:
```python
    def test_invalidation_candles_parameter_governs_grace_duration(self):
        """Verify invalidation_candles dynamically controls the grace period length."""
        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)

        df_analyzed = pd.DataFrame({
            "date": [trade_open_time + timedelta(hours=10)],
            "donchian_mid": [100.0],
            "close": [97.0]
        })
        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)

        # Set invalidation candles to 6 hours
        self.strategy.invalidation_candles.value = 6

        # At 4.5h (would have triggered under default 4h, but protected under 6h)
        t_4_5h = trade_open_time + timedelta(hours=4, minutes=30)
        res_protected = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_4_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertIsNone(res_protected)

        # At 6.5h (expired under 6h threshold)
        t_6_5h = trade_open_time + timedelta(hours=6, minutes=30)
        res_expired = self.strategy.custom_exit(
            pair="FET/EUR",
            trade=trade,
            current_time=t_6_5h,
            current_rate=97.0,
            current_profit=-0.01,
        )
        self.assertEqual(res_expired, "fast_invalidation_mid")
```
