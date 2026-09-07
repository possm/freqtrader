from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_u(IStrategy):
    """
    EMA-crossover trend following on 4h. EMA20 over EMA50 = uptrend regime,
    confirmed by price > EMA200 and ADX > 20. Ride until EMA20 crosses back
    below EMA50. Let winners run (no ROI cap); wide stop.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 100.0}
    stoploss = -0.12
    trailing_stop = False
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    ADX_MIN = 20

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["ema20"], dataframe["ema50"])
        uptrend = dataframe["close"] > dataframe["ema200"]
        trending = dataframe["adx"] > self.ADX_MIN
        dataframe.loc[
            (cross_up & uptrend & trending & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "ema_cross")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe
