// Freqtrade REST API client.
// Exposes useFreqtradeData() hook that polls all endpoints every 5s.
// Also exposes auth helpers (login / logout / stored config).

const POLL_INTERVAL = 5000;
const STORAGE_KEY = "ft_api_config";   // active bot config (back-compat)
const BOTS_KEY = "ft_bots";            // list of all saved bots

// ── Config (stored in localStorage) ──────────────────────────────────────────
function loadConfig() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); }
  catch { return null; }
}
function saveConfig(cfg) {
  // Tag with name if missing — fallback to URL (host:port)
  if (!cfg.name) {
    try { cfg.name = new URL(cfg.url).host; } catch { cfg.name = cfg.url; }
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
  addBot(cfg);  // also add/update in the bot list
}
function clearConfig() {
  // Logout clears tokens + active bot, but KEEPS the saved bot list
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem("ft_token");
  sessionStorage.removeItem("ft_refresh");
}

// ── Multi-bot support ─────────────────────────────────────────────────────────
function loadBots() {
  try {
    const arr = JSON.parse(localStorage.getItem(BOTS_KEY) || "[]");
    return Array.isArray(arr) ? arr : [];
  } catch { return []; }
}
function saveBots(arr) {
  localStorage.setItem(BOTS_KEY, JSON.stringify(arr));
}
function addBot(cfg) {
  const bots = loadBots();
  const idx = bots.findIndex(b => b.url === cfg.url);
  if (idx >= 0) bots[idx] = { ...bots[idx], ...cfg };
  else bots.push(cfg);
  saveBots(bots);
  return bots;
}
function removeBot(url) {
  const bots = loadBots().filter(b => b.url !== url);
  saveBots(bots);
  return bots;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
// Freqtrade's /token/login expects HTTP Basic auth (NOT a JSON body).
// If we sent JSON body without an Authorization header, the API returns 401 with
// `WWW-Authenticate: Basic` — the browser then pops up its native login dialog,
// which is the "second login" the user kept seeing.
async function login(baseUrl, username, password) {
  const res = await fetch(baseUrl.replace(/\/$/, "") + "/api/v1/token/login", {
    method: "POST",
    headers: { "Authorization": "Basic " + btoa(username + ":" + password) },
  });
  if (!res.ok) throw new Error("Login failed — check credentials");
  const data = await res.json();
  if (!data.access_token) throw new Error("No access token returned");
  sessionStorage.setItem("ft_token", data.access_token);
  if (data.refresh_token) sessionStorage.setItem("ft_refresh", data.refresh_token);
  return data.access_token;
}

// Use the refresh token to get a new access token without re-sending credentials.
async function refreshAccessToken(baseUrl) {
  const refresh = sessionStorage.getItem("ft_refresh");
  if (!refresh) throw new Error("No refresh token");
  const res = await fetch(baseUrl.replace(/\/$/, "") + "/api/v1/token/refresh", {
    method: "POST",
    headers: { "Authorization": "Bearer " + refresh },
  });
  if (!res.ok) throw new Error("Refresh failed");
  const data = await res.json();
  if (!data.access_token) throw new Error("Refresh returned no token");
  sessionStorage.setItem("ft_token", data.access_token);
  return data.access_token;
}

// Try refresh first, fall back to a full re-login using stored credentials.
async function ensureToken(baseUrl) {
  try { return await refreshAccessToken(baseUrl); }
  catch {
    const cfg = loadConfig();
    if (!cfg) throw new Error("No stored credentials");
    return await login(baseUrl, cfg.username, cfg.password);
  }
}

// ── HTTP helper with transparent token recovery ──────────────────────────────
async function ftFetch(baseUrl, path, opts = {}, _retried = false) {
  const token = sessionStorage.getItem("ft_token");
  const res = await fetch(baseUrl.replace(/\/$/, "") + path, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": "Bearer " + token } : {}),
      ...(opts.headers || {}),
    },
  });
  if (res.status === 401 && !_retried) {
    // Token expired or missing — refresh/re-login and retry exactly once.
    try { await ensureToken(baseUrl); }
    catch { throw Object.assign(new Error("Unauthorized"), { code: 401 }); }
    return ftFetch(baseUrl, path, opts, true);
  }
  if (res.status === 401) throw Object.assign(new Error("Unauthorized"), { code: 401 });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// ── Data mappers ──────────────────────────────────────────────────────────────
function mapPosition(t) {
  const entry = t.open_rate ?? 0;
  const current = t.current_rate ?? entry;
  const size = t.amount ?? 0;
  const pnlAbs = t.profit_abs ?? 0;
  const pnlPct = (t.profit_ratio ?? 0) * 100;
  const sl = t.stop_loss_abs ?? t.initial_stop_loss_abs ?? (entry * 0.97);
  // Freqtrade doesn't expose TP directly; derive from min_roi[0] or fall back to 3%
  const tp = t.min_roi_timeoutted ?? (entry * 1.03);
  const spark = sparkSeries(entry, current, 40, String(t.trade_id));
  return {
    id: String(t.trade_id),
    pair: t.pair,
    side: (t.is_short ? "short" : "long"),
    strategy: t.strategy || "—",
    entry, current, size,
    stakeAmount: t.stake_amount ?? (entry * size),
    notional: current * size,
    openedAt: t.open_timestamp,
    sl, tp, pnlAbs, pnlPct, spark,
    orders: t.orders || [],
    entries: t.nr_of_successful_entries ?? t.nr_of_successful_buys ?? 1,
    exits: t.nr_of_successful_exits ?? t.nr_of_successful_sells ?? 0,
    maxStake: t.max_stake_amount, // Optional if provided by bot
  };
}

function mapTrade(t) {
  const entry = t.open_rate ?? 0;
  const exit  = t.close_rate ?? t.open_rate ?? 0;
  const size  = t.amount ?? 0;
  const durMin = t.trade_duration ?? Math.round(((t.close_timestamp ?? Date.now()) - (t.open_timestamp ?? 0)) / 60000);
  return {
    id: String(t.trade_id),
    pair: t.pair,
    strategy: t.strategy || "—",
    side: (t.is_short ? "short" : "long"),
    entry, exit, size, durMin,
    stakeAmount: t.stake_amount ?? (entry * size),
    notional: exit * size,
    openedAt: t.open_timestamp,
    closedAt: t.close_timestamp ?? Date.now(),
    pnlAbs: t.profit_abs ?? 0,
    pnlPct: (t.profit_ratio ?? 0) * 100,
    reason: mapReason(t.exit_reason, t),
    status: "closed",
  };
}

function mapReason(r, t) {
  const reason = (r || (t && t.sell_reason) || "").toLowerCase();
  if (!reason) return "Strategy exit";
  if (reason === "roi") return "ROI";
  if (reason === "stop_loss" || reason === "stoploss") return "Stop-loss";
  if (reason === "take_profit" || reason === "roi_custom") return "Take-profit";
  if (reason === "trailing_stop_loss") return "Trailing stop";
  if (reason === "force_exit" || reason === "emergency_exit") return "Force-exit";
  if (reason === "ema_cross_exit") return "EMA Cross";
  return "Strategy exit";
}

function buildEquity(dailyStats, currentBalance, totalPnl, unrealizedPnl = 0) {
  // dailyStats from /daily: array of {date, abs_profit, ...}
  // Freqtrade returns newest-first — sort ascending so we accumulate oldest→newest.
  if (!dailyStats || dailyStats.length === 0) return [];
  const sorted = [...dailyStats].sort((a, b) => new Date(a.date) - new Date(b.date));
  // Freqtrade's /balance (currentBalance) already includes the live value of open positions.
  // To avoid double-counting, we subtract unrealizedPnl to find the true closed starting balance.
  const closedBalance = (currentBalance ?? 0) - unrealizedPnl;
  const startBalance = closedBalance - (totalPnl ?? 0);
  let cumulative = startBalance;
  return sorted.map((d, i) => {
    cumulative += (d.abs_profit ?? 0);
    const isLast = i === sorted.length - 1;
    return { 
      date: d.date, 
      v: Math.max(0, cumulative),
      unrealized: isLast ? unrealizedPnl : 0
    };
  });
}

function buildSummary(profit, trades, positions) {
  const closedTrades = trades.filter(t => t.status === "closed");
  const wins   = closedTrades.filter(t => t.pnlAbs > 0);
  const losses  = closedTrades.filter(t => t.pnlAbs <= 0);
  const totalPnl = profit?.profit_closed_coin ?? closedTrades.reduce((a, t) => a + t.pnlAbs, 0);
  const totalVol  = closedTrades.reduce((a, t) => a + Math.abs(t.entry * t.size), 0);
  const avgWin    = wins.length   ? wins.reduce((a, t) => a + t.pnlAbs, 0) / wins.length   : 0;
  const avgLoss   = losses.length ? losses.reduce((a, t) => a + t.pnlAbs, 0) / losses.length : 0;
  const grossWin  = wins.reduce((a, t) => a + t.pnlAbs, 0);
  const grossLoss = Math.abs(losses.reduce((a, t) => a + t.pnlAbs, 0)) || 1;
  const profitFactor = grossWin / grossLoss;
  const strats = [...new Set(closedTrades.map(t => t.strategy))];
  const STRATEGY_STATS = strats.map(s => {
    const ts = closedTrades.filter(t => t.strategy === s);
    const w  = ts.filter(t => t.pnlAbs > 0).length;
    const pnl = ts.reduce((a, t) => a + t.pnlAbs, 0);
    return {
      name: s, trades: ts.length,
      winRate: ts.length ? (w / ts.length) * 100 : 0,
      pnl,
      avgPct: ts.length ? ts.reduce((a, t) => a + t.pnlPct, 0) / ts.length : 0,
    };
  }).sort((a, b) => b.pnl - a.pnl);
  const sorted = closedTrades.slice().sort((a, b) => b.pnlAbs - a.pnlAbs);
  return {
    totalPnl,
    roiPct: profit?.profit_closed_percent ?? ((totalPnl / (profit?.holding_value ?? 10000)) * 100),
    winRate: closedTrades.length ? (wins.length / closedTrades.length) * 100 : 0,
    lossRate: closedTrades.length ? (losses.length / closedTrades.length) * 100 : 0,
    trades: closedTrades.length,
    wins: wins.length, losses: losses.length,
    avgWin, avgLoss, profitFactor, totalVolume: totalVol,
    best: sorted[0] ?? null, worst: sorted[sorted.length - 1] ?? null,
    bestStrategy: STRATEGY_STATS[0] ?? null,
    worstStrategy: STRATEGY_STATS[STRATEGY_STATS.length - 1] ?? null,
    STRATEGY_STATS,
  };
}

// Map Freqtrade exchange IDs (always lowercase, e.g. "kucoin") to their
// human-friendly display names. Unknown values fall back to a Title-cased
// version of the raw string.
const EXCHANGE_DISPLAY_NAMES = {
  binance: "Binance", binanceus: "Binance.US", binancecoinm: "Binance COIN-M", binanceusdm: "Binance USDS-M",
  bitvavo: "Bitvavo", kraken: "Kraken", kucoin: "KuCoin", kucoinfutures: "KuCoin Futures",
  bybit: "Bybit", okx: "OKX", okex: "OKEx",
  coinbase: "Coinbase", coinbasepro: "Coinbase Pro", coinbaseinternational: "Coinbase International",
  gateio: "Gate.io", gate: "Gate.io",
  htx: "HTX", huobi: "Huobi", huobipro: "Huobi Pro",
  bitfinex: "Bitfinex", bitstamp: "Bitstamp", bitmex: "BitMEX",
  bingx: "BingX", mexc: "MEXC", phemex: "Phemex", woox: "WOO X",
  cryptocom: "Crypto.com", deribit: "Deribit",
};

function formatExchangeName(raw) {
  if (raw == null) return "—";
  // Some Freqtrade builds return { name: "binance", ... } as an object — handle both.
  const rawStr = typeof raw === "string" ? raw : raw.name || raw.id || "";
  if (!rawStr) return "—";
  const key = rawStr.toLowerCase().replace(/[\s_-]/g, "");
  return EXCHANGE_DISPLAY_NAMES[key] || rawStr.charAt(0).toUpperCase() + rawStr.slice(1);
}

function buildBot(config, balance, positions) {
  const maxSlots = config?.max_open_trades ?? 10;
  const stakeCurr = config?.stake_currency ?? "USDT";
  let avail = 0;
  if (balance?.currencies && Array.isArray(balance.currencies)) {
    const c = balance.currencies.find(x => x.currency === stakeCurr);
    if (c) avail = c.free;
  }

  return {
    name: config?.bot_name ?? "freqtrade",
    status: "running",
    exchange: formatExchangeName(config?.exchange),
    mode: config?.dry_run ? "Dry" : "Live",
    stake: stakeCurr,
    openSlots: maxSlots < 0 ? 99 : maxSlots,
    usedSlots: positions.length,
    balance: balance?.total ?? 0,
    available: avail,
    allocated: positions.reduce((a, p) => a + (p.stakeAmount || 0), 0),
    uptime: "—",
    timeframe: config?.timeframe ?? "4h",
    strategy: config?.strategy ?? null,
  };
}

// ── Main data hook ────────────────────────────────────────────────────────────
function useFreqtradeData(baseUrl) {
  const [state, setState] = React.useState({
    positions: [],
    trades: [],
    equity: [],
    daily: [],
    summary: null,
    bot: null,
    strats: [],
    locks: [],
    loading: true,
    error: null,
    lastUpdated: null,
  });

  const rawRef = React.useRef({
    status: [], trades: null, profit: null, daily: null, balance: null, config: null, locks: null
  });

  const processData = React.useCallback(() => {
    const { status, trades, profit, daily, balance, config, locksRes } = rawRef.current;
    
    const positions = (Array.isArray(status) ? status : []).map(mapPosition);
    const allTrades = (trades?.trades ?? []).map(mapTrade);
    const closedTrades = allTrades.filter(t => t.status === "closed");
    const unrealizedPnl = positions.reduce((a, p) => a + p.pnlAbs, 0);

    const sortedDaily = [...(daily?.data ?? [])].sort((a, b) => new Date(a.date) - new Date(b.date));
    const dailyArr = sortedDaily.map((d, i, arr) => ({
      date: d.date, daysAgo: arr.length - 1 - i,
      v: d.abs_profit ?? 0,
      unrealized: i === arr.length - 1 ? unrealizedPnl : 0,
    }));

    const summary = buildSummary(profit, allTrades, positions);
    const bot = buildBot(config, balance, positions);
    setCurrency(bot.stake);
    const equity = buildEquity(daily?.data ?? [], bot.balance, summary.totalPnl, unrealizedPnl);
    const strats = [...new Set(allTrades.map(t => t.strategy).filter(Boolean))];
    
    const locksArr = Array.isArray(locksRes?.locks) ? locksRes.locks : (Array.isArray(locksRes) ? locksRes : []);
    const locks = locksArr.map(l => ({
      id: l.id, pair: l.pair, side: l.side || "*", reason: l.reason || "—",
      until: l.lock_end_timestamp ?? (l.lock_end_time ? new Date(l.lock_end_time).getTime() : null),
    })).filter(l => !l.until || l.until > Date.now()).sort((a, b) => (a.until ?? 0) - (b.until ?? 0));

    setState({
      positions, trades: closedTrades, equity, daily: dailyArr,
      summary, bot, strats, locks,
      loading: false, error: null, lastUpdated: Date.now(),
    });
  }, []);

  const fetchFast = React.useCallback(async () => {
    if (!baseUrl) return;
    try {
      const [status, balance] = await Promise.all([
        ftFetch(baseUrl, "/api/v1/status"),
        ftFetch(baseUrl, "/api/v1/balance").catch(() => null),
      ]);
      rawRef.current.status = status;
      rawRef.current.balance = balance;
      processData();
    } catch (err) {
      setState(prev => ({
        ...prev, loading: false,
        error: err.code === 401 ? "auth" : (err.message || "Connection error"),
      }));
    }
  }, [baseUrl, processData]);

  const fetchSlow = React.useCallback(async () => {
    if (!baseUrl) return;
    try {
      const [trades, profit, daily, config, locksRes] = await Promise.all([
        ftFetch(baseUrl, "/api/v1/trades?limit=500"),
        ftFetch(baseUrl, "/api/v1/profit").catch(() => null),
        ftFetch(baseUrl, "/api/v1/daily?timescale=30").catch(() => null),
        ftFetch(baseUrl, "/api/v1/show_config").catch(() => null),
        ftFetch(baseUrl, "/api/v1/locks").catch(() => null),
      ]);
      rawRef.current.trades = trades;
      rawRef.current.profit = profit;
      rawRef.current.daily = daily;
      rawRef.current.config = config;
      rawRef.current.locksRes = locksRes;
      processData();
    } catch (err) {
      // Fast poll handles auth errors mostly, but catch here too.
    }
  }, [baseUrl, processData]);

  const fetchAll = React.useCallback(async () => {
    await Promise.all([fetchFast(), fetchSlow()]);
  }, [fetchFast, fetchSlow]);

  React.useEffect(() => {
    if (!baseUrl) return;
    fetchAll();
    const fastId = setInterval(fetchFast, 5000);
    const slowId = setInterval(fetchSlow, 60000);
    return () => {
      clearInterval(fastId);
      clearInterval(slowId);
    };
  }, [fetchAll, fetchFast, fetchSlow, baseUrl]);

  return { ...state, refresh: fetchAll };
}

// Delete a pair lock by id — used by the dashboard's "unlock" action.
async function deleteLock(baseUrl, lockId) {
  return ftFetch(baseUrl, `/api/v1/locks/${lockId}`, { method: "DELETE" });
}

// Force exit a trade by id — used by the dashboard's "sell" action.
async function forceExit(baseUrl, tradeId) {
  return ftFetch(baseUrl, `/api/v1/forceexit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tradeid: tradeId })
  });
}

// ── Signals (per-pair indicator state) ────────────────────────────────────────
// Fetches the live analyzed dataframe for a single pair and returns the latest
// row as a {column: value} object. Freqtrade's /pair_candles response shape:
//   { columns: [...], data: [[...], [...]], length, strategy, pair, timeframe }
async function fetchPairCandles(baseUrl, pair, timeframe, limit = 1) {
  const qs = new URLSearchParams({ pair, timeframe, limit: String(limit) });
  const r = await ftFetch(baseUrl, `/api/v1/pair_candles?${qs.toString()}`);
  const cols = r?.columns || [];
  const rows = r?.data || [];
  if (!rows.length) return null;
  const last = rows[rows.length - 1];
  const obj = {};
  cols.forEach((c, i) => { obj[c] = last[i]; });
  return { pair, timeframe, strategy: r.strategy, lastAnalyzed: r.last_analyzed, candle: obj };
}

// Fetch live indicator state for all pairs (used by the Signals view).
async function fetchAllPairSignals(baseUrl, pairs, timeframe) {
  const results = await Promise.allSettled(
    pairs.map(p => fetchPairCandles(baseUrl, p, timeframe, 1))
  );
  return results.map((res, i) => ({
    pair: pairs[i],
    ok: res.status === "fulfilled" && res.value != null,
    data: res.status === "fulfilled" ? res.value : null,
    error: res.status === "rejected" ? (res.reason?.message || "error") : null,
  }));
}

// Fetch the live pair whitelist (configured pairs).
async function fetchWhitelist(baseUrl) {
  const r = await ftFetch(baseUrl, "/api/v1/whitelist");
  return Array.isArray(r?.whitelist) ? r.whitelist : [];
}

// Fetch N candles for a pair/timeframe, returning fully mapped row objects.
// The Freqtrade response includes all strategy indicators when the requested
// timeframe matches the bot's strategy timeframe.
async function fetchChartCandles(baseUrl, pair, timeframe, limit = 500) {
  const qs = new URLSearchParams({ pair, timeframe, limit: String(limit) });
  const r = await ftFetch(baseUrl, `/api/v1/pair_candles?${qs.toString()}`);
  if (!r || !r.columns || !r.data) return null;
  const cols = r.columns;
  const rows = r.data.map(row => {
    const obj = {};
    cols.forEach((c, i) => { obj[c] = row[i]; });
    return obj;
  });
  return {
    pair: r.pair || pair,
    timeframe: r.timeframe || timeframe,
    strategy: r.strategy,
    lastAnalyzed: r.last_analyzed,
    columns: cols,
    rows,
  };
}

// Fetch the live strategy's plot_config — explicit indicator → chart mapping
// defined by the strategy author.  Shape:
//   { main_plot: { col: {color, type, fill_to, fill_color, ...} },
//     subplots:  { "RSI": { col: {...}, ... }, "MACD": { ... } } }
async function fetchPlotConfig(baseUrl) {
  try {
    const r = await ftFetch(baseUrl, "/api/v1/plot_config");
    return r || null;
  } catch {
    return null;
  }
}

Object.assign(window, {
  loadConfig, saveConfig, clearConfig,
  login, refreshAccessToken, ensureToken, useFreqtradeData,
  deleteLock, forceExit,
  fetchPairCandles, fetchAllPairSignals, fetchWhitelist, fetchChartCandles,
  fetchPlotConfig,
});
