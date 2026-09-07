from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_hopt_es_80(IStrategy):
    """Perturbation of WolfTrend_EMA_hopt — ema_slow 80 (slower)"""
    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.024
    trailing_stop = False
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 350

    EMA_FAST = 20
    EMA_SLOW = 80
    EMA_TREND = 105
    ADX_MIN = 15

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe, metadata):
        dataframe["ema_fast"]  = ta.EMA(dataframe, timeperiod=self.EMA_FAST)
        dataframe["ema_slow"]  = ta.EMA(dataframe, timeperiod=self.EMA_SLOW)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.EMA_TREND)
        dataframe["adx"]       = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        cross_up = qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
        uptrend = dataframe["close"] > dataframe["ema_trend"]
        trending = dataframe["adx"] > self.ADX_MIN
        dataframe.loc[
            (cross_up & uptrend & trending & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "es_80")
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        cross_down = qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe
