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
        # Protect against non-positive lows and ensure ratio >= 1.0 (clip lower at 1e-8)
        safe_low = dataframe["low"].clip(lower=1e-8)
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
        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = None

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
        dataframe["exit_long"] = 0
        dataframe["exit_tag"] = None

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
