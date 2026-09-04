import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy
from WolfTrend_EMA_hopt_tuned_variants import WTE_btc200
from WolfTrend_EMA_hopt_tuned import WolfTrend_EMA_hopt_tuned
import freqtrade.vendor.qtpylib.indicators as qtpylib

class WTE_btc200_2h(WTE_btc200):
    """
    Steps in up to half a candle earlier by checking conditions on a 2h timeframe.
    Indicator periods are doubled to match the exact same real-time lengths as the 4h base.
    """
    timeframe = "2h"
    EMA_FAST = 40       # 20 * 2
    EMA_SLOW = 142      # 71 * 2
    EMA_TREND = 210     # 105 * 2
    
    # We also need a larger startup_candle_count since the max period is 210 here (plus the BTC EMA200 which is 200 on 4h -> 800 on 2h)
    startup_candle_count = 850
    
class WTE_btc200_1h(WTE_btc200):
    """
    Steps in earlier on a 1h timeframe.
    Indicator periods are quadrupled.
    """
    timeframe = "1h"
    EMA_FAST = 80       # 20 * 4
    EMA_SLOW = 284      # 71 * 4
    EMA_TREND = 420     # 105 * 4
    
    startup_candle_count = 1700

class WTE_btc200_15m(WTE_btc200):
    """
    Steps in much earlier on a 15m timeframe.
    Indicator periods are multiplied by 16.
    """
    timeframe = "15m"
    EMA_FAST = 320      # 20 * 16
    EMA_SLOW = 1136     # 71 * 16
    EMA_TREND = 1680    # 105 * 16
    
    startup_candle_count = 4900

# The prompt also asks: "en doe een twee laag met op de gevonden alternatieven met een sl van 5%"
# (and do a second layer on the found alternatives with an sl of 5%)
class WTE_btc200_2h_sl5(WTE_btc200_2h):
    stoploss = -0.05

class WTE_btc200_1h_sl5(WTE_btc200_1h):
    stoploss = -0.05

class WTE_btc200_15m_sl5(WTE_btc200_15m):
    stoploss = -0.05

