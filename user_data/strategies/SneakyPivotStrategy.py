# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter, merge_informative_pair)
import talib.abstract as ta
import pandas_ta as pta

class SneakyPivotStrategy(IStrategy):
    """
    Sneaky Pivot Strategy
    Based on identifying previous day's range low tests with a long lower wick (the sneaky candle),
    and entering on the subsequent candle if it breaks the sneaky candle's high.
    Targets the top of the range (previous day's high).
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    INTERFACE_VERSION = 3

    # Timeframe
    timeframe = '15m'
    
    # Informative timeframe for daily range
    informative_timeframe = '1d'

    # Can this strategy go short?
    can_short = False

    # Minimal ROI designed for the strategy.
    minimal_roi = {
        "0": 0.293,
        "51": 0.105,
        "136": 0.018,
        "461": 0
    }

    # Stoploss:
    stoploss = -0.307
    
    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Hyperoptable parameters
    buy_wick_multiplier = DecimalParameter(1.0, 3.0, default=1.74, space="buy", optimize=True)
    buy_range_tolerance = DecimalParameter(0.005, 0.03, default=0.029, space="buy", optimize=True)
    sell_target_modifier = DecimalParameter(0.95, 0.999, default=0.963, space="sell", optimize=True)

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Get daily data for previous day's high/low
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=self.informative_timeframe)
        
        # Shift 1 to ensure we are using the CLOSED daily candle of yesterday
        informative['prev_day_high'] = informative['high'].shift(1)
        informative['prev_day_low'] = informative['low'].shift(1)
        
        # Merge with 15m timeframe
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True)
        
        # Candle shape properties on the 15m timeframe
        dataframe['body_size'] = abs(dataframe['close'] - dataframe['open'])
        dataframe['lower_wick'] = dataframe[['open', 'close']].min(axis=1) - dataframe['low']
        dataframe['upper_wick'] = dataframe['high'] - dataframe[['open', 'close']].max(axis=1)
        dataframe['total_size'] = dataframe['high'] - dataframe['low']
        
        # Avoid division by zero
        dataframe['body_size'] = np.where(dataframe['body_size'] == 0, 0.00001, dataframe['body_size'])

        # Is this candle a 'Sneaky Candle'?
        # 1. Lower wick is noticeably larger than the body
        condition_wick = dataframe['lower_wick'] > (dataframe['body_size'] * self.buy_wick_multiplier.value)
        
        # 2. The low of the candle is testing the previous day's low (within tolerance)
        range_low = dataframe[f'prev_day_low_{self.informative_timeframe}']
        lower_bound = range_low * (1 - self.buy_range_tolerance.value)
        upper_bound = range_low * (1 + self.buy_range_tolerance.value)
        condition_near_bottom = (dataframe['low'] >= lower_bound) & (dataframe['low'] <= upper_bound)
        
        dataframe['is_sneaky_candle'] = condition_wick & condition_near_bottom
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # We enter if the PREVIOUS candle was a sneaky candle, and CURRENT close breaks its high
        
        dataframe.loc[
            (
                (dataframe['is_sneaky_candle'].shift(1) == True) &
                (dataframe['close'] > dataframe['high'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Custom exit: if we reach the previous day's high (range top) on a close basis
        range_high = dataframe[f'prev_day_high_{self.informative_timeframe}']
        target_high = range_high * self.sell_target_modifier.value
        
        dataframe.loc[
            (
                (dataframe['close'] >= target_high) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe

    def custom_exit(self, pair: str, trade: 'Trade', current_time: 'datetime', current_rate: float,
                    current_profit: float, **kwargs):
        # We can also strictly exit if the current price hits the daily high
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        prev_day_high = last_candle[f'prev_day_high_{self.informative_timeframe}']
        target_high = prev_day_high * self.sell_target_modifier.value
        
        if current_rate >= target_high:
            return "reached_range_high"
        
        return None
