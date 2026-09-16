from datetime import datetime, timezone
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

class WolfBreakout_Variant_Offset(IStrategy):
    """
    Variant 1: Timeframe Offset — HYPEROPTED
    Uses 1h timeframe, only acts at 05:00 UTC (07:00 NL) to avoid midnight volatility spike.
    """
    INTERFACE_VERSION = 3
    timeframe = "1h"

    # Hyperopted parameters
    buy_params = {
        "buy_donchian_period": 15,
        "buy_ema_period": 42,
        "buy_offset_hour": 5,
        "buy_vol_multiplier": 2.252,
    }
    minimal_roi = {
        "0": 0.167,
        "289": 0.079,
        "859": 0.052,
        "2274": 0
    }
    stoploss = -0.259
    trailing_stop = True
    trailing_stop_positive = 0.142
    trailing_stop_positive_offset = 0.175
    trailing_only_offset_is_reached = False

    buy_offset_hour = IntParameter(2, 8, default=5, space="buy", optimize=True)
    buy_donchian_period = IntParameter(10, 25, default=15, space="buy", optimize=True)
    buy_ema_period = IntParameter(20, 60, default=42, space="buy", optimize=True)
    buy_vol_multiplier = DecimalParameter(0.8, 2.5, default=2.252, decimals=3, space="buy", optimize=True)

    startup_candle_count: int = 60 * 24

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for period in range(10, 26):
            dataframe[f"donchian_high_{period}"] = dataframe["high"].rolling(period * 24).max().shift(1)
        for period in range(20, 61):
            dataframe[f"ema_trend_{period}"] = ta.EMA(dataframe, timeperiod=period * 24)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20 * 24).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        donch_col = f"donchian_high_{self.buy_donchian_period.value}"
        ema_col = f"ema_trend_{self.buy_ema_period.value}"
        conditions = [
            (dataframe['date'].dt.hour == self.buy_offset_hour.value),
            (dataframe["close"] > dataframe[donch_col]),
            (dataframe["close"] > dataframe[ema_col]),
            (dataframe["volume"] > (dataframe["volume_mean20"] * self.buy_vol_multiplier.value))
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["enter_long", "enter_tag"]] = (1, "offset_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_col = f"ema_trend_{self.buy_ema_period.value}"
        conditions = [
            (dataframe['date'].dt.hour == self.buy_offset_hour.value),
            (dataframe["close"] < dataframe[ema_col]),
            (dataframe["close"].shift(1) >= dataframe[ema_col].shift(1))
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["exit_long", "exit_tag"]] = (1, "offset_trend_broken")
        return dataframe
