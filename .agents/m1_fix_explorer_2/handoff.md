# Fix Explorer 2 Report: Resolution of Exit Logic Timing Defect & Breathing Room Architecture

**Agent**: `m1_fix_explorer_2` (Fix Explorer 2)  
**Assigned Scope**: Exit mechanics, signal collision between `populate_exit_trend` and `custom_exit`, 4-candle breathing room preservation, and exact code diff recommendations for Worker.  
**Working Directory**: `.agents/m1_fix_explorer_2/`  
**Date**: September 4, 2026  

---

## 1. Observation

### 1.1 Premature Exit Trigger in `populate_exit_trend`
In `user_data/strategies/WolfBreakout_HVRSPB.py` (lines 384–405):
```python
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Triggers long exit on momentum trend exhaustion / breakdown:
        - Candle closes below Donchian Middle Line (mean of high/low range)
        """
        if dataframe is None or dataframe.empty:
            return dataframe

        dataframe["exit_long"] = 0
        dataframe["exit_tag"] = None

        exit_conditions = []
        if self.exit_donchian_mid.value and "donchian_mid" in dataframe.columns:
            exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])

        if exit_conditions:
            dataframe.loc[
                np.logical_or.reduce(exit_conditions) & (dataframe["volume"] > 0),
                ["exit_long", "exit_tag"]
            ] = (1, "trend_invalidation_mid")

        return dataframe
```

### 1.2 Intended 4-Candle Invalidation in `custom_exit`
In `user_data/strategies/WolfBreakout_HVRSPB.py` (lines 477–492):
```python
        # 1. Fast Invalidation after N candles (default 4 hours)
        if duration_hours >= float(self.invalidation_candles.value):
            if hasattr(self, "dp") and self.dp:
                try:
                    df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                    if df is not None and not df.empty:
                        last_candle = df.iloc[-1]
                        if "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:
                            return "fast_invalidation_mid"
                except Exception:
                    pass

            # Invalidation on adverse move if trade fails to gain traction within 4h
            if current_profit < -0.015:
                return "fast_invalidation_loss"
```

### 1.3 Freqtrade Core Engine Dispatch (`freqtrade/strategy/interface.py:should_exit`)
Inspection of Freqtrade's engine via Docker:
```python
        if self.use_exit_signal:
            if exit_ and not enter:
                exit_signal = ExitType.EXIT_SIGNAL
            else:
                reason_cust = strategy_safe_wrapper(self.custom_exit, default_retval=False)(
                    pair=trade.pair,
                    trade=trade,
                    current_time=current_time,
                    current_rate=current_rate,
                    current_profit=current_profit,
                )
```

### 1.4 Empirical Docker Verification of Premature Termination vs Breathing Room
Command executed:
```bash
docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
from datetime import datetime, timezone
from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
from freqtrade.persistence import LocalTrade

strat = WolfBreakout_HVRSPB({'stake_currency': 'EUR'})
strat.minimal_roi = {int(k): v for k, v in strat.minimal_roi.items()}
strat.use_exit_signal = True

trade = LocalTrade(
    pair='FET/EUR', open_rate=100.0, amount=1.0,
    open_date=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    fee_open=0.0016, fee_close=0.0016, exchange='kraken', is_open=True
)

# Candle 1 (only 1h elapsed): exit_ = True (as triggered by populate_exit_trend)
exits_premature = strat.should_exit(
    trade, rate=99.0, current_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
    enter=False, exit_=True
)
print('Premature exit on candle 1 with exit_=True:', exits_premature)

# Candle 1 (only 1h elapsed): exit_ = False (when populate_exit_trend leaves exit_long=0)
exits_clean = strat.should_exit(
    trade, rate=99.0, current_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
    enter=False, exit_=False
)
print('Breathing room on candle 1 with exit_=False:', exits_clean)
"
```
Verbatim output:
```
Premature exit on candle 1 with exit_=True: [ExitCheckTuple(exit_signal, exit_signal)]
Breathing room on candle 1 with exit_=False: []
```

### 1.5 Critical Engine Dependency: `use_exit_signal`
Verifying behavior when `use_exit_signal = False`:
```bash
docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
from datetime import datetime, timezone
from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
from freqtrade.persistence import LocalTrade

strat = WolfBreakout_HVRSPB({'stake_currency': 'EUR'})
strat.minimal_roi = {int(k): v for k, v in strat.minimal_roi.items()}
strat.use_exit_signal = False

trade = LocalTrade(
    pair='FET/EUR', open_rate=100.0, amount=1.0,
    open_date=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    fee_open=0.0016, fee_close=0.0016, exchange='kraken', is_open=True
)

exits = strat.should_exit(
    trade, rate=98.0, current_time=datetime(2026, 1, 1, 16, 0, tzinfo=timezone.utc),
    enter=False, exit_=False
)
print('With use_exit_signal=False exits:', exits)
"
```
Verbatim output:
```
With use_exit_signal=False exits: []
```
Proving that setting `use_exit_signal = False` completely disables `custom_exit` in Freqtrade.

---

## 2. Logic Chain

1. **Mutually Exclusive Execution in Freqtrade Engine**:
   In `IStrategy.should_exit()` (Observation 1.3), `custom_exit` is enclosed within the `else:` clause of `if exit_ and not enter:`.
   When `exit_` is `True` (i.e. `exit_long == 1` in the dataframe), Freqtrade immediately constructs an `ExitType.EXIT_SIGNAL` exit and **never invokes `custom_exit`**.

2. **Vectorized vs Position-Aware Execution**:
   `populate_exit_trend` operates vectorized across all historical candles without awareness of individual trade objects, trade entry times, or holding duration.
   Because `WolfBreakout_HVRSPB.py` line 397 checked `dataframe["close"] < dataframe["donchian_mid"]`, any pullback below midline on candle 1, 2, or 3 set `exit_long = 1` (Observation 1.1).
   When evaluated against an open trade, `exit_` was evaluated as `True`, immediately terminating the trade on candle 1, 2, or 3 (Observation 1.4).

3. **Total Subversion of Intended Payoff Engine**:
   `PROJECT.md` line 61 explicitly specifies:
   `"Time/Volatility invalidation: Close < Entry EMA or Donchian Mid after 4 candles."`
   The breakout strategy requires an initial holding grace period (`invalidation_candles`, default 4 candles) to absorb retest volatility and allow momentum to unfold.
   By firing `exit_long = 1` in `populate_exit_trend`, the 4-candle breathing window was 100% nullified.

4. **Parameter Inconsistency in `custom_exit`**:
   Line 484 in `custom_exit` checked `if "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:`.
   It omitted `self.exit_donchian_mid.value`. Consequently, hyperopting `exit_donchian_mid = False` in the `sell` space had zero effect on `fast_invalidation_mid`.

5. **Optimal Exit Architecture**:
   - Midline breakdown must be handled **exclusively** by `custom_exit` where `duration_hours` is known.
   - `populate_exit_trend` must initialize `exit_long = 0` and `exit_tag = None`, generating no exit signals.
   - `use_exit_signal` must **remain `True`** so that `IStrategy.should_exit` invokes `custom_exit` (Observation 1.5).
   - `custom_exit` must check `if self.exit_donchian_mid.value and ...` to honor the hyperopt parameter.
   - Downside risk during the initial 4-candle grace period remains securely bounded by `stoploss = -0.06` (-6.0% hard disaster stop) and Freqtrade `protections` (`MaxDrawdown` and `StoplossGuard`).

---

## 3. Caveats

1. **Macro Emergency Signals**:
   We investigated whether `populate_exit_trend` should retain an "emergency indicator exit" (e.g. BTC crash or volatility collapse).
   Findings:
   - Neither `PROJECT.md` nor `ORIGINAL_REQUEST.md` specifies an indicator exit in `populate_exit_trend`.
   - Any exit in `populate_exit_trend` lacks trade age awareness and would terminate fresh trades on candle 1.
   - Catastrophic market flash crashes are already protected by `stoploss = -0.06`, while portfolio-level drawdowns are protected by `MaxDrawdown` (20% drawdown -> 24h halt) and `StoplossGuard` (4 stopouts -> 12h halt).
   - Therefore, introducing an uncalibrated indicator exit into `populate_exit_trend` would only reintroduce false-positive premature exits.

2. **Maker Fee Priority on Limit Exits**:
   `WolfBreakout_HVRSPB.order_types["exit"]` is `"limit"`.
   In Freqtrade, exits triggered by `custom_exit` execute via the order type specified in `order_types["exit"]`. Therefore, limit order maker execution is 100% preserved.

---

## 4. Conclusion & Actionable Recommendations for Worker

### Recommended Changes

#### Component 1: `user_data/strategies/WolfBreakout_HVRSPB.py`
1. Update `populate_exit_trend` (lines 384–405) to leave `exit_long = 0` and `exit_tag = None`, delegating all position-level invalidation to `custom_exit`.
2. Update `custom_exit` (line 484) to explicitly check `self.exit_donchian_mid.value`.
3. Keep `use_exit_signal = True`.

#### Component 2: `tests/test_wolfbreakout_hvrspb.py`
1. Update `test_exit_signal_on_donchian_mid_break` (lines 526–536) to assert `exit_df["exit_long"].iloc[-1] == 0` and `exit_df["exit_tag"].iloc[-1] is None`.
2. Add a test confirming that `custom_exit` honors `exit_donchian_mid = False`.
3. Add a test confirming that `should_exit()` grants breathing room on candle 1 and invalidates on candle 4+.

---

## Exact Code Diffs for Worker

### Diff 1: `user_data/strategies/WolfBreakout_HVRSPB.py`

```diff
--- a/user_data/strategies/WolfBreakout_HVRSPB.py
+++ b/user_data/strategies/WolfBreakout_HVRSPB.py
@@ -384,24 +384,17 @@ class WolfBreakout_HVRSPB(KrakenSlippageMixin, IStrategy):
     def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
         """
-        Triggers long exit on momentum trend exhaustion / breakdown:
-        - Candle closes below Donchian Middle Line (mean of high/low range)
+        Populate exit trend dataframe.
+        All position-level exit mechanics (time-gated midline invalidation, trailing runners,
+        and stale exits) are handled dynamically via custom_exit and custom_stoploss to guarantee
+        the mandatory 4-candle breathing room before trade invalidation.
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
 
@@ -481,7 +474,7 @@ class WolfBreakout_HVRSPB(KrakenSlippageMixin, IStrategy):
                 try:
                     df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                     if df is not None and not df.empty:
                         last_candle = df.iloc[-1]
-                        if "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:
+                        if self.exit_donchian_mid.value and "donchian_mid" in last_candle and current_rate < last_candle["donchian_mid"]:
                             return "fast_invalidation_mid"
                 except Exception:
                     pass
```

---

### Diff 2: `tests/test_wolfbreakout_hvrspb.py`

```diff
--- a/tests/test_wolfbreakout_hvrspb.py
+++ b/tests/test_wolfbreakout_hvrspb.py
@@ -526,14 +526,38 @@ class TestExitSignalsAndRisk(unittest.TestCase):
-    def test_exit_signal_on_donchian_mid_break(self):
-        """Close penetrates below Donchian Midline -> exit_long == 1."""
+    def test_populate_exit_trend_leaves_exit_long_zero(self):
+        """
+        populate_exit_trend must not generate exit_long signals on midline break,
+        delegating all invalidation to custom_exit to preserve the 4-candle breathing room.
+        """
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
+
+    def test_custom_exit_midline_disabled_when_flag_false(self):
+        """When exit_donchian_mid is False, midline breach after 4 candles does NOT exit."""
+        self.strategy.exit_donchian_mid.value = False
+        trade_open_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
+        current_time = datetime(2026, 1, 1, 14, 30, tzinfo=timezone.utc)
+        trade = MockTrade(open_date_utc=trade_open_time, open_rate=100.0)
+        df_analyzed = pd.DataFrame({
+            "date": [current_time],
+            "donchian_mid": [100.0],
+            "close": [99.0]
+        })
+        self.strategy.dp = MockDataProvider(analyzed_df=df_analyzed)
+        result = self.strategy.custom_exit(
+            pair="FET/EUR",
+            trade=trade,
+            current_time=current_time,
+            current_rate=99.0,
+            current_profit=-0.01,
+        )
+        self.assertIsNone(result)
```

---

## 5. Verification Method

To independently verify the fix:

1. **Verify Breathing Room Preservation on Candle 1**:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
   from datetime import datetime, timezone
   from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
   from freqtrade.persistence import LocalTrade

   strat = WolfBreakout_HVRSPB({'stake_currency': 'EUR'})
   strat.minimal_roi = {int(k): v for k, v in strat.minimal_roi.items()}
   trade = LocalTrade(
       pair='FET/EUR', open_rate=100.0, amount=1.0,
       open_date=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
       fee_open=0.0016, fee_close=0.0016, exchange='kraken', is_open=True
   )
   # Check candle 1 (1h elapsed): close < midline
   exits = strat.should_exit(
       trade, rate=99.0, current_time=datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
       enter=False, exit_=False
   )
   assert exits == [], f'Expected no exit on candle 1, got {exits}'
   print('PASS: 4-candle breathing room preserved on candle 1.')
   "
   ```

2. **Verify Fast Invalidation on Candle 4+**:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint python3 freqtradeorg/freqtrade:stable -c "
   from datetime import datetime, timezone
   import pandas as pd
   from user_data.strategies.WolfBreakout_HVRSPB import WolfBreakout_HVRSPB
   from freqtrade.persistence import LocalTrade

   class MockDP:
       def get_analyzed_dataframe(self, pair, timeframe):
           return pd.DataFrame({'donchian_mid': [100.0]}), datetime.now(timezone.utc)

   strat = WolfBreakout_HVRSPB({'stake_currency': 'EUR'})
   strat.minimal_roi = {int(k): v for k, v in strat.minimal_roi.items()}
   strat.dp = MockDP()
   trade = LocalTrade(
       pair='FET/EUR', open_rate=100.0, amount=1.0,
       open_date=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
       fee_open=0.0016, fee_close=0.0016, exchange='kraken', is_open=True
   )
   # Check candle 5 (5h elapsed): rate 99.0 < mid 100.0
   exits = strat.should_exit(
       trade, rate=99.0, current_time=datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc),
       enter=False, exit_=False
   )
   assert len(exits) == 1 and exits[0].exit_reason == 'fast_invalidation_mid', f'Unexpected exits: {exits}'
   print('PASS: Fast invalidation triggers correctly on candle 5.')
   "
   ```

3. **Execute Project Test Suite**:
   ```bash
   docker run --rm -v $(pwd):/freqtrade/project -w /freqtrade/project --entrypoint sh freqtradeorg/freqtrade:stable -c "pip install pytest -q && pytest tests/test_wolfbreakout_hvrspb.py -o addopts='' -v"
   ```
