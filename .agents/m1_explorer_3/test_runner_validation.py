"""
test_runner_validation.py — Validates that proposed_test_wolfbreakout_pvb.py
passes 100% against the WolfBreakout_PVB implementation designed by Explorer 2.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add strategies directory to sys.path
for p in ["/freqtrade/user_data/strategies", "/Users/matthijsdrenth/IdeaProjects/freqtrade-trend/user_data/strategies"]:
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from datetime import datetime, timezone
from typing import Optional

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
    INTERFACE_VERSION = 3
    timeframe = "1h"

    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    stoploss = -0.045
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.045
    trailing_only_offset_is_reached = True

    minimal_roi = {
        "0": 0.28,
        "120": 0.16,
        "360": 0.08,
        "720": 0.04,
        "1440": 0.02,
    }
    STALE_EXIT_DAYS: int = 14

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 2},
        {"method": "StoplossGuard", "lookback_period_candles": 24, "trade_limit": 3,
         "stop_duration_candles": 12, "only_per_pair": False},
        {"method": "MaxDrawdown", "lookback_period_candles": 72, "trade_limit": 5,
         "stop_duration_candles": 24, "max_allowed_drawdown": 0.10},
    ]

    donchian_period = IntParameter(14, 36, default=20, space="buy", optimize=True)
    pvr_threshold = DecimalParameter(1.02, 1.35, default=1.10, decimals=2, space="buy", optimize=True)
    keltner_mult = DecimalParameter(1.20, 2.50, default=1.75, decimals=2, space="buy", optimize=True)
    volume_factor = DecimalParameter(1.05, 1.50, default=1.20, decimals=2, space="buy", optimize=True)
    trend_ema_period = IntParameter(80, 220, default=100, space="buy", optimize=True)

    exit_donchian_mid = BooleanParameter(default=True, space="sell", optimize=True)
    exit_ema_basis = BooleanParameter(default=False, space="sell", optimize=True)

    pvr_fast_period: int = 10
    pvr_slow_period: int = 30
    btc_ema_period: int = 200

    @property
    def regime_pair(self) -> str:
        stake = self.config.get("stake_currency", "EUR")
        return f"BTC/{stake}"

    def informative_pairs(self):
        return [(self.regime_pair, self.timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        safe_low = dataframe["low"].clip(lower=1e-8)
        ratio = (dataframe["high"] / safe_low).clip(lower=1.0)
        log_hl = np.log(ratio)
        parkinson_var = (log_hl ** 2) / (4.0 * np.log(2.0))

        dataframe["parkinson_fast"] = np.sqrt(parkinson_var.rolling(window=self.pvr_fast_period).mean())
        dataframe["parkinson_slow"] = np.sqrt(parkinson_var.rolling(window=self.pvr_slow_period).mean())
        dataframe["pvr"] = dataframe["parkinson_fast"] / (dataframe["parkinson_slow"] + 1e-9)

        donch_window = self.donchian_period.value
        dataframe["donchian_high"] = dataframe["high"].shift(1).rolling(window=donch_window).max()
        dataframe["donchian_low"] = dataframe["low"].shift(1).rolling(window=donch_window).min()
        dataframe["donchian_mid"] = (dataframe["donchian_high"] + dataframe["donchian_low"]) / 2.0

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["ema_basis"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["keltner_upper"] = dataframe["ema_basis"] + self.keltner_mult.value * dataframe["atr"]
        dataframe["keltner_lower"] = dataframe["ema_basis"] - self.keltner_mult.value * dataframe["atr"]

        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.trend_ema_period.value)

        if self.dp:
            btc = self.dp.get_pair_dataframe(pair=self.regime_pair, timeframe=self.timeframe)
            if btc is not None and not btc.empty:
                btc["btc_ema200"] = ta.EMA(btc, timeperiod=self.btc_ema_period)
                btc["btc_uptrend"] = (btc["close"] > btc["btc_ema200"]).astype(int)
                dataframe = merge_informative_pair(
                    dataframe, btc[["date", "btc_uptrend"]], self.timeframe, self.timeframe, ffill=True
                )

        if "btc_uptrend_1h" not in dataframe.columns:
            dataframe["btc_uptrend_1h"] = 1
        else:
            dataframe["btc_uptrend_1h"] = dataframe["btc_uptrend_1h"].ffill().fillna(1).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
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


    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)

        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
        return None


# Inject into test module
import proposed_test_wolfbreakout_pvb as test_module
test_module.WolfBreakout_PVB = WolfBreakout_PVB

import unittest
suite = unittest.defaultTestLoader.loadTestsFromModule(test_module)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
