from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMomentum_u(IStrategy):
    """
    MOMENTUM STRATEGY — buy STRENGTH, not weakness.

    Philosophy: The reversion-based WolfCustomSwing buys oversold dips.
    This buys breakouts in established uptrends. Designed for trending markets
    where mean-reversion strategies underperform.

    Entry conditions (ALL must be true):
      1. TREND: Close > EMA50 > EMA200 on 1h (clear uptrend)
      2. MOMENTUM: 15m close > 20-candle high (5-hour breakout)
      3. STRENGTH: RSI(14) between 55-72 (rising but not exhausted)
      4. CONFIRMATION: MACD positive AND MACD > MACD signal
      5. VOLUME: Current candle volume > 20-candle average × 1.2

    Exits:
      - TP via minimal_roi ladder (loose for momentum: 12% → 8% → 5%)
      - Hard SL -3% (tight, fakeouts cut quickly)
      - Wider trailing (1.5%) armed at +3% — let winners run
      - Stale-position exit at 5 days (shorter; momentum either works or it doesn't)
      - Cooldown 4 candles after exit (1h)

    Risk management:
      - BTC crash filter (inherited)
      - Standard drawdown protections
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"
    informative_timeframe = "1h"

    # Looser ROI for momentum — let big winners run further
    minimal_roi = {"0": 0.12, "60": 0.08, "240": 0.05, "1440": 0.03}

    stoploss = -0.03                          # Tighter — fakeouts cut quickly
    trailing_stop = True
    trailing_stop_positive = 0.015            # Wide — let winners run
    trailing_stop_positive_offset = 0.03      # Arm later (at +3%)
    trailing_only_offset_is_reached = True

    use_custom_stoploss = False               # Static stoploss only

    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 250

    # Momentum parameters
    BREAKOUT_LOOKBACK = 20                    # 5h breakout (15m × 20)
    RSI_MIN = 55
    RSI_MAX = 72
    VOLUME_MULT = 1.2

    STALE_EXIT_DAYS = 5

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
        # 15m indicators
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]

        # Breakout: highest high in last BREAKOUT_LOOKBACK candles (excluding current)
        dataframe["recent_high"] = dataframe["high"].rolling(self.BREAKOUT_LOOKBACK).max().shift(1)

        # Volume average
        dataframe["volume_avg"] = dataframe["volume"].rolling(self.BREAKOUT_LOOKBACK).mean()

        # 1h trend filter
        informative = self.dp.get_pair_dataframe(
            pair=metadata["pair"], timeframe=self.informative_timeframe
        )
        informative["ema50"] = ta.EMA(informative, timeperiod=50)
        informative["ema200"] = ta.EMA(informative, timeperiod=200)
        informative["uptrend"] = (
            (informative["close"] > informative["ema50"]) &
            (informative["ema50"] > informative["ema200"])
        ).astype(int)

        dataframe = merge_informative_pair(
            dataframe, informative, self.timeframe, self.informative_timeframe, ffill=True,
        )

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        uptrend_col = f"uptrend_{self.informative_timeframe}"

        conditions = (
            # 1. Trend filter: 1h uptrend confirmed
            (dataframe[uptrend_col] == 1) &
            # 2. Momentum: 15m breakout above recent 20-candle high
            (dataframe["close"] > dataframe["recent_high"]) &
            # 3. RSI in healthy momentum zone (rising but not exhausted)
            (dataframe["rsi"] > self.RSI_MIN) &
            (dataframe["rsi"] < self.RSI_MAX) &
            # 4. MACD confirms uptrend
            (dataframe["macd"] > 0) &
            (dataframe["macd"] > dataframe["macdsignal"]) &
            # 5. Volume spike confirms breakout
            (dataframe["volume"] > dataframe["volume_avg"] * self.VOLUME_MULT) &
            # Volume basic
            (dataframe["volume"] > 0)
        )

        dataframe.loc[conditions, "enter_long"] = 1
        dataframe.loc[conditions, "enter_tag"] = "momentum_breakout"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_time - trade.open_date_utc >= timedelta(days=self.STALE_EXIT_DAYS):
            return "stale_5d"
        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        try:
            btc_df = self.dp.get_pair_dataframe(
                pair=self.MARKET_REGIME_PAIR, timeframe=self.informative_timeframe,
            )
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
