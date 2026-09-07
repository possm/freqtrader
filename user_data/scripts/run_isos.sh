#!/usr/bin/env bash
#
# Phase 3 — cross-window In-Sample/Out-of-Sample runner.
#
# Backtests every variant across every yearly regime window in ONE pass per window
# (--strategy-list loads the data once and runs all strategies). Because we have a clean
# per-year grid, ANY of the three IS/OOS framings is just a re-grouping of these results:
#   * IS 2023 -> OOS 2024            (read y2023 vs y2024)
#   * IS 2024 -> OOS 2022 + 2023     (read y2024 vs y2022,y2023)
#   * IS 2021-22 -> OOS 2023-24      (read y2021,y2022 vs y2023,y2024)
#
# Each window exports a result JSON (for analyze_backtest.py) and tees the human-readable
# STRATEGY SUMMARY comparison to its own log (fallback if JSON parsing ever hiccups).
#
# RUN ON THE VPS:  bash user_data/scripts/run_isos.sh
# OVERRIDES:       STRATS="WolfQuantEdge WQE_Ride"  ORDER="y2023 y2024"  bash ...
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Auto-detect a compose service to run one-off backtests in (service names change as the user
# reorganizes bots). Any freqtrade service works — we override --config anyway. Override with SERVICE=.
SERVICE="${SERVICE:-$(docker compose config --services 2>/dev/null | head -1)}"
TIMEFRAME="${TIMEFRAME:-1h}"
CONFIG="/freqtrade/user_data/config_binance.json"
STRATS="${STRATS:-WolfQuantEdge WQE_NoDCA WQE_Ride WQE_Fresh WQE_RideNoDCA}"
OUTDIR="user_data/backtest_results"
LOGDIR="user_data/logs"
mkdir -p "${OUTDIR}" "${LOGDIR}"

declare -A WINDOWS=(
  [y2021]="20210101-20220101"
  [y2022]="20220101-20230101"
  [y2023]="20230101-20240101"
  [y2024]="20240101-20250101"
  [y2025]="20250101-20260101"
  [y2026]="20260101-20270101"
  [full]="20210101-"
)
ORDER="${ORDER:-y2021 y2022 y2023 y2024 y2025 y2026 full}"

for w in ${ORDER}; do
  tr="${WINDOWS[$w]}"
  echo "=================================================================="
  echo " WINDOW=${w}  timerange=${tr}  strategies=[${STRATS}]"
  echo "=================================================================="
  # snapshot the latest-result pointer BEFORE the run so we can prove a FRESH result was written
  lastfile="${OUTDIR}/.last_result.json"
  before="$(sed -E 's/.*"latest_backtest"[: ]*"([^"]+)".*/\1/' "${lastfile}" 2>/dev/null)"

  # shellcheck disable=SC2086  # intentional word-splitting of STRATS
  docker compose run --rm "${SERVICE}" backtesting \
    --config "${CONFIG}" \
    --strategy-list ${STRATS} \
    --timeframe "${TIMEFRAME}" \
    --timerange "${tr}" \
    --export trades \
    --cache none 2>&1 | tee "${LOGDIR}/isos_${w}.log"
  rc=${PIPESTATUS[0]}

  # Bulletproof guard: only tag if a NEW result was actually written (pointer changed). This
  # catches BOTH a non-zero exit AND the subtler failure where the run errors but we'd otherwise
  # re-tag a previous run's stale result (learned the hard way: a bad --strategy-list member
  # aborts the whole run and leaves the old pointer in place).
  latest="$(sed -E 's/.*"latest_backtest"[: ]*"([^"]+)".*/\1/' "${lastfile}" 2>/dev/null)"
  if [ "${rc}" -ne 0 ] || [ -z "${latest}" ] || [ "${latest}" = "${before}" ]; then
    echo "!! NO FRESH RESULT for window ${w} (rc=${rc}, latest='${latest}', before='${before}') — NOT tagging"
    continue
  fi
  cp -f "${OUTDIR}/${latest}" "${OUTDIR}/wqe_${w}.zip"
  cp -f "${OUTDIR}/${latest%.zip}.meta.json" "${OUTDIR}/wqe_${w}.meta.json" 2>/dev/null || true
  echo ">> tagged ${latest} -> wqe_${w}.zip"
done

echo ">> ISOS DONE — results in ${OUTDIR}/wqe_*.json, logs in ${LOGDIR}/isos_*.log"
