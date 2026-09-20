#!/bin/bash
cat << 'HEADER' > dashboard/app_new.jsx
import React, { useState as aUseState, useEffect as aUseEffect, useCallback as aUseCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Icon, Btn, useBreakpoint, Card
} from './components.jsx';
import {
  useFreqtradeData, login, loadConfig, saveConfig, clearConfig, loadBots, saveBots, addBot, removeBot
} from './api.jsx';
import {
  OverviewView, ChartView, SignalsView, TradesView, PerformanceView, LocksView
} from './views.jsx';

HEADER
cat dashboard/app.jsx | sed 's/const { useState: aUseState, useEffect: aUseEffect, useCallback: aUseCallback } = React;//g' >> dashboard/app_new.jsx

mv dashboard/app_new.jsx dashboard/app.jsx
