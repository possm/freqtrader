#!/bin/bash
cat << 'HEADER' > dashboard/components_new.jsx
import React, { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';

HEADER
cat dashboard/components.jsx | sed 's/const { useState, useEffect, useMemo, useRef, useLayoutEffect } = React;//g' >> dashboard/components_new.jsx

cat << 'FOOTER' >> dashboard/components_new.jsx

export {
  useBreakpoint, STAKE_SYMBOLS, setCurrency, getCurrency, fmtMoney, pnlColor, pnlTone,
  fmtPrice, fmtCompact, fmtDuration, fmtTimeAgo, fmtTime, mulberry32, hashStr, sparkSeries,
  Icon, PAIR_COLORS, PairToken, PairLabel, Card, PnlPill, TableStack, Sparkline, StatusDot,
  EquityChart, DailyBars, WinLossDonut, ColHead, Segmented, Chip, Btn, SearchInput, KpiCard,
  MobileRowCard, MobilePositionCard, MobileTradeCard, MobileSignalCard, applySort
};
FOOTER
mv dashboard/components_new.jsx dashboard/components.jsx
