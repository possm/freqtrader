from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMR_4h_btc_cbb25_a3_t15_u(IStrategy):
    """
    baseline bb, earlier arm + tighter trail
    bb_exit=0.025, arm=0.03, trail=0.015, sl=-0.06
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"
    minimal_roi = {"0": 0.08, "1440": 0.04, "4320": 0.02}
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
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

    plot_config = {
        "main_plot": {
            "bb_upperband": {"color": "#a0a0a0"},
            "bb_middleband": {"color": "#5e8eff"},
            "bb_lowerband": {
                "color": "#a0a0a0",
                "fill_to": "bb_upperband",
                "fill_color": "rgba(100,100,255,0.07)",
            },
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "purple"},
            },
            "MFI": {
                "mfi": {"color": "orange"},
            },
            "BTC 4h uptrend filter": {
                "btc_uptrend_4h": {"color": "green", "type": "bar"},
            },
        },
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        # 4h is base timeframe; add BTC as 4h informative too (gets merged so the col exists)
        info = []
        if (self.MARKET_REGIME_PAIR, "4h") not in info:
            info.append((self.MARKET_REGIME_PAIR, "4h"))
        return info

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)

        # BTC 4h trend
        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["ema50"] = ta.EMA(btc_4h, timeperiod=50)
        btc_4h["btc_uptrend"] = (btc_4h["close"] > btc_4h["ema50"]).astype(int)
        # Same-timeframe "merge": just align on date
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_uptrend"]].rename(columns={"btc_uptrend": "btc_uptrend_4h"}),
            on="date", how="left"
        )
        dataframe["btc_uptrend_4h"] = dataframe["btc_uptrend_4h"].ffill().fillna(0).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 30) &
                (dataframe["mfi"] < 30) &
                (dataframe["btc_uptrend_4h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "cbb25_a3_t15")
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
