from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfTrend_EMA(IStrategy):
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

    plot_config = {
        "main_plot": {
            # Trend EMAs overlaid on price candles
            "ema20":  {"color": "#2bd4c5"},
            "ema50":  {"color": "#5e8eff"},
            "ema200": {"color": "#ff9d4a"},
        },
        "subplots": {
            "ADX (trend strength)": {
                "adx": {"color": "#a855f7"},
            },
            "Conditions": {
                "ema_cross":    {"color": "#2ad47b"},  # ema20 > ema50 (state)
                "above_trend":  {"color": "#2ad47b"},  # close > ema200
                "adx_ok":       {"color": "#ffb74a"},  # adx > ADX_MIN
            },
        },
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # Binary condition columns — auto-detected as ON/OFF by the dashboard.
        dataframe["ema_cross"]   = (dataframe["ema20"]  > dataframe["ema50"]).astype(int)
        dataframe["above_trend"] = (dataframe["close"]  > dataframe["ema200"]).astype(int)
        dataframe["adx_ok"]      = (dataframe["adx"]    > self.ADX_MIN).astype(int)
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
