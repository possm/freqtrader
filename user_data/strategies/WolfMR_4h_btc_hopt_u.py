from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
)


class WolfMR_4h_btc_hopt_u(IStrategy):
    """
    Hyperopt-able version of WolfMR_4h_btc.
    Defaults match the production strategy (RSI<30, MFI<30, BB stds=2, BTC EMA50).
    Hyperopt spaces: buy / sell / roi / stoploss / trailing.
    """

    INTERFACE_VERSION = 3
    timeframe = "4h"

    # Defaults match production
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
    MARKET_REGIME_PAIR = "BTC/USDT"

    # === Buy hyperopt parameters ===
    buy_rsi = IntParameter(15, 40, default=30, space="buy", optimize=True)
    buy_mfi = IntParameter(15, 40, default=30, space="buy", optimize=True)
    buy_bb_stds = DecimalParameter(1.5, 2.8, default=2.0, decimals=1, space="buy", optimize=True)
    buy_btc_ema = IntParameter(20, 100, default=50, space="buy", optimize=True)

    # === Sell hyperopt parameters ===
    sell_bb_exit_min_profit = DecimalParameter(
        0.005, 0.04, default=0.025, decimals=3, space="sell", optimize=True
    )

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 1},
    ]

    def informative_pairs(self):
        return [(self.MARKET_REGIME_PAIR, "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=self.buy_bb_stds.value
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)

        btc_4h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="4h").copy()
        btc_4h["btc_ema"] = ta.EMA(btc_4h, timeperiod=self.buy_btc_ema.value)
        btc_4h["btc_uptrend"] = (btc_4h["close"] > btc_4h["btc_ema"]).astype(int)
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
                (dataframe["rsi"] < self.buy_rsi.value) &
                (dataframe["mfi"] < self.buy_mfi.value) &
                (dataframe["btc_uptrend_4h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "4h_btc_filter")
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
        if (
            current_rate > last_candle["bb_middleband"]
            and current_profit > self.sell_bb_exit_min_profit.value
        ):
            return "bb_middle_reached"
        return None
