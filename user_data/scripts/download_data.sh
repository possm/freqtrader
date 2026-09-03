#!/usr/bin/env bash
#
# Phase 1.1 — Multi-year, multi-timeframe OHLCV download for Kraken-routed backtesting.
#
# WHY this shape:
#   * We discover/backtest on BINANCE data because it has the deepest history and the
#     thickest order books (cleanest price action, fewest data gaps).
#   * We TRADE on Kraken (see ../../config.json). The execution-drag gap between the two
#     venues is bridged by the slippage/spread mixin, NOT by the data source.
#   * download-data is INCREMENTAL: existing 15m/1h/4h candles are only topped-up to "now";
#     the 5m timeframe (currently absent for Binance) is back-filled from scratch.
#
# WHERE: run this ON THE VPS (that is where backtests execute and where the data lives).
#        From repo root:  bash user_data/scripts/download_data.sh
#
# OVERRIDES (env vars):  PAIRS="BTC/USDT ETH/USDT"  TIMEFRAMES="5m 1h"  START=20220101-  bash ...
#
set -euo pipefail

# --- locate the docker-compose project root (this file lives in user_data/scripts/) -------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${PROJECT_ROOT}"

SERVICE="${SERVICE:-freqtrade}"                 # docker-compose service name (one-off `run --rm`)
EXCHANGE="${EXCHANGE:-binance}"
CONFIG_IN_CONTAINER="/freqtrade/user_data/config_binance.json"
TIMEFRAMES="${TIMEFRAMES:-5m 15m 1h 4h}"
START="${START:-20210101-}"                     # ~5.4y: spans 2021 bull, 2022 bear, 2023 chop, 2024 bull, 2025-26
DATA_FORMAT="feather"

# Universe mirrors the LIVE Kraken EUR whitelist (../../config.json), quoted in USDT so we get
# Binance's depth + history. KAS is intentionally absent: Kaspa is NOT listed on Binance spot,
# so it is downloaded from Kraken separately at the bottom of this script.
PAIRS="${PAIRS:-AAVE/USDT ADA/USDT ARB/USDT BTC/USDT ETH/USDT FET/USDT HBAR/USDT INJ/USDT \
LINK/USDT NEAR/USDT OP/USDT POL/USDT RENDER/USDT SOL/USDT STX/USDT SUI/USDT TIA/USDT}"

echo "=============================================================================="
echo " download-data | exchange=${EXCHANGE} | tf=[${TIMEFRAMES}] | from=${START}"
echo " pairs: ${PAIRS}"
echo "=============================================================================="

# Per-pair loop so a single flaky/late-listed/unavailable pair cannot abort the batch.
# Each call still fetches ALL timeframes for that pair in one shot.
failed=""
for PAIR in ${PAIRS}; do
  echo "------------------------------------------------------------------------------"
  echo ">> ${PAIR}  [${TIMEFRAMES}]"
  # shellcheck disable=SC2086  # word-splitting of TIMEFRAMES is intentional
  if docker compose run --rm "${SERVICE}" download-data \
      --config "${CONFIG_IN_CONTAINER}" \
      --exchange "${EXCHANGE}" \
      --timeframes ${TIMEFRAMES} \
      --timerange "${START}" \
      --pairs "${PAIR}" \
      --data-format-ohlcv "${DATA_FORMAT}"; then
    echo ">> ${PAIR} OK"
  else
    echo "!! ${PAIR} FAILED/unavailable on ${EXCHANGE} — skipping"
    failed="${failed} ${PAIR}"
  fi
done
[ -n "${failed}" ] && echo ">> NOTE: failed/skipped pairs:${failed}"

echo
echo ">> Binance inventory after download:"
# shellcheck disable=SC2086
docker compose run --rm "${SERVICE}" list-data \
  --config "${CONFIG_IN_CONTAINER}" --exchange "${EXCHANGE}"

# --- KAS only exists on Kraken (not Binance) — grab it from the live venue itself -----------
# Kraken's history is shorter/thinner, but this keeps KAS tradeable in dry-run validation.
if [ "${SKIP_KAS:-0}" != "1" ]; then
  echo
  echo ">> KAS/USDT is not on Binance — downloading KAS from Kraken instead:"
  docker compose run --rm "${SERVICE}" download-data \
    --config /freqtrade/config.json \
    --exchange kraken \
    --timeframes ${TIMEFRAMES} \
    --timerange "${START}" \
    --pairs KAS/EUR KAS/USD \
    --data-format-ohlcv "${DATA_FORMAT}" \
    || echo "!! KAS download skipped/unavailable on Kraken — continuing."
fi

echo
echo ">> DONE. Data dir: user_data/data/${EXCHANGE}/ (+ user_data/data/kraken/ for KAS)"
