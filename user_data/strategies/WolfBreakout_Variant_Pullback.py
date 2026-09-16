from datetime import datetime, timezone
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

class WolfBreakout_Variant_Pullback(IStrategy):
    """
    Variant 2: Pullback Entry (Limit Order) — HYPEROPTED
    Detects breakout on 1d, places a limit order X% below the close to catch the pullback dip.
    """
    INTERFACE_VERSION = 3
    timeframe = "1d"

    # Hyperopted parameters
    buy_params = {
        "buy_donchian_period": 16,
        "buy_ema_period": 40,
        "buy_pullback_pct": 0.036,
        "buy_vol_multiplier": 2.273,
    }
    minimal_roi = {
        "0": 0.508,
        "6038": 0.312,
        "21172": 0.056,
        "28797": 0
    }
    stoploss = -0.227
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.092
    trailing_only_offset_is_reached = True

    order_types = {
        'entry': 'limit',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    unfilledtimeout = {'entry': 120, 'exit': 10}

    buy_donchian_period = IntParameter(10, 25, default=16, space="buy", optimize=True)
    buy_ema_period = IntParameter(20, 60, default=40, space="buy", optimize=True)
    buy_vol_multiplier = DecimalParameter(0.8, 2.5, default=2.273, decimals=3, space="buy", optimize=True)
    buy_pullback_pct = DecimalParameter(0.005, 0.04, default=0.036, decimals=3, space="buy", optimize=True)

    process_only_new_candles = True
    startup_candle_count: int = 150

    def custom_entry_price(self, pair: str, current_time: datetime, proposed_rate: float,
                           entry_tag: str, side: str, **kwargs) -> float:
        return proposed_rate * (1 - self.buy_pullback_pct.value)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for period in range(10, 26):
            dataframe[f"donchian_high_{period}"] = dataframe["high"].rolling(period).max().shift(1)
        for period in range(20, 61):
            dataframe[f"ema_trend_{period}"] = ta.EMA(dataframe, timeperiod=period)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        donch_col = f"donchian_high_{self.buy_donchian_period.value}"
        ema_col = f"ema_trend_{self.buy_ema_period.value}"
        conditions = [
            (dataframe["close"] > dataframe[donch_col]),
            (dataframe["close"] > dataframe[ema_col]),
            (dataframe["volume"] > (dataframe["volume_mean20"] * self.buy_vol_multiplier.value))
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["enter_long", "enter_tag"]] = (1, "pullback_limit_bid")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_col = f"ema_trend_{self.buy_ema_period.value}"
        conditions = [
            (dataframe["close"] < dataframe[ema_col]),
            (dataframe["close"].shift(1) >= dataframe[ema_col].shift(1))
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["exit_long", "exit_tag"]] = (1, "trend_broken")
        return dataframe
