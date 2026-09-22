from datetime import datetime, timezone
from typing import Optional
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy

class WolfSqueeze_Anticipation(IStrategy):
    """
    WolfSqueeze Anticipation Strategy - HYPEROPTED (1000 Epochs)
    Enters on short-term momentum with below-average volatility, 
    and rides the trend extremely long.
    """
    INTERFACE_VERSION = 3
    timeframe = "1d" 
    
    # -------------------------------------------------------------
    # Hyperopted Parameters (ROI, Stoploss, Trailing)
    # -------------------------------------------------------------
    minimal_roi = {
        "0": 1.002,
        "7248": 0.408,
        "23000": 0.127,
        "36240": 0
    }

    stoploss = -0.345

    trailing_stop = True
    trailing_stop_positive = 0.014
    trailing_stop_positive_offset = 0.077
    trailing_only_offset_is_reached = True
    
    # Buy Params
    buy_bb_period = 21
    buy_bbw_factor = 1.029
    buy_ema_period = 20
    
    # Sell Params
    sell_ema_period = 94
    
    # Options
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 150

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Macro trend
        dataframe["macro_trend"] = ta.EMA(dataframe, timeperiod=self.buy_ema_period)
        dataframe["sell_ema_trend"] = ta.EMA(dataframe, timeperiod=self.sell_ema_period)
        
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=self.buy_bb_period, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_lowerband"] = bollinger["lowerband"]
        dataframe["bb_middleband"] = bollinger["middleband"]
        dataframe["bb_upperband"] = bollinger["upperband"]
        
        # Bollinger Band Width (BBW)
        dataframe["bbw"] = (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]
        dataframe["bbw_mean"] = dataframe["bbw"].rolling(self.buy_bb_period).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["close"] > dataframe["macro_trend"]),
            (dataframe["bbw"] < (dataframe["bbw_mean"] * self.buy_bbw_factor)),
            (dataframe["close"] > dataframe["bb_middleband"]),
            (dataframe["close"].shift(1) <= dataframe["bb_middleband"].shift(1)) 
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "squeeze_hyper")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["close"] < dataframe["sell_ema_trend"]),
            (dataframe["close"].shift(1) >= dataframe["sell_ema_trend"].shift(1))
        ]
        
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["exit_long", "exit_tag"]
        ] = (1, "trend_broken")
        return dataframe
