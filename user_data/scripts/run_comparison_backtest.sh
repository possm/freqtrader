#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-freqtrade-hopt-live}"
CONFIG="/freqtrade/user_data/config_binance.json"
STRATS="WTE_btc200 WTE_btc200_2h_sl5"

echo "Running full backtest for comparison (2021-2026)..."
> user_data/logs/comparison_backtest.log

for STRAT in $STRATS; do
  echo "Backtesting $STRAT..."
  docker compose run --rm "${SERVICE}" backtesting \
    --config "${CONFIG}" \
    --strategy $STRAT \
    --timerange "20210101-" \
    --export trades \
    --cache none 2>&1 | tee -a user_data/logs/comparison_backtest.log
done
