from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class WolfBreakout_Daily(IStrategy):
    """
    WolfBreakout Daily (Macro) Strategy
    Fully Hyperopted (Buy logic + ROI + Stoploss)
    """
    INTERFACE_VERSION = 3
    timeframe = "1d" 
    
    # -------------------------------------------------------------
    # Hyperopted Parameters (ROI, Stoploss, Trailing)
    # -------------------------------------------------------------
    minimal_roi = {
        "0": 0.297,
        "10151": 0.182, 
        "27171": 0.092, 
        "41954": 0      
    }

    stoploss = -0.293

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.106
    trailing_only_offset_is_reached = True
    
    # -------------------------------------------------------------
    # Hyperopted Buy Parameters
    # -------------------------------------------------------------
    buy_donchian_period = 15
    buy_ema_period = 35
    buy_vol_multiplier = 1.334
    
    # Options
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 150

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian channel for breakout
        dataframe["donchian_high"] = dataframe["high"].rolling(self.buy_donchian_period).max().shift(1)
        
        # Trend indicators
        dataframe["ema_trend"] = ta.EMA(dataframe, timeperiod=self.buy_ema_period)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()

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

        import numpy as np
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "daily_breakout")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit if the coin loses its macro uptrend
        conditions = [
            (dataframe["close"] < dataframe["ema_trend"])
        ]
        import numpy as np
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["exit_long", "exit_tag"]
        ] = (1, "trend_broken")
        return dataframe
