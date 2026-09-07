from datetime import datetime, timedelta
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy


class WolfMeanReversion_u(IStrategy):
    """
    Pure mean reversion: BB lower + RSI<30 entry, BB middle exit, fast loss cut.

    Entry:
      - Close < lower Bollinger Band (typical price, 20/2)
      - RSI(14) < 30 (oversold)
      - Volume > 0

    Exit:
      - ROI ladder: 3% (instant) / 1.5% (60min) / 1% (120min) — fast take-profit
      - Static stoploss -4%
      - swing_target_reached: rate > BB middle AND profit > 1%
      - winst_is_verlies_timeout: if profit < 0 after 4 candles (1h),
        exit immediately. The "loss is loss" rule — bad timing, cut it fast,
        don't bagholding.

    Key difference vs WolfCustomSwing:
      - Only 2 entry conditions (vs 3-of-4)
      - Aggressive 1h loss timeout (vs -5% hold)
      - No trailing stop — rely on ROI + BB middle exit
      - Faster ROI targets (3% vs 8%)
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"

    # Fast take-profit ladder
    minimal_roi = {"0": 0.03, "60": 0.015, "120": 0.01}

    stoploss = -0.04
    trailing_stop = False  # Pure ROI + custom_exit design

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 50

    # Loss timeout: cut losers after this many 15m candles if still negative
    LOSS_TIMEOUT_CANDLES = 4  # 1 hour

    # BB middle exit: take profit when price returns to the mean
    BB_EXIT_MIN_PROFIT = 0.01  # only exit at BB middle if at least +1% profit

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

    plot_config = {
        "main_plot": {
            "bb_upperband": {"color": "#a0a0a0"},
            "bb_middleband": {"color": "#5e8eff"},
            "bb_lowerband": {"color": "#a0a0a0", "fill_to": "bb_upperband", "fill_color": "rgba(100,100,255,0.08)"},
        },
        "subplots": {
            "RSI": {"rsi": {"color": "purple"}},
        },
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bollinger Bands on typical price (HLC3) — slightly more responsive than close-only
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) &
                (dataframe["rsi"] < 30) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "bb_rsi_oversold")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        """
        Two custom exits:
          1. swing_target_reached — price returned to BB middle and we're profitable
          2. winst_is_verlies_timeout — trade is underwater after 1h, cut it
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()

        # Compute candles elapsed since entry
        elapsed_seconds = (current_time - trade.open_date_utc).total_seconds()
        candles_elapsed = int(elapsed_seconds / (15 * 60))  # 15m candles

        # 1. Take profit at BB middle return
        if current_rate > last_candle["bb_middleband"] and current_profit > self.BB_EXIT_MIN_PROFIT:
            return "swing_target_reached"

        # 2. Loss timeout — bad timing, cut it fast
        if current_profit < 0 and candles_elapsed >= self.LOSS_TIMEOUT_CANDLES:
            return "winst_is_verlies_timeout"

        return None

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):
        """BTC crash filter — block entries during major BTC drawdowns."""
        try:
            btc_df = self.dp.get_pair_dataframe(pair=self.MARKET_REGIME_PAIR, timeframe="1h")
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
