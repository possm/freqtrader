import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta, timezone

from freqtrade.strategy import IStrategy, informative
from freqtrade.persistence import PairLocks
import talib.abstract as ta

class MomentumPyramid(IStrategy):
    """
    MomentumPyramid Strategy - Geoptimaliseerd
    Combineert 1m snelle executie met 1h lange termijn trend (smoothing).
    """
    INTERFACE_VERSION = 3
    
    # 1m timeframe voor tick-like rapid evaluation
    timeframe = '5m'
    
    # Max 4999 candles voor Bybit 1m timeframe (Freqtrade limit is 5x exchange API limit)
    # 4999 candles = ~3.4 dagen. (We kunnen daardoor max een 3-day ROC gebruiken).
    startup_candle_count = 4999

    position_adjustment_enable = False
    max_entry_position_adjustment = 0

    minimal_roi = {
        "0": 100.0
    }
    
    stoploss = -0.15

    # Visualisatie instellingen voor FreqUI / Dashboard
    plot_config = {
        'main_plot': {
            'ema_short': {'color': 'orange'},
        },
        'subplots': {
            "ROC 3-Daags (1H)": {
                'roc_3d_1h': {'color': 'blue'},
                'roc_3d_sma_1h': {'color': 'red'}
            },
            "Volume Trend (1H)": {
                'volume_1h': {'color': 'gray'},
                'sma_volume_1h': {'color': 'purple'}
            }
        }
    }

    # --- INFORMATIVE PAIR (1-UUR GRAFIEK) ---
    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 3-daags momentum (72 uur) in plaats van 7-dagen om binnen de 4999 limit te blijven
        dataframe['roc_3d'] = ta.ROC(dataframe, timeperiod=72)
        
        # 1. Smoothed momentum (Voorkomt ruis): 3-uurs gemiddelde van de ROC
        dataframe['roc_3d_sma'] = ta.SMA(dataframe['roc_3d'], timeperiod=3)
        
        # Fading momentum: Smoothed ROC is lager dan het vorige uur
        dataframe['momentum_fading'] = dataframe['roc_3d_sma'] < dataframe['roc_3d_sma'].shift(1)
        
        # 2. Smoothed Volume trend: Volume boven het 24-uurs gemiddelde
        dataframe['sma_volume'] = ta.SMA(dataframe['volume'], timeperiod=24)
        dataframe['volume_rising'] = dataframe['volume'] > dataframe['sma_volume']
        
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Prijs trend op 5m (snel)
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['price_rising'] = dataframe['close'] > dataframe['ema_short']
        
        # Volume breakout
        dataframe['volume_mean_5m'] = ta.SMA(dataframe['volume'], timeperiod=12)
        dataframe['volume_breakout'] = dataframe['volume'] > (dataframe['volume_mean_5m'] * 1.5)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['roc_3d_1h'] > 0) &
                (dataframe['volume_rising_1h'] == True) &
                (dataframe['ema_short'] > dataframe['ema_long']) &
                (dataframe['price_rising'] == True) &
                (dataframe['volume_breakout'] == True)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        """ Waterval kruisanalyse: Pak alleen de sterkste munt, tenzij al in bezit. Maximaal afzakken tot #3. """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or len(dataframe) == 0:
            return False

        current_candles = dataframe[dataframe['date'] <= current_time]
        if len(current_candles) == 0:
            return False
            
        current_roc = current_candles.iloc[-1].get('roc_3d_1h', 0)
        if pd.isna(current_roc):
            return False

        whitelist = self.dp.current_whitelist()
        
        # Haal open trades op om te kijken welke munten we al bezitten
        from freqtrade.persistence import Trade
        open_trades = Trade.get_open_trades()
        open_pairs = [t.pair for t in open_trades]

        better_coins_count = 0
        
        for p in whitelist:
            if p == pair:
                continue
            
            p_df, _ = self.dp.get_analyzed_dataframe(p, self.timeframe)
            if p_df is not None and len(p_df) > 0:
                p_candles = p_df[p_df['date'] <= current_time]
                if len(p_candles) > 0:
                    p_roc = p_candles.iloc[-1].get('roc_3d_1h', 0)
                    
                    if not pd.isna(p_roc) and p_roc > current_roc:
                        better_coins_count += 1
                        
                        # Als de betere munt NIET in bezit is, en NIET in cooldown zit, 
                        # betekent dit dat er een vrij, sterker alternatief op de markt is.
                        # Dan mogen we DEZE huidige munt dus NIET kopen!
                        if p not in open_pairs and not PairLocks.is_pair_locked(p, current_time):
                            return False
                            
        # Zelfs als alle betere munten bezet zijn, zakken we maximaal af tot de absolute #3 van de markt
        if better_coins_count >= 3:
            return False
            
        return True

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> str | None:
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1].squeeze()

        # Exit als de 5m trend breekt (EMA short kruist onder EMA long)
        if last_candle.get('ema_short') < last_candle.get('ema_long'):
            # Lock pair for 1 hour to prevent immediate re-entry
            lock_time = current_time + timedelta(hours=1)
            PairLocks.lock_pair(pair, lock_time, "Trend_Reversal")
            return "5m_trend_reversal"

        return None

