from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy, merge_informative_pair


class WolfMR_stoch(IStrategy):
    """
    Mean reversion with MOMENTUM/STATISTICAL oscillators (no RSI, no BB):
      - Stochastic oscillator: K crossed above D from below 20 (oversold + momentum
        turn — not just a level read, but an actual reversal signal)
      - CCI: measures statistical deviation from typical price; < -100 = oversold
      - VWAP: institutional fair-value anchor; only enter when price is BELOW VWAP
      - BTC 1h EMA200 trend filter (kept — known to work)

    Exit at VWAP (mean reversion back to fair value) rather than BB middle.

    Entry: stoch K cross-up from <20 AND CCI < -100 AND close < VWAP
           AND BTC above 1h EMA200
    Exit:
      - Close above VWAP AND profit > 1%
      - ROI ladder: 3% / 1.5% (120min) / 1% (240min)
      - Hard SL (from config)
      - Stale exit after 5 days
    """

    INTERFACE_VERSION = 3

    timeframe = "15m"

    minimal_roi = {"0": 0.03, "120": 0.015, "240": 0.01}

    stoploss = -0.04
    trailing_stop = False

    use_custom_stoploss = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 250

    STALE_EXIT_DAYS = 5
    VWAP_EXIT_MIN_PROFIT = 0.01

    MARKET_REGIME_PAIR = "BTC/EUR"

    position_adjustment_enable = False

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4},
        {"method": "MaxDrawdown", "lookback_period_candles": 96, "trade_limit": 3,
         "stop_duration_candles": 96, "max_allowed_drawdown": 0.04},
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
        # Stochastic — momentum oversold with cross-up signal
        stoch = ta.STOCH(dataframe, fastk_period=14, slowk_period=3, slowd_period=3)
        dataframe["stoch_k"] = stoch["slowk"]
        dataframe["stoch_d"] = stoch["slowd"]
        dataframe["stoch_cross_up"] = qtpylib.crossed_above(
            dataframe["stoch_k"], dataframe["stoch_d"]
        )

        # CCI — statistical deviation from typical price
        dataframe["cci"] = ta.CCI(dataframe, timeperiod=20)

        # Rolling VWAP — institutional fair value
        dataframe["vwap"] = qtpylib.rolling_vwap(dataframe, window=20)

        # BTC 1h EMA200 trend filter
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
                dataframe["stoch_cross_up"] &
                (dataframe["stoch_k"] < 15) &
                (dataframe["cci"] < -200) &
                (dataframe["close"] < dataframe["vwap"]) &
                (dataframe["btc_uptrend_1h"] == 1) &
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "stoch_cci_vwap")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        age = ct - open_date

        if age.days >= self.STALE_EXIT_DAYS:
            return "stale_exit"

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return None
        last_candle = dataframe.iloc[-1].squeeze()

        if current_rate > last_candle["vwap"] and current_profit > self.VWAP_EXIT_MIN_PROFIT:
            return "vwap_reverted"

        return None
