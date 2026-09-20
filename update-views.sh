#!/bin/bash
cat << 'HEADER' > dashboard/views_new.jsx
import React, { useState as vUseState, useMemo as vUseMemo, useEffect, useRef } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import { useQuery } from '@tanstack/react-query';
import {
  useBreakpoint, Card, Icon, PairToken, TableStack, pnlColor, pnlTone, fmtMoney, fmtPrice, 
  fmtCompact, fmtDuration, fmtTimeAgo, fmtTime, KpiCard, StatusDot, PnlPill, EquityChart, 
  DailyBars, WinLossDonut, ColHead, Segmented, Chip, Btn, SearchInput, MobileRowCard, 
  MobilePositionCard, MobileTradeCard, MobileSignalCard, applySort, getCurrency, PairLabel
} from './components.jsx';
import { formatExchangeName } from './api.jsx';

HEADER
cat dashboard/views.jsx | sed 's/const { useState: vUseState, useMemo: vUseMemo } = React;//g' | sed 's/const { createChart, CrosshairMode } = window.LightweightCharts || {};//g' >> dashboard/views_new.jsx

cat << 'FOOTER' >> dashboard/views_new.jsx

export {
  OverviewView, ChartView, SignalsView, TradesView, PerformanceView, LocksView
};
FOOTER
mv dashboard/views_new.jsx dashboard/views.jsx
