from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMR_swing(IStrategy):
    """
    SWING approach: bigger profit targets, wider stops, longer holds.
    Same selective entry (RSI<20 + MFI<20 + BB lower + BTC uptrend) but:
    - Target 5%+ wins instead of 1.5%
    - Use BB upper as exit signal (not BB middle)
    - Trailing stop locks in at 2.5% gain
    - Wider stop loss (-5%) since bigger targets need more room
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"
    minimal_roi = {"0": 0.08, "480": 0.04, "1440": 0.02}  # 8% / 8h:4% / 24h:2%
    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True
    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 7
    BB_UPPER_EXIT_MIN_PROFIT = 0.025
    MARKET_REGIME_PAIR = "BTC/EUR"

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 8},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.06},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, "1h") for pair in pairs]
        if (self.MARKET_REGIME_PAIR, "1h") not in informative:
            informative.append((self.MARKET_REGIME_PAIR, "1h"))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["mfi"] = ta.MFI(dataframe, timeperiod=14)

        btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
        btc_1h["ema200"] = ta.EMA(btc_1h, timeperiod=200)
        btc_1h["btc_uptrend"] = (btc_1h["close"] > btc_1h["ema200"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc_1h[["date", "btc_uptrend"]], self.timeframe, "1h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 20) &
                (dataframe["mfi"] < 20) &
                (dataframe["btc_uptrend_1h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "swing_oversold")
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
        # Exit at BB upper (overshoot the mean) when profit is meaningful
        if current_rate > last_candle["bb_upperband"] and current_profit > self.BB_UPPER_EXIT_MIN_PROFIT:
            return "bb_upper_reached"
        return None
