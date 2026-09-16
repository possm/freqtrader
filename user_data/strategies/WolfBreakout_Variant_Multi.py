from datetime import datetime, timezone
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.strategy import merge_informative_pair

class WolfBreakout_Variant_Multi(IStrategy):
    """
    Variant 3: Multi-Timeframe — HYPEROPTED
    Uses 1d for macro breakout conditions, triggers entry on 15m RSI dip.
    """
    INTERFACE_VERSION = 3
    timeframe = "15m"
    informative_timeframe = "1d"

    # Hyperopted parameters
    buy_params = {
        "buy_donchian_period": 17,
        "buy_ema_period": 56,
        "buy_rsi_period": 21,
        "buy_rsi_threshold": 39,
        "buy_vol_multiplier": 2.044,
    }
    minimal_roi = {
        "0": 0.327,
        "44": 0.126,
        "78": 0.019,
        "407": 0
    }
    stoploss = -0.276
    trailing_stop = True
    trailing_stop_positive = 0.133
    trailing_stop_positive_offset = 0.208
    trailing_only_offset_is_reached = True

    buy_donchian_period = IntParameter(10, 25, default=17, space="buy", optimize=True)
    buy_ema_period = IntParameter(20, 60, default=56, space="buy", optimize=True)
    buy_vol_multiplier = DecimalParameter(0.8, 2.5, default=2.044, decimals=3, space="buy", optimize=True)
    buy_rsi_threshold = IntParameter(25, 50, default=39, space="buy", optimize=True)
    buy_rsi_period = IntParameter(7, 21, default=21, space="buy", optimize=True)

    startup_candle_count: int = 150

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        inf_tf = self.informative_timeframe
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=inf_tf)
        for period in range(10, 26):
            informative[f"donchian_high_{period}"] = informative["high"].rolling(period).max().shift(1)
        for period in range(20, 61):
            informative[f"ema_trend_{period}"] = ta.EMA(informative, timeperiod=period)
        informative["volume_mean20"] = informative["volume"].rolling(20).mean()
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)
        for period in range(7, 22):
            dataframe[f"rsi_{period}"] = ta.RSI(dataframe, timeperiod=period)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        donch_col = f"donchian_high_{self.buy_donchian_period.value}_1d"
        ema_col = f"ema_trend_{self.buy_ema_period.value}_1d"
        rsi_col = f"rsi_{self.buy_rsi_period.value}"
        conditions = [
            (dataframe["close_1d"] > dataframe[donch_col]),
            (dataframe["close_1d"] > dataframe[ema_col]),
            (dataframe["volume_1d"] > (dataframe["volume_mean20_1d"] * self.buy_vol_multiplier.value)),
            (dataframe[rsi_col] < self.buy_rsi_threshold.value)
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["enter_long", "enter_tag"]] = (1, "multi_tf_dip_entry")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ema_col = f"ema_trend_{self.buy_ema_period.value}_1d"
        conditions = [
            (dataframe["close_1d"] < dataframe[ema_col]),
            (dataframe["close_1d"].shift(1) >= dataframe[ema_col].shift(1))
        ]
        import numpy as np
        dataframe.loc[np.logical_and.reduce(conditions), ["exit_long", "exit_tag"]] = (1, "trend_broken_1d")
        return dataframe
