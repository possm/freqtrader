from WolfTrend_EMA import WolfTrend_EMA


class WolfTrend_EMA_ema50sl(WolfTrend_EMA):
    """
    WolfTrend_EMA with EMA50 as a dynamic trailing stop (2% buffer below EMA50).
    The stop rises with the trend; once price breaks EMA50 the trade exits.
    Entry/exit signals and ROI are identical to the base strategy.
    """

    use_custom_stoploss = True

    def custom_stoploss(self, pair, trade, current_time, current_rate,
                        current_profit, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return self.stoploss

        ema50 = dataframe.iloc[-1]["ema50"]
        sl_price = ema50 * 0.98          # 2% buffer below EMA50
        sl_from_rate = (sl_price / current_rate) - 1
        return max(sl_from_rate, self.stoploss)  # never wider than -12%
