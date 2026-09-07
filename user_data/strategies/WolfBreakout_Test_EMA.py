from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, merge_informative_pair, BooleanParameter


class WolfBreakout_Test_EMA(IStrategy):
    """
    Test Strategy to evaluate different altcoin bleed filters for 2024-2026.
    """
    INTERFACE_VERSION = 3
    timeframe = "1h"  # Using 1h to match typical PVB or breakout
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

    # Testing toggles
    use_alt_ema = BooleanParameter(default=True, space="buy", optimize=False)
    use_vol_conf = BooleanParameter(default=False, space="buy", optimize=False)
    use_adx = BooleanParameter(default=False, space="buy", optimize=False)

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 8},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.06},
        {"method": "StoplossGuard", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 48, "only_per_pair": False},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, "1h") for pair in pairs]
        if (self.MARKET_REGIME_PAIR, "1h") not in informative:
            informative.append((self.MARKET_REGIME_PAIR, "1h"))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Donchian
        dataframe["donchian_high"] = dataframe["high"].rolling(self.DONCHIAN_PERIOD).max().shift(1)
        
        # Test filters
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)

        # BTC Trend
        btc_1h = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h").copy()
        btc_1h["ema200"] = ta.EMA(btc_1h, timeperiod=200)
        btc_1h["btc_uptrend"] = (btc_1h["close"] > btc_1h["ema200"]).astype(int)
        dataframe = merge_informative_pair(
            dataframe, btc_1h[["date", "btc_uptrend"]], self.timeframe, "1h", ffill=True
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = [
            (dataframe["close"] > dataframe["donchian_high"]),
            (dataframe["btc_uptrend_1h"] == 1),
            (dataframe["volume"] > 0)
        ]

        if self.use_alt_ema.value:
            conditions.append(dataframe["close"] > dataframe["ema50"])
            
        if self.use_vol_conf.value:
            conditions.append(dataframe["volume"] > 1.5 * dataframe["volume_mean20"])
            
        if self.use_adx.value:
            conditions.append(dataframe["adx"] > 25)

        import numpy as np
        dataframe.loc[
            np.logical_and.reduce(conditions),
            ["enter_long", "enter_tag"]
        ] = (1, "breakout_test")
        
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
