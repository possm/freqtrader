from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, IntParameter


class WolfTrend_EMA_hopt(IStrategy):
    """
    Hyperopt-able version of WolfTrend_EMA.
    Defaults match the proven baseline (20/50/200 EMA, ADX>20, -12% stop).

    Hyperopt spaces: buy (EMA periods + ADX threshold) + stoploss.
    Leave exit as EMA fast/slow cross (uses same params), and ROI disabled
    (no caps on winners — that's the whole point of trend-following).
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
    startup_candle_count: int = 350   # enough for ema_trend up to 300

    # === Buy hyperopt parameters ===
    buy_ema_fast  = IntParameter(8,  30,  default=20,  space="buy", optimize=True)
    buy_ema_slow  = IntParameter(35, 80,  default=50,  space="buy", optimize=True)
    buy_ema_trend = IntParameter(100, 300, default=200, space="buy", optimize=True)
    buy_adx_min   = IntParameter(15, 35,  default=20,  space="buy", optimize=True)

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"]  = ta.EMA(dataframe, timeperiod=self.buy_ema_fast.value)
        dataframe["ema_slow"]  = ta.EMA(dataframe, timeperiod=self.buy_ema_slow.value)
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.buy_ema_trend.value)
        dataframe["adx"]       = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
        uptrend = dataframe["close"] > dataframe["ema_trend"]
        trending = dataframe["adx"] > self.buy_adx_min.value
        dataframe.loc[
            (cross_up & uptrend & trending & (dataframe["volume"] > 0)),
            ["enter_long", "enter_tag"]
        ] = (1, "ema_hopt")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_down = qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
        dataframe.loc[cross_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_exit")
        return dataframe
