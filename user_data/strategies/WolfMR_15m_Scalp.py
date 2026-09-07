from datetime import datetime, timezone
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy import IStrategy

class WolfMR_15m_Scalp(IStrategy):
    """
    15-minute Scalping strategy using Mean Reversion.
    Buys the dip (Oversold RSI + below lower Bollinger Band) during a macro uptrend.
    Aims for rapid 1-3% profits.
    """

    INTERFACE_VERSION = 3
    timeframe = "15m"
    
    # Very tight ROI for scalping: 
    # Take 3% instantly, 2% after 30 mins (2 candles), 1% after 1 hr (4 candles)
    minimal_roi = {
        "0": 0.03,
        "30": 0.02,
        "60": 0.01,
        "120": 0.005 # 0.5% after 2 hours
    }
    
    # 5% stoploss gives the trade room to breathe and bounce
    stoploss = -0.05
    
    # No trailing stop; we rely on the strict ROI ladder to lock in profits.
    trailing_stop = False
    use_custom_stoploss = False
    
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 200

    STALE_EXIT_DAYS = 3 # If it doesn't bounce in 3 days, get out.

    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 4}, # 1 hour cooldown after a trade
    ]

    def informative_pairs(self):
        return [(f"BTC/{self.config['stake_currency']}", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # BTC Macro Uptrend (EMA 200 on 4h timeframe)
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
        # Buy the dip!
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["bb_lowerband"]) & # Price crashed below BB
                (dataframe["rsi"] < 30) &                          # RSI is deeply oversold
                (dataframe["btc_uptrend_4h"] == 1) &               # Overall market is in a bull trend!
                (dataframe["volume"] > 0)
            ),
            ["enter_long", "enter_tag"]
        ] = (1, "buy_the_dip_15m")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Sell if it bounces wildly over the middle band (mean reversion achieved!)
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
        
        # Stale exit (time stoploss)
        if (ct - open_date).days >= self.STALE_EXIT_DAYS:
            return "stale_exit"
            
        return None
