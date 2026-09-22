from datetime import datetime, timezone
from typing import Optional
import numpy as np

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy

class WolfBreakout_Daily(IStrategy):
    """
    WolfBreakout Daily (Macro) Strategy - v2 HYPEROPTED
    Beats original strategy with higher profit and lower drawdown.
    """
    INTERFACE_VERSION = 3
    timeframe = "1d" 
    
    # -------------------------------------------------------------
    # Hyperopted Parameters (ROI, Stoploss, Trailing) - NEW WINNING
    # -------------------------------------------------------------
    minimal_roi = {
        "0": 0.253,
        "4973": 0.18,
        "15350": 0.136,
        "46070": 0
    }

    stoploss = -0.024

    trailing_stop = True
    trailing_stop_positive = 0.105
    trailing_stop_positive_offset = 0.187
    trailing_only_offset_is_reached = True
    
    # -------------------------------------------------------------
    # Hyperopted Buy Parameters - NEW WINNING
    # -------------------------------------------------------------
    buy_donchian_period = 10
    buy_ema_period = 40
    buy_vol_multiplier = 1.898
    
    # Options
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 150

    # -------------------------------------------------------------
    # UI Plot Configuration
    # -------------------------------------------------------------
    plot_config = {
        "main_plot": {
            "ema_trend": {"color": "#ffaa00"},
            "target_price": {"color": "#00aaff", "type": "line", "dash": "dash"},
        },
        "subplots": {
            "Volume Metrics": {
                "volume": {"color": "#686868", "type": "bar"},
                "target_volume": {"color": "#ff0000", "type": "line"}
            }
        }
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian channel for breakout
        dataframe["donchian_high"] = dataframe["high"].rolling(self.buy_donchian_period).max().shift(1)
        
        # Trend indicators
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.buy_ema_period)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()

        # Explicit target columns for the Dashboard Signals tab
        dataframe["target_price"] = dataframe["donchian_high"]
        dataframe["target_volume"] = dataframe["volume_mean20"] * self.buy_vol_multiplier

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            # 1. Breakout above the N-day high
            (dataframe["close"] > dataframe["donchian_high"]),
            # 2. Must be in a macro uptrend
            (dataframe["close"] > dataframe["ema_trend"]),
            # 3. Volume must be above average to confirm the breakout
            (dataframe["volume"] > (dataframe["volume_mean20"] * self.buy_vol_multiplier))
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "daily_breakout")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit ONLY on the exact day the coin crosses below the macro uptrend
        conditions = [
            (dataframe["close"] < dataframe["ema_trend"]),
            (dataframe["close"].shift(1) >= dataframe["ema_trend"].shift(1))
        ]
        
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["exit_long", "exit_tag"]
        ] = (1, "trend_broken")
        return dataframe
