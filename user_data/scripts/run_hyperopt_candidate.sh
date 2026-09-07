#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-freqtrade-hopt-live}"
CONFIG="/freqtrade/user_data/config_binance.json"

echo "Running hyperopt on WolfTrend_2h_Candidate..."
docker compose run --rm "${SERVICE}" hyperopt \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces stoploss roi trailing \
  --strategy WolfTrend_2h_Candidate \
  --config "${CONFIG}" \
  --timerange "20210101-" \
  -e 150 2>&1 | tee user_data/logs/hyperopt_candidate.log
