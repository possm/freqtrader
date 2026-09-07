from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend4h(IStrategy):
    """
    Route 2: Higher timeframe trend following.

    4h timeframe, 20/50 EMA cross. Long-only in uptrend.
    Doel: vang multi-day trends in plaats van micro-chop.

    Entry: EMA20 crosses above EMA50 (mini golden cross)
           AND price > EMA50 (confirming)
    Exit: EMA20 crosses below EMA50 (mini death cross)
          OR -10% stoploss
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"

    # Loose ROI — let trends run; main exit is death-cross via custom_exit
    minimal_roi = {"0": 0.20, "1440": 0.15, "2880": 0.10, "7200": 0.05}

    stoploss = -0.10              # Wide — 4h volatility needs room
    trailing_stop = True
    trailing_stop_positive = 0.04
    trailing_stop_positive_offset = 0.08
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False

    startup_candle_count: int = 60   # EMA50 needs ~50 candles warmup

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 2},
    ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)

        dataframe["golden_cross"] = qtpylib.crossed_above(dataframe["ema20"], dataframe["ema50"])
        dataframe["death_cross"]  = qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                dataframe["golden_cross"] &
                (dataframe["close"] > dataframe["ema50"]) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "golden_cross_4h")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            dataframe["death_cross"],
            ["exit_long", "exit_tag"]
        ] = (1, "death_cross_4h")
        return dataframe
