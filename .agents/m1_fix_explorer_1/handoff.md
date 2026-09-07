# Fix Explorer 1 Handoff Report: Hyperopt Parameter Space Architectural Resolution

**Agent**: `m1_fix_explorer_1` (Fix Explorer 1)  
**Assigned Scope**: Milestone 1 Iteration 2 — Fix Analysis for Hyperopt Parameter Spaces & Dead Code in `WolfBreakout_HVRSPB.py`  
**Working Directory**: `.agents/m1_fix_explorer_1/`  
**Date**: September 4, 2026  
**Status**: Investigation Complete — Ready for Worker Implementation  

---

## 1. Observation

### Observation 1: Dead-Code Parameter Facade `hard_stoploss` and Engine Collision
- **Location**: `user_data/strategies/WolfBreakout_HVRSPB.py:145`
  ```python
  hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
  ```
- **Usage Analysis**:
  Grep search for `hard_stoploss` in `user_data/strategies/WolfBreakout_HVRSPB.py`:
  - Line 145 is the only occurrence in the entire strategy file.
  - In `custom_stoploss` (lines 445–446):
    ```python
    # Below breakeven threshold: hard stoploss governs
    return None
    ```
  - When `custom_stoploss` returns `None`, Freqtrade falls back to `self.stoploss = -0.06` (line 83). `self.hard_stoploss.value` is never read anywhere in the code.
- **Engine Crash**:
  Freqtrade HyperOptimizer execution trace (`freqtrade/optimize/hyperopt/hyperopt_optimizer.py:274-276`):
  ```python
  for attr_name, attr in self.backtesting.strategy.enumerate_parameters():
      if attr.in_space and attr.optimize:
          attr.value = params_dict[attr_name]
  ```
  In Freqtrade, `stoploss_space()` creates a single parameter named `"stoploss"` (`freqtrade/optimize/hyperopt/hyperopt_interface.py:101`). When `--spaces stoploss` is activated:
  - `hard_stoploss.in_space` is flagged `True` because `attr.space == "stoploss"`.
  - In `generate_optimizer`, accessing `params_dict['hard_stoploss']` raises:
    ```
    KeyError: 'hard_stoploss'
    ```

### Observation 2: Collision of Custom Trailing Runner Parameters with Reserved `space="trailing"`
- **Location**: `user_data/strategies/WolfBreakout_HVRSPB.py:148-151`
  ```python
  be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="trailing", optimize=True)
  be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="trailing", optimize=True)
  trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="trailing", optimize=True)
  trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="trailing", optimize=True)
  ```
- **Engine Mechanics**:
  - In Freqtrade, `space="trailing"` is strictly reserved for the native trailing stop engine (`IHyperOpt.trailing_space()`), generating dimensions: `['trailing_stop', 'trailing_stop_positive', 'trailing_stop_positive_offset_p1', 'trailing_only_offset_is_reached']`.
  - In `WolfBreakout_HVRSPB.py`, `trailing_stop = False` and `use_custom_stoploss = True`. Trailing is handled entirely inside `custom_stoploss()`.
  - When running `freqtrade hyperopt --spaces trailing` or `--spaces all`:
    All 4 parameters have `in_space = True`.
    In `generate_optimizer`, accessing `params_dict['be_lock_margin']` raises:
    ```
    KeyError: 'be_lock_margin'
    ```
  - When running standard optimization `freqtrade hyperopt --spaces buy sell`:
    Parameters with `space="trailing"` have `in_space = False` and are completely ignored, making the asymmetric trailing runner impossible to optimize.

### Observation 3: Premature Midline Exit Signal vs 4-Candle Invalidation Window
- **Location**: `user_data/strategies/WolfBreakout_HVRSPB.py:396-403` vs `WolfBreakout_HVRSPB.py:478-486`
- **Conflict**:
  - In `populate_exit_trend`:
    ```python
    if self.exit_donchian_mid.value and "donchian_mid" in dataframe.columns:
        exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])
    ```
    Sets `exit_long = 1` immediately on any candle where `close < donchian_mid`.
  - In `custom_exit`:
    ```python
    if duration_hours >= float(self.invalidation_candles.value):
        if hasattr(self, "dp") and self.dp:
            ...
            if "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:
                return "fast_invalidation_mid"
    ```
  - Because `use_exit_signal = True`, a close below `donchian_mid` on candle 1, 2, or 3 terminates the position immediately via `populate_exit_trend`, nullifying the 4-candle breathing window (`invalidation_candles`) specified in `PROJECT.md:61`.

### Observation 4: Verified Freqtrade Space Overriding Mechanism
- Docker inspection of `HyperOptAuto._get_func`:
  ```python
  hyperopt_cls = getattr(self.strategy, "HyperOpt", None)
  default_func = getattr(super(), name)
  if hyperopt_cls:
      return getattr(hyperopt_cls, name, default_func)
  else:
      return default_func
  ```
  Freqtrade natively checks `strategy.HyperOpt.stoploss_space()` when an inner class `HyperOpt` is defined on the strategy class.

---

## 2. Logic Chain

1. *From Observation 1*: `hard_stoploss` is declared as a `DecimalParameter(space="stoploss")`, causing Freqtrade's parameter loader to register it as an active parameter when `stoploss` space is active. But Freqtrade's stoploss hyperspace generator only emits `'stoploss'`, guaranteeing a fatal `KeyError: 'hard_stoploss'`. Furthermore, since `custom_stoploss` returns `None` for initial risk, Freqtrade's engine naturally reads `strategy.stoploss = -0.06`.
2. *From Observation 4*: Defining an inner class `HyperOpt` with `@staticmethod def stoploss_space()` allows configuring exact bounds `[-0.12, -0.04]` for the native `'stoploss'` parameter. During hyperopt, `generate_optimizer` updates `self.backtesting.strategy.stoploss = params_dict["stoploss"]`, which seamlessly controls the catastrophic stoploss in `custom_stoploss` without any dead code or KeyError.
3. *From Observation 2*: In Freqtrade, all custom exit/trailing logic parameters belong in `space="sell"` (as evidenced by `user_data/strategies/WolfCustomSwing_Hyper.py`). Moving `be_profit_threshold`, `be_lock_margin`, `trailing_runner_offset`, and `trailing_runner_distance` to `space="sell"`:
   - Eliminates the crash under `--spaces trailing` (because their space is no longer `"trailing"`).
   - Allows all four parameters to be optimized during `--spaces sell` or `--spaces buy sell`.
   - Populates their values via `params_dict[attr_name]` without KeyError.
4. *From Observation 3*: Centralizing midline breakdown invalidation into `custom_exit` (under `if duration_hours >= float(self.invalidation_candles.value):`) and setting `dataframe["exit_long"] = 0` in `populate_exit_trend` guarantees that trades have the full 4-candle breathing period required by `PROJECT.md` before invalidation can trigger, while still allowing `exit_donchian_mid` to be hyperoptimized in `space="sell"`.

---

## 3. Caveats

- Freqtrade's native `--spaces trailing` CLI option is designed solely for strategies with `trailing_stop = True`. For `WolfBreakout_HVRSPB`, where trailing is dynamically handled by `custom_stoploss`, hyperoptimization should target `--spaces buy sell stoploss` (or `--spaces default` / `--spaces all`).
- When `SKDecimal` is imported from `freqtrade.optimize.space`, it is available across all Freqtrade versions since 2021.

---

## 4. Conclusion & Architectural Recommendation

The parameter spaces and exit architecture must be restructured as follows:

1. **Catastrophic Stoploss Architecture**:
   - Remove `hard_stoploss = DecimalParameter(...)` completely.
   - Retain `stoploss = -0.06` on `WolfBreakout_HVRSPB`.
   - Add inner class `HyperOpt` with `@staticmethod def stoploss_space()` returning `[SKDecimal(-0.12, -0.04, decimals=3, name="stoploss")]`.
   - Freqtrade's hyperopt engine will directly optimize `self.stoploss`, and `custom_stoploss` returning `None` will naturally enforce this value.

2. **Custom Trailing Runner Parameters**:
   - Change `space="trailing"` to `space="sell"` for:
     - `be_profit_threshold`
     - `be_lock_margin`
     - `trailing_runner_offset`
     - `trailing_runner_distance`

3. **Time-Gated Invalidation Harmonization**:
   - In `populate_exit_trend`, remove `close < donchian_mid` to prevent premature exits during the 4-candle breathing window.
   - In `custom_exit`, gate the midline check behind `if self.exit_donchian_mid.value and ...` so `exit_donchian_mid` is fully functional and optimizable.

4. **Test Suite Modernization**:
   - Update `test_hyperopt_spaces_presence` in `tests/test_wolfbreakout_hvrspb.py` to assert `space == "sell"` for custom trailing parameters, verify `stoploss == -0.06`, and check `HyperOpt.stoploss_space()`.
   - Add `test_hyperopt_spaces_execution_no_keyerror` simulating parameter resolution under `['stoploss', 'trailing']` and `['buy', 'sell', 'stoploss']`.

---

## 5. Exact Code Diff Recommendations for Worker

### File 1: `user_data/strategies/WolfBreakout_HVRSPB.py`

```diff
--- a/user_data/strategies/WolfBreakout_HVRSPB.py
+++ b/user_data/strategies/WolfBreakout_HVRSPB.py
@@ -49,6 +49,7 @@
     merge_informative_pair,
     stoploss_from_open,
 )
+from freqtrade.optimize.space import SKDecimal
 
 try:
     from kraken_slippage import KrakenSlippageMixin
@@ -83,6 +84,11 @@
     # Hard catastrophic stoploss (-6.0% disaster floor)
     stoploss = -0.06
 
+    class HyperOpt:
+        @staticmethod
+        def stoploss_space():
+            return [SKDecimal(-0.12, -0.04, decimals=3, name="stoploss")]
+
     # Custom stoploss engine handles the two-tier asymmetric trailing runner
     use_custom_stoploss = True
     trailing_stop = False
@@ -141,14 +147,11 @@
     exit_donchian_mid = BooleanParameter(default=True, space="sell", optimize=True)
     invalidation_candles = IntParameter(2, 8, default=4, space="sell", optimize=True)
 
-    # Stoploss Space: Hard circuit breaker
-    hard_stoploss = DecimalParameter(-0.12, -0.04, default=-0.06, decimals=3, space="stoploss", optimize=True)
-
-    # Trailing Space: Two-Tier Asymmetric Trailing Stop
-    be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="trailing", optimize=True)
-    be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="trailing", optimize=True)
-    trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="trailing", optimize=True)
-    trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="trailing", optimize=True)
+    # Sell Space: Two-Tier Asymmetric Trailing Runner (custom exit logic belongs in sell space)
+    be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="sell", optimize=True)
+    be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="sell", optimize=True)
+    trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="sell", optimize=True)
+    trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="sell", optimize=True)
 
     # Fixed calculation periods
     pvr_period: int = 20
@@ -384,23 +387,17 @@
     def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         """
-        Triggers long exit on momentum trend exhaustion / breakdown:
-        - Candle closes below Donchian Middle Line (mean of high/low range)
+        Exit signals.
+        Time-gated midline invalidation is managed exclusively by custom_exit to respect
+        the 4-candle breathing window (PROJECT.md R1/Exit Logic).
         """
         if dataframe is None or dataframe.empty:
             return dataframe
 
         dataframe["exit_long"] = 0
         dataframe["exit_tag"] = None
-
-        exit_conditions = []
-        if self.exit_donchian_mid.value and "donchian_mid" in dataframe.columns:
-            exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])
-
-        if exit_conditions:
-            dataframe.loc[
-                np.logical_or.reduce(exit_conditions) & (dataframe["volume"] > 0),
-                ["exit_long", "exit_tag"]
-            ] = (1, "trend_invalidation_mid")
 
         return dataframe
@@ -477,7 +474,7 @@
         # 1. Fast Invalidation after N candles (default 4 hours)
         if duration_hours >= float(self.invalidation_candles.value):
-            if hasattr(self, "dp") and self.dp:
+            if self.exit_donchian_mid.value and hasattr(self, "dp") and self.dp:
                 try:
                     df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                     if df is not None and not df.empty:
```

---

### File 2: `tests/test_wolfbreakout_hvrspb.py`

```diff
--- a/tests/test_wolfbreakout_hvrspb.py
+++ b/tests/test_wolfbreakout_hvrspb.py
@@ -525,18 +525,18 @@
 
-    def test_exit_signal_on_donchian_mid_break(self):
-        """Close penetrates below Donchian Midline -> exit_long == 1."""
+    def test_populate_exit_trend_no_premature_signals(self):
+        """populate_exit_trend does not emit premature exits (handled by custom_exit)."""
         df = generate_synthetic_ohlcv(n_bars=60)
         analyzed = self.strategy.populate_indicators(df.copy(), {"pair": "FET/EUR"})
         analyzed.loc[analyzed.index[-1], "donchian_mid"] = 100.0
         analyzed.loc[analyzed.index[-1], "close"] = 98.0  # below donchian_mid
         analyzed.loc[analyzed.index[-1], "volume"] = 1000.0
 
         exit_df = self.strategy.populate_exit_trend(analyzed, {"pair": "FET/EUR"})
-        self.assertEqual(exit_df["exit_long"].iloc[-1], 1)
-        self.assertEqual(exit_df["exit_tag"].iloc[-1], "trend_invalidation_mid")
+        self.assertEqual(exit_df["exit_long"].iloc[-1], 0)
+        self.assertIsNone(exit_df["exit_tag"].iloc[-1])
 
@@ -751,20 +751,48 @@
     def test_hyperopt_spaces_presence(self):
-        """Verify parameters exist across buy, sell, stoploss, and trailing spaces."""
+        """Verify parameters exist across buy and sell spaces, and stoploss space is configured."""
         self.assertEqual(self.strategy.donchian_period.space, "buy")
         self.assertEqual(self.strategy.keltner_mult.space, "buy")
         self.assertEqual(self.strategy.pvr_threshold.space, "buy")
         self.assertEqual(self.strategy.rs_threshold.space, "buy")
         self.assertEqual(self.strategy.volume_factor.space, "buy")
         self.assertEqual(self.strategy.macro_filter_mode.space, "buy")
 
         self.assertEqual(self.strategy.exit_donchian_mid.space, "sell")
         self.assertEqual(self.strategy.invalidation_candles.space, "sell")
 
-        self.assertEqual(self.strategy.hard_stoploss.space, "stoploss")
-
-        self.assertEqual(self.strategy.be_profit_threshold.space, "trailing")
-        self.assertEqual(self.strategy.be_lock_margin.space, "trailing")
-        self.assertEqual(self.strategy.trailing_runner_offset.space, "trailing")
-        self.assertEqual(self.strategy.trailing_runner_distance.space, "trailing")
+        # Custom trailing runner parameters belong in sell space
+        self.assertEqual(self.strategy.be_profit_threshold.space, "sell")
+        self.assertEqual(self.strategy.be_lock_margin.space, "sell")
+        self.assertEqual(self.strategy.trailing_runner_offset.space, "sell")
+        self.assertEqual(self.strategy.trailing_runner_distance.space, "sell")
+
+        # Stoploss space is governed by native Freqtrade stoploss and HyperOpt inner class
+        self.assertEqual(self.strategy.stoploss, -0.06)
+        self.assertTrue(hasattr(self.strategy, "HyperOpt"))
+        sl_space = self.strategy.HyperOpt.stoploss_space()
+        self.assertEqual(len(sl_space), 1)
+        self.assertEqual(sl_space[0].name, "stoploss")
+        self.assertEqual(sl_space[0].low, -0.12)
+        self.assertEqual(sl_space[0].high, -0.04)
+
+    def test_hyperopt_spaces_execution_no_keyerror(self):
+        """Verify Freqtrade _evaluate_epoch parameter resolution completes without KeyError."""
+        # 1. Native stoploss + trailing space
+        strat1 = WolfBreakout_HVRSPB({"stake_currency": "EUR", "spaces": ["stoploss", "trailing"]})
+        strat1.ft_load_hyper_params(hyperopt=True)
+        params_dict1 = {
+            "stoploss": -0.05,
+            "trailing_stop": True,
+            "trailing_stop_positive": 0.02,
+            "trailing_stop_positive_offset_p1": 0.01,
+            "trailing_only_offset_is_reached": False,
+        }
+        for name, p in strat1.enumerate_parameters():
+            if p.in_space and p.optimize:
+                self.assertIn(name, params_dict1)
+
+        # 2. Buy + Sell space
+        strat2 = WolfBreakout_HVRSPB({"stake_currency": "EUR", "spaces": ["buy", "sell"]})
+        strat2.ft_load_hyper_params(hyperopt=True)
+        for name, p in strat2.enumerate_parameters():
+            if p.in_space and p.optimize:
+                self.assertIn(p.space, ["buy", "sell"])
```

---

## 6. Verification Method

To independently verify the proposed architectural fix:

1. **Verify No KeyError in Hyperopt Parameter Iteration**:
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
   print('Stoploss + Trailing space test: SUCCESS')
   "
   ```
   *Expected Output*: `Stoploss + Trailing space test: SUCCESS` (exit code 0, no `KeyError`).

2. **Run Strategy Unit Test Suite**:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_wolfbreakout_hvrspb.py" -v
   ```
   *Expected Output*: Ran 37 tests, OK.

3. **Run Full Repository Regression Suite**:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -m unittest discover -s tests -p "test_*.py" -v
   ```
   *Expected Output*: Ran 151+ tests, OK.
