from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMR_1h(IStrategy):
    """
    1-HOUR timeframe mean reversion (vs 15m). 1h signals are more reliable.
    Each candle represents 1 hour of price action so RSI<25 on 1h is far rarer
    and stronger than RSI<25 on 15m.
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"
    minimal_roi = {"0": 0.05, "480": 0.025, "1440": 0.01}  # 0/8h/24h
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 10
    BB_EXIT_MIN_PROFIT = 0.015
    MARKET_REGIME_PAIR = "BTC/EUR"

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 2},
        {"method": "MaxDrawdown", "lookback_period_candles": 168, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.05},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, "4h") for pair in pairs]
        if (self.MARKET_REGIME_PAIR, "4h") not in informative:
            informative.append((self.MARKET_REGIME_PAIR, "4h"))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)

        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["ema50"] = ta.EMA(btc_4h, timeperiod=50)
        btc_4h["btc_uptrend"] = (btc_4h["close"] > btc_4h["ema50"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc_4h[["date", "btc_uptrend"]], self.timeframe, "4h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 25) &
                (dataframe["mfi"] < 25) &
                (dataframe["btc_uptrend_4h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "1h_oversold")
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
