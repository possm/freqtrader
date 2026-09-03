from datetime import datetime
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA_LS(IStrategy):
    """
    Long/SHORT version of the deployed hopt-tuned trend follower.
    Same EMA-cross engine + tuned params (20/71/105, ADX>15, -2.4% stop),
    but SYMMETRIC: shorts the downtrends instead of sitting in cash.

    LONG  entry: ema_fast crosses ABOVE ema_slow, close > ema_trend, ADX>15
    LONG  exit : ema_fast crosses below ema_slow
    SHORT entry: ema_fast crosses BELOW ema_slow, close < ema_trend, ADX>15
    SHORT exit : ema_fast crosses above ema_slow

    Futures mode, leverage 1x (no leverage — isolates the value of shorting).
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = True
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
    EMA_SLOW = 71
    EMA_TREND = 105
    ADX_MIN = 15

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def leverage(self, pair, current_time, current_rate, proposed_leverage,
                 max_leverage, entry_tag, side, **kwargs) -> float:
        return 1.0  # no leverage — fair comparison vs spot long-only

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"]  = ta.EMA(dataframe, timeperiod=self.EMA_FAST)
        dataframe["ema_slow"]  = ta.EMA(dataframe, timeperiod=self.EMA_SLOW)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.EMA_TREND)
        dataframe["adx"]       = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        trending = dataframe["adx"] > self.ADX_MIN
        vol = dataframe["volume"] > 0
        # LONG
        dataframe.loc[
            (qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]) &
             (dataframe["close"] > dataframe["ema_trend"]) & trending & vol),
            ["enter_long", "enter_tag"]
        ] = (1, "ls_long")
        # SHORT
        dataframe.loc[
            (qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]) &
             (dataframe["close"] < dataframe["ema_trend"]) & trending & vol),
            ["enter_short", "enter_tag"]
        ] = (1, "ls_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]),
            ["exit_long", "exit_tag"]
        ] = (1, "x_long")
        dataframe.loc[
            qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]),
            ["exit_short", "exit_tag"]
        ] = (1, "x_short")
        return dataframe
