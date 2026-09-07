#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-freqtrade-hopt-live}"
CONFIG="/freqtrade/user_data/config_binance.json"

echo "Running hyperopt on WTE_btc200_2h for stoploss and trailing..."
docker compose run --rm "${SERVICE}" hyperopt \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces stoploss trailing \
  --strategy WTE_btc200_2h \
  --config "${CONFIG}" \
  --timerange "20210101-" \
  -e 250 2>&1 | tee user_data/logs/hyperopt_early.log
