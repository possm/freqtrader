#!/usr/bin/env bash
set -euo pipefail

SERVICE="${SERVICE:-freqtrade-hopt-live}"
CONFIG="/freqtrade/user_data/config_binance.json"
STRATS="WTE_btc200 WTE_btc200_2h WTE_btc200_1h WTE_btc200_15m WTE_btc200_2h_sl5 WTE_btc200_1h_sl5 WTE_btc200_15m_sl5"

echo "Running backtests for variants on 2024 data..."
for STRAT in $STRATS; do
  echo "Backtesting $STRAT..."
  docker compose run --rm "${SERVICE}" backtesting \
    --config "${CONFIG}" \
    --strategy $STRAT \
    --timerange "20240101-" \
    --cache none 2>&1 | grep -A 25 "BACKTESTING REPORT" | tee -a user_data/logs/early_entry_backtest.log
done

