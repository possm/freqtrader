from WolfTrend_EMA import WolfTrend_EMA


class WolfTrend_EMA_roi(WolfTrend_EMA):
    """
    WolfTrend_EMA with a step ROI table instead of the disabled cap.
    Entry/exit signals and stoploss are identical to the base strategy.
    """

    minimal_roi = {
        "0":     0.15,   # close immediately at 15%
        "1440":  0.10,   # after 1 day, accept 10%
        "4320":  0.05,   # after 3 days, accept 5%
        "10080": 0.02,   # after 7 days, accept 2%
    }
