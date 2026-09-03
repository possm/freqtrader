from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMomentum_strict_pullback_u(IStrategy):
    """
    Momentum variant: Strict + pullback entry
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"
    informative_timeframe = "1h"

    minimal_roi = {"0": 0.12, "60": 0.08, "240": 0.05, "1440": 0.03}

    stoploss = -0.025
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 250

    BREAKOUT_LOOKBACK = 50
    RSI_MIN = 40
    RSI_MAX = 65
    VOLUME_MULT = 1.5
    STALE_EXIT_DAYS = 5

    USE_EMA_ALIGNMENT = True      # Require EMA20 > EMA50 > EMA200 on 1h
    USE_PULLBACK = True                # Wait for pullback after breakout
    PULLBACK_LOOKBACK = 10                       # Look for breakout in last N candles

    MARKET_REGIME_PAIR = "BTC/USDT"
    MARKET_CRASH_CHECKS = [(1, -0.03), (4, -0.05), (24, -0.10)]

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.04},
        {"method": "MaxDrawdown", "lookback_period_candles": 672, "trade_limit": 8,
         "stop_duration_candles": 192, "max_allowed_drawdown": 0.08},
        {"method": "StoplossGuard", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 48, "only_per_pair": False},
    ]

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative = [(pair, self.informative_timeframe) for pair in pairs]
        if (self.MARKET_REGIME_PAIR, self.informative_timeframe) not in informative:
            informative.append((self.MARKET_REGIME_PAIR, self.informative_timeframe))
        return informative

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["recent_high"] = dataframe["high"].rolling(self.BREAKOUT_LOOKBACK).max().shift(1)
        dataframe["volume_avg"] = dataframe["volume"].rolling(self.BREAKOUT_LOOKBACK).mean()

        # Track breakouts for pullback detection
        dataframe["broke_out"] = (dataframe["close"] > dataframe["recent_high"]).astype(int)
        dataframe["recent_breakout"] = dataframe["broke_out"].rolling(self.PULLBACK_LOOKBACK, min_periods=1).max()

        # Pullback level: highest close in breakout window
        dataframe["breakout_level"] = dataframe["close"].where(dataframe["broke_out"] == 1).ffill()

        # 1h trend filter with optional alignment
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=self.informative_timeframe)
        informative["ema20"] = ta.EMA(informative, timeperiod=20)
        informative["ema50"] = ta.EMA(informative, timeperiod=50)
        informative["ema200"] = ta.EMA(informative, timeperiod=200)

        if self.USE_EMA_ALIGNMENT:
            informative["uptrend"] = (
                (informative["close"] > informative["ema20"]) &
                (informative["ema20"] > informative["ema50"]) &
                (informative["ema50"] > informative["ema200"])
            ).astype(int)
        else:
            informative["uptrend"] = (
                (informative["close"] > informative["ema50"]) &
                (informative["ema50"] > informative["ema200"])
            ).astype(int)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        uptrend_col = f"uptrend_{self.informative_timeframe}"

        # Base conditions: trend, RSI healthy, MACD positive, volume
        base_conditions = (
            (dataframe[uptrend_col] == 1) &
            (dataframe["rsi"] > self.RSI_MIN) &
            (dataframe["rsi"] < self.RSI_MAX) &
            (dataframe["macd"] > 0) &
            (dataframe["macd"] > dataframe["macdsignal"]) &
            (dataframe["volume"] > dataframe["volume_avg"] * self.VOLUME_MULT) &
            (dataframe["volume"] > 0)
        )

        if self.USE_PULLBACK:
            # Pullback entry: there was a recent breakout, AND current price pulled back to within 2% of breakout level, AND now bouncing
            entry_condition = (
                base_conditions &
                (dataframe["recent_breakout"] == 1) &
                (dataframe["close"] <= dataframe["breakout_level"] * 1.02) &  # Within 2% of breakout
                (dataframe["close"] > dataframe["close"].shift(1)) &  # Bouncing
                (dataframe["rsi"] < 60)  # Mild pullback (not overheated)
            )
        else:
            # Breakout entry: close > recent high
            entry_condition = base_conditions & (dataframe["close"] > dataframe["recent_high"])

        dataframe.loc[entry_condition, "enter_long"] = 1
        dataframe.loc[entry_condition, "enter_tag"] = "momentum_strict_pullback"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_5d"
        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, current_time, entry_tag, side, **kwargs):
        try:
            btc_df = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe=self.informative_timeframe)
            btc_now = float(btc_df["close"].iloc[-1])
            for hours, threshold in self.MARKET_CRASH_CHECKS:
                needed = hours + 1
                if len(btc_df) < needed:
                    continue
                btc_then = float(btc_df["close"].iloc[-needed])
                if btc_then <= 0:
                    continue
                change = (btc_now / btc_then) - 1.0
                if change < threshold:
                    return False
        except Exception:
            return True
        return True
