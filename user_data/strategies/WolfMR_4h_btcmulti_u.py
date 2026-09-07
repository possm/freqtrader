from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMR_4h_btcmulti_u(IStrategy):
    """
    4h mean reversion + MULTI-TIMEFRAME BTC filter:
    BTC must be above 4h EMA50 AND 1h EMA50.
    Catches BTC weakness on shorter timeframe before 4h reflects it.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 0.08, "1440": 0.04, "4320": 0.02}
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 15
    BB_EXIT_MIN_PROFIT = 0.025
    MARKET_REGIME_PAIR = "BTC/USDT"

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 1},
    ]

    def informative_pairs(self):
        return [
            (self.MARKET_REGIME_PAIR, "4h"),
            (self.MARKET_REGIME_PAIR, "1h"),
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)

        # BTC 4h trend (same TF, just merge)
        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["ema50"] = ta.EMA(btc_4h, timeperiod=50)
        btc_4h["btc_4h_up"] = (btc_4h["close"] > btc_4h["ema50"]).astype(int)
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_4h_up"]],
            on="date", how="left"
        )
        dataframe["btc_4h_up"] = dataframe["btc_4h_up"].ffill().fillna(0).astype(int)

        # BTC 1h trend (higher TF -> 4h via merge_informative_pair)
        btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
        btc_1h["ema50"] = ta.EMA(btc_1h, timeperiod=50)
        btc_1h["btc_1h_up"] = (btc_1h["close"] > btc_1h["ema50"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc_1h[["date", "btc_1h_up"]], self.timeframe, "1h", ffill=True
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 30) &
                (dataframe["mfi"] < 30) &
                (dataframe["btc_4h_up"] == 1) &
                (dataframe["btc_1h_up_1h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "4h_btcmulti")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()
        if current_rate > last_candle["bb_middleband"] and current_profit > self.BB_EXIT_MIN_PROFIT:
            return "bb_middle_reached"
        return None
