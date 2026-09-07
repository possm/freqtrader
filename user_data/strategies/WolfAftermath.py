import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy

class WolfAftermath(IStrategy):
    """
    WolfAftermath (Fake-out Dump Catcher)
    Uses a failed bullish breakout as a leading indicator for a dump.
    When a bullish fake-out occurs (high volume pierce of resistance, but closes below),
    we know altcoin bleed has started. We wait for the panic (RSI crash) and buy the dip.
    """
    INTERFACE_VERSION = 3
    timeframe = "15m" 
    minimal_roi = {"0": 0.05, "120": 0.02, "240": 0.01}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.035
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    startup_candle_count: int = 50

    DONCHIAN_PERIOD = 20

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian High (Resistance line)
        dataframe['donchian_high'] = dataframe['high'].rolling(self.DONCHIAN_PERIOD).max().shift(1)
        
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        
        # Bull Trap (Fake-out) Logic
        # 1. Price pierced the resistance
        # 2. But the candle closed back below it (or very low)
        # 3. On high volume (retail got trapped)
        bull_trap_condition = (
            (dataframe['high'] > dataframe['donchian_high']) &
            (dataframe['close'] < dataframe['donchian_high']) &
            (dataframe['volume'] > 1.5 * dataframe['volume_mean'])
        )
        dataframe['bull_trap'] = bull_trap_condition.astype(int)

        # Has a bull trap occurred in the recent 16 candles (4 hours)?
        dataframe['recent_bull_trap'] = dataframe['bull_trap'].rolling(16).max() == 1

        # RSI to measure the subsequent dump
        dataframe['rsi'] = ta.RSI(dataframe, 14)
        
        # Bollinger Bands for extreme exhaustion
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_lowerband'] = bollinger['lowerband']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # We buy the panic AFTER a fake-out
        conditions = [
            dataframe['recent_bull_trap'],
            # The dump must be severe: RSI below 30 or price piercing lower BB
            ((dataframe['rsi'] < 30) | (dataframe['low'] < dataframe['bb_lowerband'])),
            dataframe['volume'] > 0
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ['enter_long', 'enter_tag']
        ] = (1, 'aftermath_dip')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit on relief bounce
        dataframe.loc[
            (dataframe['rsi'] > 65) & (dataframe['volume'] > 0),
            ['exit_long', 'exit_tag']
        ] = (1, 'relief_bounce')
        return dataframe
