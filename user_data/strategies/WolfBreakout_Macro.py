from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, merge_informative_pair, BooleanParameter


class WolfBreakout_Macro(IStrategy):
    """
    Breakout Strategy with Heavy Macro Filters (Daily Trend + ETH/BTC Dominance)
    """
    INTERFACE_VERSION = 3
    timeframe = "1h" 
    minimal_roi = {"0": 0.05}
    stoploss = -0.04
    trailing_stop = False
    use_custom_stoploss = True
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 7
    ATR_TRAIL_MULTIPLIER = 2.5
    DONCHIAN_PERIOD = 20
    MARKET_REGIME_PAIR = "BTC/USDT"
    ALT_DOM_PAIR = "ETH/BTC"

    # Testing toggles
    use_daily_trend = BooleanParameter(default=True, space="buy", optimize=False)
    use_eth_btc_trend = BooleanParameter(default=False, space="buy", optimize=False)

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, "1d") for pair in pairs] # Daily timeframe for all traded pairs
        if (self.MARKET_REGIME_PAIR, "1h") not in informative:
            informative.append((self.MARKET_REGIME_PAIR, "1h"))
        if (self.ALT_DOM_PAIR, "1d") not in informative:
            informative.append((self.ALT_DOM_PAIR, "1d"))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian
        dataframe["donchian_high"] = dataframe["high"].rolling(self.DONCHIAN_PERIOD).max().shift(1)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # BTC 1h Trend (Original)
        btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
        btc_1h["ema200"] = ta.EMA(btc_1h, timeperiod=200)
        btc_1h["btc_uptrend"] = (btc_1h["close"] > btc_1h["ema200"]).astype(int)
        dataframe = merge_informative_pair(dataframe, btc_1h[["date", "btc_uptrend"]], self.timeframe, "1h", ffill=True)

        # 1. Macro Filter: Specific Pair Daily Trend (Is this specific altcoin actually rising long term?)
        pair_1d = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe="1d").copy()
        pair_1d["ema50"] = ta.EMA(pair_1d, timeperiod=50)
        pair_1d["daily_uptrend"] = (pair_1d["close"] > pair_1d["ema50"]).astype(int)
        dataframe = merge_informative_pair(dataframe, pair_1d[["date", "daily_uptrend"]], self.timeframe, "1d", ffill=True)

        # 2. Macro Filter: ETH/BTC Daily Trend (Are altcoins as a whole gaining against BTC?)
        ethbtc_1d = self.dp.get_pair_dataframe(pair=self.ALT_DOM_PAIR, timeframe="1d").copy()
        ethbtc_1d["ema20"] = ta.EMA(ethbtc_1d, timeperiod=20)
        ethbtc_1d["ethbtc_uptrend"] = (ethbtc_1d["close"] > ethbtc_1d["ema20"]).astype(int)
        dataframe = merge_informative_pair(dataframe, ethbtc_1d[["date", "ethbtc_uptrend"]], self.timeframe, "1d", ffill=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["close"] > dataframe["donchian_high"]),
            (dataframe["btc_uptrend_1h"] == 1),
            (dataframe["volume"] > 0)
        ]

        if self.use_daily_trend.value:
            # Only buy if the specific coin is above its Daily EMA50
            conditions.append(dataframe["daily_uptrend_1d"] == 1)
            
        if self.use_eth_btc_trend.value:
            # Only buy if Altcoins are gaining dominance (ETH/BTC above Daily EMA20)
            conditions.append(dataframe["ethbtc_uptrend_1d"] == 1)

        import numpy as np
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "macro_breakout")
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> Optional[float]:
        if current_profit < 0.02:
            return None
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()
        atr = last_candle["atr"]
        if atr <= 0 or current_rate <= 0:
            return None
        atr_pct = (atr * self.ATR_TRAIL_MULTIPLIER) / current_rate
        trail_stop = current_profit - atr_pct
        return max(trail_stop, -0.04)

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
        return None
