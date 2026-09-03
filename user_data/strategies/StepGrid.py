from datetime import datetime
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import pandas as pd
import pandas_ta as ta

class StepGrid(IStrategy):
    """
    StepGrid-like strategy for Freqtrade.
    It enters when RSI is relatively low.
    It buys additional steps (DCA) as the price drops.
    It exits when average profit hits a certain ROI target.
    """
    INTERFACE_VERSION = 3

    # DCA Settings
    position_adjustment_enable = True
    max_entry_position_adjustment = 5 # Allow 5 additional DCA orders (steps)
    
    # Step drops for DCA (e.g., -2%, -4%, -6%, -8%, -10%)
    dca_step_pct = DecimalParameter(0.015, 0.05, default=0.02, space="buy", optimize=True)

    # ROI table: Sell when average position profit reaches 1.5%
    minimal_roi = {
        "0": 0.015
    }

    # Stoploss (e.g. -15% total average drop)
    stoploss = -0.15

    timeframe = '15m'

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Simple RSI for initial entry
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (dataframe['rsi'] < 40),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        return dataframe

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: float, max_stake: float, **kwargs) -> float:
        """
        DCA Logic: add to position if the profit drops by the step percentage.
        """
        # Determine the number of successful entries (1 means just the initial order)
        count = trade.nr_of_successful_entries

        # We allow up to max_entry_position_adjustment additional entries
        if count <= self.max_entry_position_adjustment:
            # We want to buy if current profit is lower than (count * -step_pct)
            # E.g. count=1 (1 entry), wait for -2%. count=2 (2 entries), wait for -4%.
            target_drop = -(self.dca_step_pct.value * count)
            
            if current_profit < target_drop:
                # Calculate the amount to add (e.g. same as initial stake amount)
                # Ensure it fits within min_stake and max_stake
                stake = trade.stake_amount / count # Example: just add original stake size
                if stake > max_stake:
                    stake = max_stake
                if stake < min_stake:
                    return None
                return stake

        return None
