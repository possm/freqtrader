"""
WolfBreakout_HVRSPB — High-Velocity Relative-Strength Parkinson Breakout Strategy
================================================================================
Academic & Quantitative Foundations:
  1. Parkinson (1980) Continuous Extreme Value Volatility Estimator (PVR):
     Measures intraday continuous price variance via high-low price extremes:
       sigma_P^2 = (ln(H/L))^2 / (4 * ln(2))
     The Parkinson Volatility Ratio compares rolling 20-period Parkinson volatility
     against its 20-period EMA to detect explosive volatility expansion (PVR > 1.15).
  2. Cross-Asset Relative Strength Decoupling (RS vs BTC):
     Calculates the rolling 24-hour excess return of the candidate asset against Bitcoin:
       RS_24h = Return_asset(24h) - Return_BTC(24h)
     Filters out market-beta noise, entering only assets demonstrating structural momentum
     leadership (RS > 0.025, i.e., > +2.5% excess return over BTC).
  3. Dual-Channel Volatility Envelope (Donchian + Keltner):
     Requires synchronous piercing of historical resistance (Donchian 20-period high,
     strictly shifted by 1 candle to prevent lookahead bias) and the ATR volatility
     envelope (Keltner 20 EMA + 1.5 ATR).
  4. Institutional Volume Surge (RVOL):
     Ensures institutional capital sponsorship by requiring Volume > Volume_SMA20 * 1.20.
  5. Asymmetric Payoff Risk Engine:
     - Fast invalidation on trend collapse: Liquidates positions if Close < Donchian Mid
       after 4 candles or if momentum reverses.
     - Two-tier asymmetric trailing stop: Locks in breakeven (+0.8%) at +3.5% open profit
       (covering fees + small profit), and activates a trailing runner stop at +8.0%
       (trailing 4.0% behind peak rate to ride fat-tailed multi-day runners).
     - Hard catastrophic stoploss circuit breaker at -6.0% (-0.06).
  6. Maker Fee Capture Architecture:
     Enforces Limit order execution on entry and exit to capture Kraken maker fee rates
     (0.16% maker vs 0.26% taker), saving 0.20% per roundtrip on high-velocity turnover.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import talib.abstract as ta
from pandas import DataFrame, Series

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    BooleanParameter,
    CategoricalParameter,
    merge_informative_pair,
    stoploss_from_open,
)
from freqtrade.optimize.space import SKDecimal

try:
    from kraken_slippage import KrakenSlippageMixin
except ImportError:
    class KrakenSlippageMixin:
        """Fallback empty mixin if kraken_slippage is absent."""
        pass


class WolfBreakout_HVRSPB(KrakenSlippageMixin, IStrategy):
    """
    High-Velocity Relative-Strength Parkinson Breakout (HV-RSPB) Strategy.
    Designed for Kraken Spot trading on 1-hour candles targeting >=10% net profit / month.
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"

    # Spot long-only execution
    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Warmup history: 250 candles ensures 200 EMA, 24h rolling returns, and channels stabilize
    startup_candle_count: int = 250

    # =========================================================================
    # RISK MANAGEMENT & EXIT PARAMETERS
    # =========================================================================
    # Hard catastrophic stoploss (-6.0% disaster floor)
    stoploss = -0.06

    class HyperOpt:
        @staticmethod
        def stoploss_space():
            return [SKDecimal(-0.12, -0.04, decimals=3, name="stoploss")]

    # Custom stoploss engine handles the two-tier asymmetric trailing runner
    use_custom_stoploss = True
    trailing_stop = False

    # Stale exit timeout: close positions that stall without follow-through after 14 days
    STALE_EXIT_DAYS: int = 14

    # Minimal ROI Table (minutes -> profit ratio)
    # Designed as high-alpha runner harvest: allows runners to compound while taking large profits
    minimal_roi = {
        "0": 0.35,
        "120": 0.18,
        "360": 0.10,
        "720": 0.05,
        "1440": 0.02,
    }

    # Order Types: Strict Limit orders for entry and exit to capture maker fees (0.16% vs 0.26%)
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_entry": "limit",
        "force_exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    order_time_in_force = {
        "entry": "GTC",
        "exit": "GTC",
    }

    # Protections: Safeguard capital against adverse volatility regimes and repetitive stop runs
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 2},
        {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 4,
         "stop_duration_candles": 12, "only_per_pair": False},
        {"method": "MaxDrawdown", "lookback_period_candles": 72, "trade_limit": 5,
         "stop_duration_candles": 24, "max_allowed_drawdown": 0.20},
    ]

    # =========================================================================
    # HYPEROPTABLE PARAMETER SPACES
    # =========================================================================
    # Buy Space: Channel periods, volatility ratios, relative strength, and volume confirmation
    donchian_period = IntParameter(14, 40, default=20, space="buy", optimize=True)
    keltner_mult = DecimalParameter(1.0, 2.5, default=1.5, decimals=2, space="buy", optimize=True)
    pvr_threshold = DecimalParameter(1.05, 1.30, default=1.15, decimals=2, space="buy", optimize=True)
    rs_threshold = DecimalParameter(0.010, 0.050, default=0.025, decimals=3, space="buy", optimize=True)
    volume_factor = DecimalParameter(1.0, 2.0, default=1.2, decimals=2, space="buy", optimize=True)
    macro_filter_mode = CategoricalParameter(
        ["none", "btc_trend", "strict"], default="btc_trend", space="buy", optimize=True
    )

    # Sell Space: Fast invalidation and two-tier asymmetric trailing runner
    exit_donchian_mid = BooleanParameter(default=True, space="sell", optimize=True)
    invalidation_candles = IntParameter(2, 8, default=4, space="sell", optimize=True)
    be_profit_threshold = DecimalParameter(0.020, 0.060, default=0.035, decimals=3, space="sell", optimize=True)
    be_lock_margin = DecimalParameter(0.004, 0.015, default=0.008, decimals=3, space="sell", optimize=True)
    trailing_runner_offset = DecimalParameter(0.050, 0.150, default=0.080, decimals=3, space="sell", optimize=True)
    trailing_runner_distance = DecimalParameter(0.020, 0.070, default=0.040, decimals=3, space="sell", optimize=True)

    # Fixed calculation periods
    pvr_period: int = 20
    pvr_ema_period: int = 20
    keltner_period: int = 20
    rs_window: int = 24
    btc_trend_ema: int = 200

    # =========================================================================
    # PLOT CONFIGURATION
    # =========================================================================
    plot_config = {
        "main_plot": {
            "donchian_high": {"color": "#2bd4c5"},
            "donchian_mid": {"color": "#5e8eff"},
            "donchian_low": {"color": "#2bd4c5"},
            "keltner_upper": {"color": "#d18b2c"},
            "keltner_lower": {"color": "#d18b2c"},
        },
        "subplots": {
            "PVR (Parkinson Volatility Ratio)": {
                "pvr": {"color": "#a855f7"},
            },
            "Relative Strength vs BTC": {
                "rs_btc": {"color": "#10b981"},
            },
        },
    }

    # =========================================================================
    # INFORMATIVE PAIRS
    # =========================================================================
    def informative_pairs(self):
        """
        Define informative pairs for Relative Strength benchmarking and macro regime.
        Always monitors both BTC/EUR and BTC/USDT to handle any quote currency.
        """
        return [
            ("BTC/EUR", self.timeframe),
            ("BTC/USDT", self.timeframe),
        ]

    @property
    def regime_pair(self) -> str:
        """Dynamically pick the relevant BTC benchmark pair based on stake_currency."""
        stake = self.config.get("stake_currency", "EUR").upper()
        if stake == "USDT":
            return "BTC/USDT"
        return "BTC/EUR"

    # =========================================================================
    # INDICATOR POPULATION
    # =========================================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculates all mathematical indicators:
        1. Parkinson (1980) Continuous Volatility Ratio (PVR)
        2. Donchian Channel (shifted by 1 bar to strictly prevent lookahead bias)
        3. Keltner Channel & ATR (and atr_pct for KrakenSlippageMixin)
        4. Volume SMA20
        5. Cross-Asset Relative Strength vs BTC (24h excess return)
        6. Macro BTC trend regime filter
        """
        if dataframe is None or dataframe.empty:
            return dataframe

        # Ensure required columns exist
        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(dataframe.columns):
            return dataframe

        # ---------------------------------------------------------------------
        # 1. Parkinson (1980) Continuous Extreme Value Volatility Ratio (PVR)
        # ---------------------------------------------------------------------
        # Protect against non-positive lows/highs and data glitches
        safe_low = dataframe["low"].clip(lower=1e-8)
        safe_high = dataframe["high"].clip(lower=safe_low)
        ratio = (safe_high / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)

        # Parkinson continuous variance per candle: (ln(H/L))^2 / (4 * ln(2))
        parkinson_var = (log_hl ** 2) / (4.0 * np.log(2.0))

        # 20-period continuous volatility estimator
        dataframe["parkinson_20"] = np.sqrt(parkinson_var.rolling(window=self.pvr_period).mean())

        # EMA of Parkinson volatility (20 periods)
        dataframe["parkinson_ema"] = dataframe["parkinson_20"].ewm(span=self.pvr_ema_period, adjust=False).mean()

        # Parkinson Volatility Ratio (PVR): detects transition from coiling to expansion
        dataframe["pvr"] = dataframe["parkinson_20"] / (dataframe["parkinson_ema"] + 1e-9)

        # ---------------------------------------------------------------------
        # 2. Donchian Breakout Channel (Shifted by 1 bar to prevent lookahead)
        # ---------------------------------------------------------------------
        donch_window = int(self.donchian_period.value)
        dataframe["donchian_high"] = dataframe["high"].shift(1).rolling(window=donch_window).max()
        dataframe["donchian_low"] = dataframe["low"].shift(1).rolling(window=donch_window).min()
        dataframe["donchian_mid"] = (dataframe["donchian_high"] + dataframe["donchian_low"]) / 2.0

        # ---------------------------------------------------------------------
        # 3. Keltner Channel & ATR
        # ---------------------------------------------------------------------
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"].clip(lower=1e-8)

        dataframe["keltner_basis"] = ta.EMA(dataframe, timeperiod=self.keltner_period)
        dataframe["keltner_upper"] = dataframe["keltner_basis"] + self.keltner_mult.value * dataframe["atr"]
        dataframe["keltner_lower"] = dataframe["keltner_basis"] - self.keltner_mult.value * dataframe["atr"]

        # ---------------------------------------------------------------------
        # 4. Volume SMA20
        # ---------------------------------------------------------------------
        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        # ---------------------------------------------------------------------
        # 5. Asset 24h Rolling Return
        # ---------------------------------------------------------------------
        shifted_close = dataframe["close"].shift(self.rs_window).clip(lower=1e-8)
        dataframe["asset_return_24h"] = (dataframe["close"] - shifted_close) / shifted_close

        # ---------------------------------------------------------------------
        # 6. Informative BTC Macro & Relative Strength (RS vs BTC)
        # ---------------------------------------------------------------------
        btc_df = None
        if hasattr(self, "dp") and self.dp:
            quote_currency = metadata.get("pair", "").split("/")[-1] if metadata and "pair" in metadata else ""
            candidate_pairs = []
            if quote_currency:
                candidate_pairs.append(f"BTC/{quote_currency}")
            candidate_pairs.extend([self.regime_pair, "BTC/EUR", "BTC/USDT"])

            for candidate in candidate_pairs:
                try:
                    df_candidate = self.dp.get_pair_dataframe(pair=candidate, timeframe=self.timeframe)
                    if df_candidate is not None and not df_candidate.empty:
                        btc_df = df_candidate.copy()
                        break
                except Exception:
                    continue

        if btc_df is not None and not btc_df.empty and "close" in btc_df.columns:
            # Calculate BTC 24h return
            btc_shifted = btc_df["close"].shift(self.rs_window).clip(lower=1e-8)
            btc_df["btc_return_24h"] = (btc_df["close"] - btc_shifted) / btc_shifted
            btc_df["btc_ema200"] = ta.EMA(btc_df, timeperiod=self.btc_trend_ema)
            btc_df["btc_uptrend"] = (btc_df["close"] > btc_df["btc_ema200"]).astype(int)

            # Merge informative fields into main dataframe
            merge_cols = [col for col in ["date", "btc_return_24h", "btc_uptrend"] if col in btc_df.columns]
            if "date" in dataframe.columns and "date" in btc_df.columns:
                dataframe = merge_informative_pair(
                    dataframe, btc_df[merge_cols], self.timeframe, self.timeframe, ffill=True
                )

        # Graceful fallback: benchmark-neutral if BTC informative pair is missing
        # If merged, column will be named 'btc_return_24h_1h' (or 'btc_return_24h')
        btc_ret_col = None
        for col in ["btc_return_24h_1h", "btc_return_24h"]:
            if col in dataframe.columns:
                btc_ret_col = col
                break

        if btc_ret_col is not None:
            dataframe["btc_return_24h_clean"] = dataframe[btc_ret_col].ffill().fillna(0.0)
        else:
            dataframe["btc_return_24h_clean"] = 0.0

        btc_trend_col = None
        for col in ["btc_uptrend_1h", "btc_uptrend"]:
            if col in dataframe.columns:
                btc_trend_col = col
                break

        if btc_trend_col is not None:
            dataframe["btc_uptrend_clean"] = dataframe[btc_trend_col].ffill().fillna(1).astype(int)
        else:
            dataframe["btc_uptrend_clean"] = 1

        # Relative Strength: excess return of asset over BTC over 24h
        dataframe["rs_btc"] = dataframe["asset_return_24h"] - dataframe["btc_return_24h_clean"]
        dataframe["rs_btc"] = dataframe["rs_btc"].fillna(0.0)

        return dataframe

    # =========================================================================
    # ENTRY LOGIC
    # =========================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Triggers long entry when ALL High-Velocity Breakout conditions align:
        1. Price breaks above 20-period Donchian Upper (historical resistance).
        2. Price expands above 20-period Keltner Upper (volatility envelope).
        3. Parkinson Volatility Ratio (PVR) > pvr_threshold (volatility expansion).
        4. Relative Strength vs BTC (rs_btc) > rs_threshold (market alpha leadership).
        5. Volume > Volume SMA20 * volume_factor (institutional capital confirmation).
        6. Macro BTC trend regime check (if enabled).
        7. Volume > 0 guard against illiquid bars.
        """
        if dataframe is None or dataframe.empty:
            return dataframe

        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = None

        conditions = [
            dataframe["close"] > dataframe["donchian_high"],
            dataframe["close"] > dataframe["keltner_upper"],
            dataframe["pvr"] > self.pvr_threshold.value,
            dataframe["rs_btc"] > self.rs_threshold.value,
            dataframe["volume"] > (self.volume_factor.value * dataframe["volume_mean"]),
            dataframe["volume"] > 0,
        ]

        # Macro filter gate
        mode = self.macro_filter_mode.value
        if mode == "btc_trend":
            conditions.append(dataframe["btc_uptrend_clean"] == 1)
        elif mode == "strict":
            conditions.append(dataframe["btc_uptrend_clean"] == 1)
            conditions.append(dataframe["btc_return_24h_clean"] >= -0.02)

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "hvrspb_breakout")

        return dataframe

    # =========================================================================
    # EXIT LOGIC
    # =========================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit trend dataframe.
        All position-level exit mechanics (time-gated midline invalidation, trailing runners,
        and stale exits) are handled dynamically via custom_exit and custom_stoploss to guarantee
        the mandatory 4-candle breathing room before trade invalidation.
        """
        if dataframe is None or dataframe.empty:
            return dataframe

        dataframe["exit_long"] = 0
        dataframe["exit_tag"] = None

        return dataframe

    # =========================================================================
    # CUSTOM STOPLOSS (Asymmetric Two-Tier Trailing Runner)
    # =========================================================================
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool = False,
        **kwargs,
    ) -> Optional[float]:
        """
        Asymmetric Two-Tier Trailing Stop Engine:
        - Tier 1: Breakeven lock (+3.5% profit trigger):
          When open profit reaches +3.5%, ratchets the stoploss to +0.8% above entry,
          locking in exchange fees and eliminating downside risk on developing trades.
        - Tier 2: Trailing runner (+8.0% profit trigger):
          When open profit exceeds +8.0%, trails the market 4.0% behind the peak price,
          allowing fat-tailed altcoin breakout trends to run to +25%..+80%.
        - Default: Hard stoploss (-6.0%) governs initial risk.
        """
        # Tier 2: Runner trailing stop (takes precedence when profit is high)
        if current_profit >= self.trailing_runner_offset.value:
            # Trail by trailing_runner_distance below current rate
            return -float(self.trailing_runner_distance.value)

        # Tier 1: Breakeven profit lock (secures maker fees + small profit)
        if current_profit >= self.be_profit_threshold.value:
            lock_offset = stoploss_from_open(
                float(self.be_lock_margin.value),
                current_profit,
                is_short=trade.is_short,
                leverage=trade.leverage
            )
            return -float(lock_offset)

        # Below breakeven threshold: hard stoploss governs
        return None

    # =========================================================================
    # CUSTOM EXIT (Fast Invalidation & Stale Trade Reclaimer)
    # =========================================================================
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        """
        Dynamic Trade Invalidation & Reclaimer:
        1. Fast Invalidation Cut:
           If trade has been open for >= 4 candles (hours) and price collapses below
           the Donchian Midline or incurs early negative momentum, liquidates immediately
           to prevent deep drawdown on false breakouts.
        2. Stale Trade Reclaimer:
           Liquidates positions open longer than STALE_EXIT_DAYS without hitting targets.
        """
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)

        duration_seconds = (ct - open_date).total_seconds()
        duration_hours = duration_seconds / 3600.0

        # 1. Fast Invalidation after N candles (default 4 hours)
        if duration_hours >= float(self.invalidation_candles.value):
            if hasattr(self, "dp") and self.dp:
                try:
                    df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                    if df is not None and not df.empty:
                        last_candle = df.iloc[-1]
                        if (
                            self.exit_donchian_mid.value
                            and "donchian_mid" in last_candle
                            and current_rate < last_candle["donchian_mid"]
                        ):
                            return "fast_invalidation_mid"
                except Exception:
                    pass

            # Invalidation on adverse move if trade fails to gain traction within 4h
            if current_profit < -0.015:
                return "fast_invalidation_loss"

        # 2. Stale Trade Reclaimer
        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"

        return None
