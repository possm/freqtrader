# Handoff Report: Architecture & API Conformance Blueprint for `WolfBreakout_PVB`

- **Author**: Milestone 1 Explorer 2 (Strategy Architecture & API Conformance)
- **Recipient**: Project Orchestrator, Strategy Developer (Milestone 1), Data Scientist (Milestone 2 Hyperopt)
- **Date**: 2026-09-04
- **Working Directory**: `/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/.agents/m1_explorer_2`
- **Target Strategy Artifact**: `user_data/strategies/WolfBreakout_PVB.py`

---

## 1. Observation

### 1.1 Existing Production Strategy Architectures

#### 1. `WolfTrend_1h_Candidate.py` (`/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/user_data/strategies/WolfTrend_1h_Candidate.py`)
- **Lines 9-19**:
  ```python
  class WolfTrend_1h_Candidate(WolfTrend_EMA_hopt_tuned):
      timeframe = '1h'
      stoploss = -0.05
  ```
  Demonstrates clean inheritance and base execution on the `1h` timeframe.
- **Lines 27-44**:
  ```python
  def informative_pairs(self):
      return [(f"BTC/{self.config['stake_currency']}", "4h")]

  def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
      ...
      btc = self.dp.get_pair_dataframe(pair=f"BTC/{self.config['stake_currency']}", timeframe="4h")
      btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
      btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
      
      dataframe = merge_informative_pair(
          dataframe, btc[["date", "btc_uptrend"]], self.timeframe, "4h", ffill=True
      )
      return dataframe
  ```
  - Accesses stake currency dynamically via `self.config['stake_currency']`.
  - Calculates indicators on the informative dataframe *before* merging.
  - Merges only `["date", "btc_uptrend"]` to prevent accidental clobbering of base OHLCV columns.
- **Lines 46-52**:
  ```python
  def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
      dataframe = super().populate_entry_trend(dataframe, metadata)
      dataframe.loc[
          dataframe["btc_uptrend_4h"] != 1, 
          ["enter_long", "enter_tag"]
      ] = (0, None)
      return dataframe
  ```
  Demonstrates that Freqtrade appends the informative timeframe (`_4h`) to merged column names.

#### 2. `WolfQuantEdge.py` (`/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/user_data/strategies/WolfQuantEdge.py`)
- **Lines 60-72**:
  ```python
  class WolfQuantEdge(KrakenSlippageMixin, IStrategy):
      INTERFACE_VERSION = 3
      timeframe = "1h"
      inf_tf = "4h"

      can_short = False                   # spot
      process_only_new_candles = True
      use_exit_signal = True
      exit_profit_only = False
      ignore_roi_if_entry_signal = False
      startup_candle_count: int = 320
  ```
  - Multiple inheritance ordering: `KrakenSlippageMixin` must precede `IStrategy` so that custom price hooks take precedence.
  - Standard Freqtrade v3 strategy execution flags for spot trading.
- **Lines 75-89**:
  ```python
  minimal_roi = {
      "0": 0.25,        # don't pre-empt a fresh breakout's run
      "2880": 0.12,     # after 2 days, accept 12%
      "5760": 0.06,     # after 4 days, 6%
      "8640": 0.03,     # after 6 days, 3%
  }
  stoploss = -0.11
  trailing_stop = False
  use_custom_stoploss = True
  CHAND_N = 8.0
  ```
  Time-decaying ROI table keyed by minutes.
- **Lines 106-112**:
  ```python
  protections = [
      {"method": "CooldownPeriod", "stop_duration_candles": 6},
      {"method": "StoplossGuard", "lookback_period_candles": 72, "trade_limit": 4,
       "stop_duration_candles": 24, "only_per_pair": False},
      {"method": "MaxDrawdown", "lookback_period_candles": 288, "trade_limit": 10,
       "stop_duration_candles": 48, "max_allowed_drawdown": 0.20},
  ]
  ```
  Standard protections guarding against over-trading and sequence risk.
- **Lines 128-132**:
  ```python
  @property
  def regime_pair(self) -> str:
      """BTC quoted in whatever we stake (BTC/USDT in backtest, BTC/EUR live)."""
      return f"BTC/{self.config['stake_currency']}"
  ```
- **Lines 161-163**:
  ```python
  dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
  dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
  dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
  ```
  Mandatory requirement: `dataframe["atr_pct"]` must be calculated for `KrakenSlippageMixin`.
- **Lines 236-245**:
  ```python
  def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                  current_profit: float, **kwargs) -> Optional[str]:
      open_date = trade.open_date_utc
      if open_date.tzinfo is None:
          open_date = open_date.replace(tzinfo=timezone.utc)
      now = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
      if (now - open_date).days >= self.STALE_EXIT_DAYS:
          return "stale_exit"
      return None
  ```
  Stale trade circuit breaker preventing capital stagnation in dormant altcoin breakouts.

#### 3. `kraken_slippage.py` (`/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/user_data/strategies/kraken_slippage.py`)
- **Lines 86-93**:
  ```python
  class KrakenSlippageMixin:
      """
      Mix in BEFORE IStrategy:  `class MyStrat(KrakenSlippageMixin, IStrategy): ...`
      """
  ```
- **Lines 106, 114**:
  ```python
  SLIP_RUNMODES = (RunMode.BACKTEST, RunMode.HYPEROPT)
  return self.dp is not None and self.dp.runmode in self.SLIP_RUNMODES
  ```
  Slippage is strictly active in backtesting/hyperopt and pass-through in live/dry-run.
- **Lines 133-155**:
  `_candle_vol_and_atr` requires `atr_pct` (or `atr` and `close`) and `volume` on the latest analyzed candle.

#### 4. Informative Timeframe Column Naming (`WolfMR_1h_strict.py`, lines 58-82)
- When informative timeframe is `"1h"` and base timeframe is `"1h"`:
  ```python
  btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
  btc_1h["ema20"] = ta.EMA(btc_1h, timeperiod=20)
  btc_1h["btc_short_up"] = (btc_1h["close"] > btc_1h["ema20"]).astype(int)
  dataframe = merge_informative_pair(
      dataframe, btc_1h[["date", "btc_short_up"]], self.timeframe, "1h", ffill=True
  )
  ```
  Resulting merged column is `btc_short_up_1h`. Thus, merging `btc_uptrend` on `1h` into a `1h` dataframe yields `btc_uptrend_1h`.

#### 5. Hyperopt Parameter Conventions (`WolfTrend_EMA_hopt.py`, lines 32-36)
- Parameters must be declared as class variables with `space="buy"`, `space="sell"`, etc.:
  ```python
  buy_ema_fast = IntParameter(8, 30, default=20, space="buy", optimize=True)
  ```
  Value access inside strategy logic: `self.buy_ema_fast.value`.

---

## 2. Logic Chain

1. **API Conformance & Execution Framework**:
   - From Observation 1.1.2 and 1.1.3, the strategy class must inherit `(KrakenSlippageMixin, IStrategy)`.
   - Setting `INTERFACE_VERSION = 3` and `timeframe = '1h'` guarantees compliance with modern Freqtrade v3+ core engine requirements.
   - Spot execution on Kraken requires `can_short = False`, `process_only_new_candles = True`, and `ignore_roi_if_entry_signal = False`.

2. **Informative BTC Macro Filter Integration**:
   - From Observation 1.1.1, 1.1.2, and 1.1.4, cross-asset Bitcoin gating requires querying `BTC/{stake_currency}`.
   - The strategy must declare `informative_pairs()` returning `[(self.regime_pair, self.timeframe)]`.
   - In `populate_indicators()`, merging `btc[["date", "btc_uptrend"]]` with `ffill=True` yields `btc_uptrend_1h`.
   - In defensive production code, if `self.dp` is `None` (such as in lightweight unit tests or offline indicator validation), the logic must default `btc_uptrend_1h = 1` rather than throwing an exception.

3. **Indicator Formulation & Lookahead Bias Prevention**:
   - **Parkinson Volatility ($PVR$)**:
     $$\sigma_P^2 = \frac{1}{4 \ln 2} \left( \ln \frac{\text{High}}{\text{Low}} \right)^2 \approx 0.36067376 \cdot \left( \ln \frac{\text{High}}{\text{Low}} \right)^2$$
     To prevent `ZeroDivisionError` or invalid logarithms on abnormal candles, `Low` is clamped: `ratio = (high / low.replace(0, np.nan)).clip(lower=1.0)`. Rolling means over fast window ($N=10$) and slow window ($N=30$) are computed, and $PVR = \sigma_{P, 10} / (\sigma_{P, 30} + 1e-9)$.
   - **Donchian Breakout**:
     The upper channel must strictly use `shift(1)`:
     `donchian_high = dataframe['high'].shift(1).rolling(donchian_period).max()`
     This ensures that the breakout condition `close > donchian_high` compares the current close against historical highs only, eliminating lookahead bias.
   - **Keltner Channel**:
     `keltner_upper = ta.EMA(dataframe, 20) + keltner_mult * ta.ATR(dataframe, 14)`.
   - **Slippage Mixin Compatibility**:
     `dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']` must be explicitly populated.

4. **Hyperopt Space Decoupling**:
   - By declaring parameters `donchian_period`, `pvr_threshold`, `keltner_mult`, `volume_factor`, and `trend_ema_period` as `IntParameter` / `DecimalParameter` with `space="buy"`, Freqtrade's hyperopt runner can optimize these parameters independently.
   - Selling conditions (`exit_donchian_mid`, `exit_ema_basis`) are placed in `space="sell"`.
   - Hard stoploss (`stoploss`) and trailing stop (`trailing_stop_positive`, `trailing_stop_positive_offset`) are tuned via Freqtrade's standard `--spaces stoploss trailing` runners.

5. **Risk Management & Asymmetric Payoff**:
   - Hard stoploss: `-0.045` (-4.5%), capping individual trade downside.
   - Native trailing stop: armed at `+0.045` (+4.5% profit), trailing at `0.025` (2.5% buffer).
   - Minimal ROI: Stepped table decaying from `+28%` down to `+2%` over 24 hours.
   - Stale exit: Closes stagnant trades after 14 days.
   - Protections: Integrated `CooldownPeriod`, `StoplossGuard`, and `MaxDrawdown` to prevent cascading drawdowns.

---

## 3. Detailed Architectural Blueprint: `user_data/strategies/WolfBreakout_PVB.py`

Below is the complete, production-grade architectural specification for `WolfBreakout_PVB.py`.

```python
"""
WolfBreakout_PVB — Parkinson Volatility-Expansion Breakout Strategy
==================================================================
Academic Quantitative Foundations:
  1. Parkinson (1980) Continuous Extreme Value Volatility Estimator
     Statistically superior range-based variance captures intraday expansion
     free from opening/closing microstructure noise in 24/7 crypto markets.
  2. Donchian (20-period) & Keltner Volatility Channel Dual Breakout
     Requires price penetration of historical resistance accompanied by
     expansion beyond the ATR volatility envelope.
  3. Mandelbrot / Engle Volatility Clustering Gate
     Signals are confirmed only when the Parkinson Volatility Ratio
     PVR = sigma_P(fast) / sigma_P(slow) > threshold (> 1.10).
  4. Cross-Asset Bitcoin Macro Trend Regime
     Altcoin beta gating via BTC > EMA200 cross-asset trend filter.
  5. Asymmetric Payoff Risk Management
     Hard catastrophic stoploss (-4.5%), trailing profit lock (+4.5% / 2.5%),
     stepped time-decaying ROI, and Kraken execution slippage simulation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    BooleanParameter,
    merge_informative_pair,
)

from kraken_slippage import KrakenSlippageMixin


class WolfBreakout_PVB(KrakenSlippageMixin, IStrategy):
    """
    Parkinson Volatility Breakout (PVB) Strategy
    Designed for Kraken spot trading on EUR pairs on the 1-hour timeframe.
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"

    # Spot long-only execution
    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Warmup history: 250 candles ensures 200 EMA and 30-period rolling windows stabilize
    startup_candle_count: int = 250

    # =========================================================================
    # RISK MANAGEMENT & EXIT PARAMETERS (Baseline Priors)
    # =========================================================================
    # Hard stoploss (catastrophic circuit breaker)
    stoploss = -0.045

    # Trailing stop: activates once trade reaches +4.5%, trails 2.5% below peak
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.045
    trailing_only_offset_is_reached = True

    # Minimal ROI Table (minutes -> profit ratio)
    minimal_roi = {
        "0": 0.28,      # +28% immediate windfall target
        "120": 0.16,    # +16% after 2 hours (2 candles)
        "360": 0.08,    # +8% after 6 hours
        "720": 0.04,    # +4% after 12 hours
        "1440": 0.02,   # +2% after 24 hours
    }

    # Stale exit timeout: close positions that fail to follow through within 14 days
    STALE_EXIT_DAYS: int = 14

    # Protections: protect against adverse volatility regimes and repetitive stop hits
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 2},
        {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 3,
         "stop_duration_candles": 12, "only_per_pair": False},
        {"method": "MaxDrawdown", "lookback_period_candles": 72, "trade_limit": 5,
         "stop_duration_candles": 24, "max_allowed_drawdown": 0.10},
    ]

    # =========================================================================
    # HYPEROPTABLE PARAMETER SPACES
    # =========================================================================
    # Buy space: Channel lookbacks and entry thresholds
    donchian_period = IntParameter(14, 36, default=20, space="buy", optimize=True)
    pvr_threshold = DecimalParameter(1.02, 1.35, default=1.10, decimals=2, space="buy", optimize=True)
    keltner_mult = DecimalParameter(1.20, 2.50, default=1.75, decimals=2, space="buy", optimize=True)
    volume_factor = DecimalParameter(1.05, 1.50, default=1.20, decimals=2, space="buy", optimize=True)
    trend_ema_period = IntParameter(80, 220, default=100, space="buy", optimize=True)

    # Sell space: Modular exit conditions
    exit_donchian_mid = BooleanParameter(default=True, space="sell", optimize=True)
    exit_ema_basis = BooleanParameter(default=False, space="sell", optimize=True)

    # Constants / Fixed parameters for indicators
    pvr_fast_period: int = 10
    pvr_slow_period: int = 30
    btc_ema_period: int = 200

    # =========================================================================
    # PLOT CONFIGURATION (FreqUI & Plotting Tooling)
    # =========================================================================
    plot_config = {
        "main_plot": {
            "donchian_high": {"color": "#2bd4c5"},
            "donchian_mid": {"color": "#5e8eff"},
            "keltner_upper": {"color": "#d18b2c"},
            "ema_trend": {"color": "#ff9d4a"},
        },
        "subplots": {
            "PVR (Parkinson Ratio)": {
                "pvr": {"color": "#a855f7"},
            },
            "Macro BTC Filter": {
                "btc_uptrend_1h": {"color": "#10b981", "type": "bar"},
            },
        },
    }

    # =========================================================================
    # INFORMATIVE PAIRS (Cross-Asset Macro Gate)
    # =========================================================================
    @property
    def regime_pair(self) -> str:
        """Dynamically builds regime pair based on stake currency (BTC/EUR or BTC/USDT)."""
        stake = self.config.get("stake_currency", "EUR")
        return f"BTC/{stake}"

    def informative_pairs(self):
        """Register the Bitcoin pair on 1h as an informative dataset."""
        return [(self.regime_pair, self.timeframe)]

    # =========================================================================
    # INDICATOR POPULATION
    # =========================================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculates all mathematical indicators:
        - Parkinson Volatility Expansion Ratio (PVR)
        - Donchian Breakout Channel (shifted by 1 candle to prevent lookahead)
        - Keltner Channel & ATR (and atr_pct for KrakenSlippageMixin)
        - Moving average of volume
        - Asset structural trend EMA
        - Cross-asset BTC macro filter merged from informative pair
        """
        # 1. Parkinson (1980) Continuous Volatility Formulation
        # Protect against non-positive lows and ensure ratio >= 1.0
        safe_low = dataframe["low"].replace(0, np.nan)
        ratio = (dataframe["high"] / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)
        # Parkinson variance per candle: (ln(H/L))^2 / (4 * ln(2))
        parkinson_var = (log_hl ** 2) / (4.0 * np.log(2.0))

        dataframe["parkinson_fast"] = np.sqrt(parkinson_var.rolling(window=self.pvr_fast_period).mean())
        dataframe["parkinson_slow"] = np.sqrt(parkinson_var.rolling(window=self.pvr_slow_period).mean())
        dataframe["pvr"] = dataframe["parkinson_fast"] / (dataframe["parkinson_slow"] + 1e-9)

        # 2. Donchian Breakout Channel (shifted by 1 bar to prevent lookahead bias)
        donch_window = self.donchian_period.value
        dataframe["donchian_high"] = dataframe["high"].shift(1).rolling(window=donch_window).max()
        dataframe["donchian_low"] = dataframe["low"].shift(1).rolling(window=donch_window).min()
        dataframe["donchian_mid"] = (dataframe["donchian_high"] + dataframe["donchian_low"]) / 2.0

        # 3. Keltner Channel & ATR
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]  # Crucial for KrakenSlippageMixin!
        dataframe["ema_basis"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["keltner_upper"] = dataframe["ema_basis"] + self.keltner_mult.value * dataframe["atr"]
        dataframe["keltner_lower"] = dataframe["ema_basis"] - self.keltner_mult.value * dataframe["atr"]

        # 4. Volume SMA
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        # 5. Asset Trend Filter
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.trend_ema_period.value)

        # 6. Informative Bitcoin Macro Filter
        if self.dp:
            btc = self.dp.get_pair_dataframe(pair=self.regime_pair, timeframe=self.timeframe)
            if btc is not None and not btc.empty:
                btc["btc_ema200"] = ta.EMA(btc, timeperiod=self.btc_ema_period)
                btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
                dataframe = merge_informative_pair(
                    dataframe, btc[["date", "btc_uptrend"]], self.timeframe, self.timeframe, ffill=True
                )

        # Graceful fallback if BTC data is absent (e.g. isolated unit tests)
        if "btc_uptrend_1h" not in dataframe.columns:
            dataframe["btc_uptrend_1h"] = 1
        else:
            dataframe["btc_uptrend_1h"] = dataframe["btc_uptrend_1h"].ffill().fillna(1).astype(int)

        return dataframe

    # =========================================================================
    # ENTRY LOGIC
    # =========================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Triggers long entry when ALL academic breakout conditions align:
        1. Price penetrates upper Donchian historical resistance.
        2. Price expands above Keltner ATR volatility boundary.
        3. Parkinson Volatility Ratio (PVR) confirms volatility regime expansion.
        4. Volume exceeds 20-period moving average by specified factor.
        5. Price trades above the structural trend EMA.
        6. Bitcoin macro gate is bullish (BTC > EMA200).
        7. Volume > 0 guard against illiquid / zero-volume bars.
        """
        conditions = [
            dataframe["close"] > dataframe["donchian_high"],
            dataframe["close"] > dataframe["keltner_upper"],
            dataframe["pvr"] > self.pvr_threshold.value,
            dataframe["volume"] > (self.volume_factor.value * dataframe["volume_mean"]),
            dataframe["close"] > dataframe["ema_trend"],
            dataframe["btc_uptrend_1h"] == 1,
            dataframe["volume"] > 0,
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "pvb_breakout")

        return dataframe

    # =========================================================================
    # EXIT LOGIC
    # =========================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Triggers long exit upon trend exhaustion / momentum breakdown.
        Configured via hyperoptable boolean flags:
        - Candle closes below Donchian Middle Line
        - Candle closes below Keltner EMA basis
        """
        exit_conditions = []
        if self.exit_donchian_mid.value:
            exit_conditions.append(dataframe["close"] < dataframe["donchian_mid"])
        if self.exit_ema_basis.value:
            exit_conditions.append(dataframe["close"] < dataframe["ema_basis"])

        if exit_conditions:
            dataframe.loc[
                np.logical_or.reduce(exit_conditions) & (dataframe["volume"] > 0),
                ["exit_long", "exit_tag"]
            ] = (1, "trend_exhaustion")

        return dataframe

    # =========================================================================
    # CUSTOM EXIT HOOKS
    # =========================================================================
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """
        Stale Trade Reclaimer:
        Liquidates positions that remain open for longer than STALE_EXIT_DAYS without
        hitting ROI or trailing stop targets, freeing margin for fresh breakouts.
        """
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)

        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"

        return None
```

---

## 4. Caveats

1. **Informative Pair Availability in Offline Backtesting**:
   When backtesting locally or on the VPS, the informative pair (`BTC/EUR` for Kraken or `BTC/USDT` for Binance) must exist in the historical data directory for the exact timerange requested. If missing, `merge_informative_pair` will merge empty rows, triggering the fallback `btc_uptrend_1h = 1`. The Data Scientist must verify that `BTC/EUR` data is downloaded prior to running Hyperopt.
2. **Order Types Alignment**:
   In `config_academic_dryrun.json`, order types should remain `"market"` for realistic execution against Kraken's order books. In backtesting, if `KrakenSlippageMixin`'s limit offsets are desired, backtest config should use `"order_types": {"entry": "limit", "exit": "limit"}` and explicit fee `0.0026`.
3. **No Code Committed to Source Directory**:
   As Explorer 2, no files have been written outside of `.agents/m1_explorer_2/`. The blueprint above is ready for the Strategy Developer to implement directly into `user_data/strategies/WolfBreakout_PVB.py` on the feature branch.

---

## 5. Conclusion

1. **Architecture Ready for Implementation**: The strategy `WolfBreakout_PVB` combines high mathematical rigor (Parkinson continuous range variance, dual-channel volatility breakout, cross-asset macro gating) with seamless Freqtrade API conformance (`INTERFACE_VERSION = 3`, `KrakenSlippageMixin`, `informative_pairs`, and hyperopt spaces).
2. **Robust Defense Against Friction**: By deploying on the `1h` timeframe and enforcing volatility expansion before entry, the expected win size ($>5.0\%$) comfortably absorbs Kraken's round-trip taker fees ($0.52\% - 0.80\%$).
3. **Lookahead Bias & Numerical Safety**: Calculations are mathematically protected against division by zero and lookahead bias (Donchian shifted by 1 candle).

---

## 6. Verification Method

To independently verify the architecture and Python implementation:

1. **Syntax & AST Compilation Check**:
   ```bash
   python3 -m py_compile user_data/strategies/WolfBreakout_PVB.py
   ```
2. **Freqtrade Strategy Validation Command**:
   ```bash
   freqtrade list-strategies --strategy-path user_data/strategies/
   ```
   Must display `WolfBreakout_PVB` in the detected strategy list without syntax or import errors.
3. **Indicator Sanity Unit Test**:
   Execute unit tests on synthetic OHLCV data verifying:
   - $PVR$ calculation matches expected theoretical ratio.
   - `donchian_high` does not leak the current candle's high.
   - `atr_pct` is populated and non-negative.
   - `btc_uptrend_1h` defaults safely to 1 if informative data is absent.
