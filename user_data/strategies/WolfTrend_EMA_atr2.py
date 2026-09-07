import talib.abstract as ta
from WolfTrend_EMA import WolfTrend_EMA


class WolfTrend_EMA_atr2(WolfTrend_EMA):
    """
    WolfTrend_EMA with a 2×ATR(14) trailing stop instead of fixed -12%.
    The stop widens in volatile conditions and tightens in calm ones.
    Capped at -25% as a hard safety net.
    """

    use_custom_stoploss = True
    stoploss = -0.25  # fallback / safety cap

    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate,
                        current_profit, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty or "atr" not in dataframe.columns:
            return self.stoploss
        atr = dataframe.iloc[-1]["atr"]
        sl_price = current_rate - (2 * atr)
        sl_ratio = (sl_price / current_rate) - 1
        return max(sl_ratio, -0.25)
