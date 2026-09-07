from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfStochRSI_4h(IStrategy):
    """
    StochRSI oversold-cross mean reversion. StochRSI is more sensitive than raw
    RSI and its %K/%D crossover gives a timing signal for the turn.

    Entry:
      - StochRSI %K crosses above %D (momentum turning up)
      - both lines were in oversold zone (< 0.20) on the cross
      - price below BB middle (still in the lower half — value zone)
      - BTC 4h uptrend filter ON
    Same exit framework as WolfMR_4h_btc.
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
    MARKET_REGIME_PAIR = "BTC/EUR"

    protections = [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    def informative_pairs(self):
        return [(self.MARKET_REGIME_PAIR, "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        stoch = ta.STOCHRSI(dataframe, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0)
        dataframe["srsi_k"] = stoch["fastk"]
        dataframe["srsi_d"] = stoch["fastd"]

        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["ema50"] = ta.EMA(btc_4h, timeperiod=50)
        btc_4h["btc_uptrend"] = (btc_4h["close"] > btc_4h["ema50"]).astype(int)
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_uptrend"]].rename(columns={"btc_uptrend": "btc_uptrend_4h"}),
            on="date", how="left"
        )
        dataframe["btc_uptrend_4h"] = dataframe["btc_uptrend_4h"].ffill().fillna(0).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross_up = qtpylib.crossed_above(dataframe["srsi_k"], dataframe["srsi_d"])
        oversold = (dataframe["srsi_k"] < 20) & (dataframe["srsi_d"] < 20)
        dataframe.loc[
            (
                cross_up &
                oversold &
                (dataframe["close"] < dataframe["bb_middleband"]) &
                (dataframe["btc_uptrend_4h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "stochrsi")
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
