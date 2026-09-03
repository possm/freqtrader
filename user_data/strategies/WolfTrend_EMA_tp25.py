from WolfTrend_EMA import WolfTrend_EMA


class WolfTrend_EMA_tp25(WolfTrend_EMA):
    """WolfTrend_EMA with a hard 25% take-profit."""

    minimal_roi = {"0": 0.25}
