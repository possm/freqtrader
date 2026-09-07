"""
WolfTrend_1h_StoplossHopt — Hyperopt variant van WolfTrend_1h_Candidate
=======================================================================
Doel: stoploss-space optimaliseren via Freqtrade Hyperopt.
      Entry/exit logica is identiek aan de live strategie.
      Na de hyperopt wordt de beste stoploss overgenomen in WolfTrend_1h_Candidate.

Gebruik:
    freqtrade hyperopt \\
      --config config_hopt_stoploss.json \\
      --strategy WolfTrend_1h_StoplossHopt \\
      --hyperopt-loss SharpeHyperOptLoss \\
      --spaces stoploss \\
      --timerange 20230101-20260901 \\
      --epochs 200 \\
      -j -1
"""
from WolfTrend_1h_Candidate import WolfTrend_1h_Candidate


class WolfTrend_1h_StoplossHopt(WolfTrend_1h_Candidate):
    """
    Hyperopt-variant: identiek aan de live strategie maar met stoploss-space open.
    Freqtrade gebruikt de class-variabele `stoploss` als startpunt;
    de --spaces stoploss vlag laat Hyperopt automatisch de range -0.02 t/m -0.35 doorzoeken.
    """

    # Startpunt voor de search (huidige live waarde)
    stoploss = -0.05

    # Trailing stop: ook opnemen in de search
    # Hyperopt test automatisch trailing_stop aan/uit als --spaces stoploss is opgegeven
    trailing_stop = False
    trailing_stop_positive = None
    trailing_stop_positive_offset = 0.0
    trailing_only_offset_is_reached = False
