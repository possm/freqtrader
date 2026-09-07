import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy

class WolfBearTrap(IStrategy):
    """
    WolfBearTrap (Liquidity Sweep)
    Profits from bearish fake-outs. Price pierces a key support level (Donchian Low)
    with high volume, triggering stop-losses of other traders. We buy when the 
    price reclaims the support level (closing back inside), trapping the shorts.
    """
    INTERFACE_VERSION = 3
    timeframe = "15m"  # Lower timeframe is good for spotting traps
    minimal_roi = {"0": 0.04, "60": 0.02, "120": 0.01}
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    startup_candle_count: int = 50

    DONCHIAN_PERIOD = 20

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian Low (Support line)
        dataframe['donchian_low'] = dataframe['low'].rolling(self.DONCHIAN_PERIOD).min().shift(1)
        
        # Volume moving average
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        
        # Bear Trap logic
        # 1. Price pierced the support level during this candle
        dataframe['pierced_low'] = dataframe['low'] < dataframe['donchian_low']
        
        # 2. Rejection: The candle closes back above the support level, trapping shorts
        dataframe['closed_above'] = dataframe['close'] > dataframe['donchian_low']
        
        # 3. High volume implies a liquidity sweep (stop losses hit)
        dataframe['vol_spike'] = dataframe['volume'] > (1.5 * dataframe['volume_mean'])

        # Optional: trend strength
        dataframe['rsi'] = ta.RSI(dataframe, 14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            dataframe['pierced_low'],
            dataframe['closed_above'],
            dataframe['vol_spike'],
            dataframe['rsi'] < 45,  # Needs to happen in a local downtrend
            dataframe['volume'] > 0
        ]

        dataframe.loc[
            np.logical_and.reduce(conditions),
            ['enter_long', 'enter_tag']
        ] = (1, 'bear_trap')

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit if RSI gets too high (momentum exhaustion)
        dataframe.loc[
            (dataframe['rsi'] > 75) & (dataframe['volume'] > 0),
            ['exit_long', 'exit_tag']
        ] = (1, 'rsi_overbought')
        return dataframe
