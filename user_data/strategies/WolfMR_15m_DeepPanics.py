from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy

class WolfMR_15m_DeepPanics(IStrategy):
    """
    15-minute Scalping strategy for DEEP Mean Reversion.
    Uses Limit Exits to save Maker Fees and strict entry filters to halve the trade count.
    Aims for ~1 to 2 trades per day across all pairs.
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"
    
    # ROI: 3.5% instantly, 2% after 1 hour, 1% after 2 hours
    minimal_roi = {
        "0": 0.035,
        "60": 0.02,
        "120": 0.01,
        "240": 0.005 # Get out after 4 hours with 0.5% if still lingering
    }
    
    stoploss = -0.05
    trailing_stop = False
    use_custom_stoploss = False
    
    # Enforce Limit Exits to guarantee Maker fees!
    order_types = {
        'entry': 'market',      # Enter fast (Taker fee)
        'exit': 'limit',        # Exit patiently on the bounce (Maker fee)
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 200

    STALE_EXIT_DAYS = 3 

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 8}, # 2 hour cooldown
    ]

    def informative_pairs(self):
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        stake = self.config.get('stake_currency', 'USDT')
        btc_4h = self.dp.get_pair_dataframe(pair=f"BTC/{stake}", timeframe="4h").copy()
        btc_4h["ema200"] = ta.EMA(btc_4h, timeperiod=200)
        btc_4h["btc_uptrend"] = (btc_4h["close"] > btc_4h["ema200"]).astype(int)
        
        dataframe = dataframe.merge(
            btc_4h[["date", "btc_uptrend"]].rename(columns={"btc_uptrend": "btc_uptrend_4h"}),
            on="date", how="left"
        )
        dataframe["btc_uptrend_4h"] = dataframe["btc_uptrend_4h"].ffill().fillna(0).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] < (dataframe["bb_lowerband"] * 0.995)) & # 0.5% DEEPER than the bottom band
                (dataframe["rsi"] < 25) &                                    # RSI extremely oversold
                (dataframe["btc_uptrend_4h"] == 1) &                         # Only dip-buy in bull markets
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "deep_panic_15m")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["bb_middleband"]) &
                (dataframe["volume"] > 0)
            ),
            ["exit_long", "exit_tag"]
        ] = (1, "mean_reverted")
        
        return dataframe

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs) -> Optional[str]:
        open_date = trade.open_date_utc
        if open_date.tzinfo is None:
            open_date = open_date.replace(tzinfo=timezone.utc)
        ct = current_time if current_time.tzinfo else current_time.replace(tzinfo=timezone.utc)
        
        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
            
        return None
