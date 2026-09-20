#!/bin/bash
cat << 'HEADER' > dashboard/api_new.jsx
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { setCurrency } from './components.jsx';

HEADER
cat dashboard/api.jsx | sed 's/const { useQuery } = window.ReactQuery || {};//g' | sed 's/(useQuery || (() => ({})))/useQuery/g' | sed 's/if (!baseUrl || !window.ReactQuery) return emptyState;/if (!baseUrl) return emptyState;/g' | sed '/Object.assign(window, {/,/});/d' >> dashboard/api_new.jsx

cat << 'FOOTER' >> dashboard/api_new.jsx

export {
  POLL_INTERVAL, loadConfig, saveConfig, clearConfig, loadBots, saveBots, addBot, removeBot,
  mapPosition, mapTrade, mapReason, buildEquity, buildSummary, EXCHANGE_DISPLAY_NAMES,
  formatExchangeName, buildBot, useFreqtradeData, login, forceExit, deleteLock,
  fetchPairCandles, fetchAllPairSignals, fetchWhitelist, fetchChartCandles, fetchPlotConfig
};
FOOTER
mv dashboard/api_new.jsx dashboard/api.jsx
