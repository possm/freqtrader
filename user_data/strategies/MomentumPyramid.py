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
    timeframe = '1m'
    
    # Max 4999 candles voor Bybit 1m timeframe (Freqtrade limit is 5x exchange API limit)
    # 4999 candles = ~3.4 dagen. (We kunnen daardoor max een 3-day ROC gebruiken).
    startup_candle_count = 4999

    position_adjustment_enable = True
    max_entry_position_adjustment = 3

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
        # Prijs trend op 1m (snel)
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['price_rising'] = dataframe['close'] > dataframe['ema_short']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Gebruik de indicatoren van de 1h grafiek (automatisch _1h achtervoegsel)
                (dataframe['roc_3d_1h'] > 0) &
                (dataframe['volume_rising_1h'] == True) &
                (dataframe['price_rising'] == True)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        """ Cross-pair analyse: Koop uitsluitend de munt met hoogste smoothed ROC. """
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
        max_roc = current_roc
        
        for p in whitelist:
            if p == pair:
                continue
            
            p_df, _ = self.dp.get_analyzed_dataframe(p, self.timeframe)
            if p_df is not None and len(p_df) > 0:
                p_candles = p_df[p_df['date'] <= current_time]
                if len(p_candles) > 0:
                    p_roc = p_candles.iloc[-1].get('roc_3d_1h', 0)
                    if not pd.isna(p_roc) and p_roc > max_roc:
                        max_roc = p_roc
                        
        if current_roc < max_roc:
            return False
            
        return True

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> str | None:
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1].squeeze()

        # Exit gebaseerd op de 1h trend (minder ruis!)
        if last_candle.get('momentum_fading_1h', False) or not last_candle.get('volume_rising_1h', True):
            lock_time = datetime.now(timezone.utc) + timedelta(hours=4)
            PairLocks.lock_pair(pair, lock_time, "Momentum_or_volume_drop")
            return "fading_momentum_or_volume"

        return None

    def adjust_trade_position(self, trade: 'Trade', current_time: datetime, current_rate: float,
                              current_profit: float, min_stake: float | None,
                              max_stake: float, current_candle: dict, **kwargs) -> float | None:
        """ Pyramiding """
        if current_profit > 0.02 and current_candle['price_rising'] and not current_candle.get('momentum_fading_1h', True):
            return trade.stake_amount

        return None
