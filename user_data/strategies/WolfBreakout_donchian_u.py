from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfBreakout_donchian_u(IStrategy):
    """
    MOMENTUM / breakout strategy — opposite of mean reversion.
    Buy strength, not weakness.

    Entry: Close breaks above 20-period high (Donchian upper)
           AND volume > 1.5x avg
           AND ADX > 25 (strong trend)
           AND BTC above 1h EMA200

    Exit: Trailing stop based on ATR (rides the trend until momentum dies),
          fallback ROI of 5%, hard SL from config, stale 7 days.
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"
    minimal_roi = {"0": 0.05}  # Let winners run further
    stoploss = -0.04
    trailing_stop = False  # We use custom ATR trail
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
        # Donchian Channel — 20-period high/low
        dataframe["donchian_high"] = dataframe["high"].rolling(self.DONCHIAN_PERIOD).max().shift(1)
        dataframe["donchian_low"] = dataframe["low"].rolling(self.DONCHIAN_PERIOD).min().shift(1)

        # ADX for trend strength
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        # ATR for dynamic stops
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # Volume filter
        dataframe["volume_mean20"] = dataframe["volume"].rolling(20).mean()

        # BTC trend filter
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
                (dataframe["close"] > dataframe["donchian_high"]) &
                (dataframe["volume"] > 1.5 * dataframe["volume_mean20"]) &
                (dataframe["adx"] > 25) &
                (dataframe["btc_uptrend_1h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "donchian_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time: datetime, current_rate: float,
                        current_profit: float, **kwargs) -> Optional[float]:
        """ATR-based trailing stop: stop = max_rate - (ATR * multiplier)."""
        if current_profit < 0.02:
            return None  # below 2% profit, use hard SL
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()
        atr = last_candle["atr"]
        if atr <= 0 or current_rate <= 0:
            return None
        # Compute stop as % below current rate
        atr_pct = (atr * self.ATR_TRAIL_MULTIPLIER) / current_rate
        # Stop must be tighter than -4% (hard SL) and respect current profit
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
