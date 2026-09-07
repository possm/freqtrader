// App shell: login screen, sidebar, top header, tab routing + data polling.

const { useState: aUseState, useEffect: aUseEffect, useCallback: aUseCallback } = React;

// ── Login screen ──────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }) {
  const savedBots = loadBots();
  // If bots are saved, default to picker view; otherwise show form for first-time setup
  const [mode, setMode] = aUseState(savedBots.length > 0 ? "picker" : "form");
  const [name, setName] = aUseState("");
  const [url, setUrl] = aUseState(() => loadConfig()?.url ?? "http://192.168.2.4");
  const [user, setUser] = aUseState(() => loadConfig()?.username ?? "freqtrader");
  const [pass, setPass] = aUseState("");
  const [error, setError] = aUseState(null);
  const [busy, setBusy] = aUseState(false);

  const connectWith = async (cfg) => {
    setBusy(true); setError(null);
    try {
      await login(cfg.url.trim(), cfg.username.trim(), cfg.password);
      saveConfig({ name: cfg.name, url: cfg.url.trim(), username: cfg.username.trim(), password: cfg.password });
      onLogin(cfg.url.trim());
    } catch (err) {
      setError(err.message);
    } finally { setBusy(false); }
  };

  const submitForm = async (e) => {
    e.preventDefault();
    await connectWith({
      name: name.trim() || (new URL(url.trim())).host,
      url: url.trim(),
      username: user.trim(),
      password: pass,
    });
  };

  const inputStyle = {
    width: "100%", padding: "9px 12px",
    background: "var(--panel-2)", border: "1px solid var(--border-2)",
    borderRadius: 8, color: "var(--text)", fontSize: 14, fontFamily: "inherit",
    outline: "none",
  };
  const labelStyle = { fontSize: 12.5, color: "var(--muted)", marginBottom: 6, display: "block", letterSpacing: ".04em" };

  return (
    <div style={{ height: "100%", display: "grid", placeItems: "center", background: "var(--bg)" }}>
      <div style={{
        width: "min(380px, calc(100vw - 32px))", background: "var(--panel)", border: "1px solid var(--border)",
        borderRadius: 16, padding: "clamp(20px, 5vw, 32px) clamp(16px, 5vw, 28px)",
        display: "flex", flexDirection: "column", gap: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <FreqtradeMark/>
          <div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>freqtrade</div>
            <div className="muted" style={{ fontSize: 12 }}>
              {mode === "picker" ? "Pick a bot to connect" : "Add a new bot"}
            </div>
          </div>
        </div>

        {mode === "picker" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {savedBots.map((bot) => (
              <button key={bot.url} type="button" disabled={busy}
                onClick={() => connectWith(bot)}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "12px 14px", background: "var(--panel-2)",
                  border: "1px solid var(--border-2)", borderRadius: 10,
                  color: "var(--text)", fontSize: 14, fontFamily: "inherit",
                  cursor: busy ? "not-allowed" : "pointer", textAlign: "left",
                  opacity: busy ? .6 : 1,
                }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{bot.name || bot.url}</div>
                  <div className="muted" style={{ fontSize: 12 }}>{bot.url}</div>
                </div>
                <span onClick={(e) => {
                  e.stopPropagation();
                  if (confirm(`Remove "${bot.name || bot.url}" from saved bots?`)) {
                    removeBot(bot.url);
                    setMode(loadBots().length > 0 ? "picker" : "form");
                  }
                }} style={{
                  padding: "4px 8px", color: "var(--muted)", cursor: "pointer",
                  fontSize: 15, opacity: .6,
                }} title="Remove">×</span>
              </button>
            ))}
            <button type="button" onClick={() => { setMode("form"); setName(""); setUrl(""); setUser("freqtrader"); setPass(""); setError(null); }}
              style={{
                padding: "10px 14px", marginTop: 4,
                background: "transparent", border: "1px dashed var(--border-2)",
                borderRadius: 10, color: "var(--muted)", fontSize: 13,
                cursor: "pointer", fontFamily: "inherit",
              }}>+ Add another bot</button>
          </div>
        )}

        {mode === "form" && (
          <form onSubmit={submitForm} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div>
              <label style={labelStyle}>Name (optional)</label>
              <input style={inputStyle} value={name} onChange={e => setName(e.target.value)}
                     placeholder="Wolf Custom Swing"/>
            </div>
            <div>
              <label style={labelStyle}>API URL</label>
              <input style={inputStyle} value={url} onChange={e => setUrl(e.target.value)}
                     placeholder="http://192.168.2.4:8080" required/>
            </div>
            <div>
              <label style={labelStyle}>Username</label>
              <input style={inputStyle} value={user} onChange={e => setUser(e.target.value)}
                     placeholder="freqtrader" required/>
            </div>
            <div>
              <label style={labelStyle}>Password</label>
              <input style={inputStyle} type="password" value={pass} onChange={e => setPass(e.target.value)}
                     placeholder="••••••••" required/>
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              {savedBots.length > 0 && (
                <button type="button" onClick={() => setMode("picker")} style={{
                  padding: "10px 14px", borderRadius: 8, border: "1px solid var(--border-2)",
                  background: "transparent", color: "var(--muted)", fontSize: 14,
                  cursor: "pointer", fontFamily: "inherit",
                }}>← Back</button>
              )}
              <button type="submit" disabled={busy} style={{
                flex: 1, padding: "10px 16px", borderRadius: 8, border: 0,
                background: "var(--accent)", color: "#062523", fontSize: 14, fontWeight: 600,
                cursor: busy ? "not-allowed" : "pointer", opacity: busy ? .7 : 1, fontFamily: "inherit",
              }}>
                {busy ? "Connecting…" : "Connect"}
              </button>
            </div>
          </form>
        )}

        {error && (
          <div style={{
            display: "flex", alignItems: "center", gap: 8, padding: "9px 12px",
            background: "var(--down-soft)", border: "1px solid var(--down-line)", borderRadius: 8,
            fontSize: 13.5, color: "var(--down)",
          }}>
            <Icon name="warn" size={14}/>
            {error}
          </div>
        )}

        <div className="muted" style={{ fontSize: 12, textAlign: "center", lineHeight: 1.6 }}>
          Credentials are stored in localStorage and the JWT in sessionStorage.
        </div>
      </div>
    </div>
  );
}

// ── Sidebar ────────────────────────────────────────────────────────────────────
function Sidebar({ tab, setTab, compact }) {
  const items = [
    { id: "overview",    icon: "dashboard", label: "Dashboard" },
    { id: "chart",       icon: "candles",   label: "Chart" },
    { id: "signals",     icon: "target",    label: "Signals" },
    { id: "trades",      icon: "trades",    label: "Trades" },
    { id: "performance", icon: "perf",      label: "Performance" },
    { id: "locks",       icon: "lock",      label: "Pair locks" },
  ];
  return (
    <aside className="chrome" style={{
      width: compact ? 64 : 220, flexShrink: 0,
      background: "var(--bg-2)", borderRight: "1px solid var(--border)",
      display: "flex", flexDirection: "column",
      padding: compact ? "16px 0" : "16px 12px",
      transition: "width .15s ease",
    }}>
      <div style={{
        padding: compact ? "0 0 18px" : "4px 8px 18px",
        display: "flex", alignItems: "center", gap: 10, justifyContent: compact ? "center" : "flex-start",
      }}>
        <FreqtradeMark/>
        {!compact && (
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
            <span style={{ fontSize: 14.5, fontWeight: 600, letterSpacing: ".005em" }}>freqtrade</span>
            <span className="muted" style={{ fontSize: 11.5, letterSpacing: ".08em", textTransform: "uppercase" }}>console</span>
          </div>
        )}
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 4 }}>
        {items.map(it => {
          const on = tab === it.id;
          return (
            <button key={it.id} type="button" onClick={() => setTab(it.id)}
              title={compact ? it.label : ""}
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: compact ? "10px 0" : "9px 12px",
                background: on ? "var(--panel-2)" : "transparent",
                color: on ? "var(--text)" : "var(--text-2)",
                border: 0, borderRadius: 9,
                fontFamily: "inherit", fontSize: 13.5, fontWeight: 500,
                cursor: "pointer", textAlign: "left", position: "relative",
                justifyContent: compact ? "center" : "flex-start",
                width: compact ? 44 : "100%", margin: compact ? "0 auto" : 0,
              }}>
              {on && !compact && (
                <span style={{ position: "absolute", left: -12, top: 6, bottom: 6, width: 2.5, background: "var(--accent)", borderRadius: 99 }}/>
              )}
              <Icon name={it.icon} size={17} style={{ color: on ? "var(--accent)" : "currentColor" }}/>
              {!compact && <span>{it.label}</span>}
              {!compact && it.badge != null && (
                <span style={{
                  marginLeft: "auto",
                  background: on ? "var(--accent-soft)" : "var(--panel-3)",
                  color: on ? "var(--accent)" : "var(--text-2)",
                  fontSize: 11.5, fontWeight: 600, padding: "1px 7px",
                  borderRadius: 99, fontFamily: "var(--mono)",
                }}>{it.badge}</span>
              )}
              {compact && on && (
                <span style={{ position: "absolute", left: 0, top: 10, bottom: 10, width: 2.5, background: "var(--accent)", borderRadius: 99 }}/>
              )}
            </button>
          );
        })}
      </nav>

      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
        <SideBtn icon="bot" label="Strategies" compact={compact}/>
        <SideBtn icon="shield" label="Risk" compact={compact}/>
        <SideBtn icon="settings" label="Settings" compact={compact}/>
      </div>
    </aside>
  );
}

function SideBtn({ icon, label, compact }) {
  return (
    <button type="button" title={compact ? label : ""}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: compact ? "10px 0" : "9px 12px",
        background: "transparent", color: "var(--muted)",
        border: 0, borderRadius: 9, fontFamily: "inherit", fontSize: 13,
        cursor: "pointer", textAlign: "left",
        justifyContent: compact ? "center" : "flex-start",
        width: compact ? 44 : "100%", margin: compact ? "0 auto" : 0,
      }}>
      <Icon name={icon} size={16}/>
      {!compact && <span>{label}</span>}
    </button>
  );
}

// ── Mobile bottom nav ─────────────────────────────────────────────────────────
function MobileNav({ tab, setTab }) {
  const items = [
    { id: "overview",    icon: "dashboard", label: "Home" },
    { id: "chart",       icon: "candles",   label: "Chart" },
    { id: "trades",      icon: "trades",    label: "Trades" },
    { id: "performance", icon: "perf",      label: "Perf" },
    { id: "signals",     icon: "target",    label: "Signals" },
  ];
  return (
    <nav className="mobile-nav chrome">
      {items.map(it => {
        const on = tab === it.id;
        return (
          <button key={it.id} type="button" onClick={() => setTab(it.id)} style={{
            display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
            flex: 1, padding: "2px 0", background: "transparent", border: 0,
            color: on ? "var(--accent)" : "var(--muted)", fontFamily: "inherit", cursor: "pointer",
          }}>
            <Icon name={it.icon} size={22}/>
            <span style={{ fontSize: 10.5, fontWeight: 500, letterSpacing: ".03em" }}>{it.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

// ── Mobile top bar ────────────────────────────────────────────────────────────
function MobileTopBar({ tab, connected, onRefresh, activeBot, onLogout }) {
  const titles = {
    overview: "Dashboard", chart: "Chart",
    signals: "Signals", trades: "Trades",
    performance: "Performance", locks: "Pair Locks",
  };
  return (
    <header className="chrome mobile-topbar" style={{
      padding: "12px 16px 10px",
      borderBottom: "1px solid var(--border)",
      background: "var(--bg)", flexShrink: 0,
      alignItems: "center", gap: 10,
    }}>
      <FreqtradeMark/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 17, fontWeight: 600 }}>{titles[tab] || tab}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 1 }}>
          <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: 99, background: connected ? "var(--up)" : "var(--warn)", flexShrink: 0 }}/>
          <span className="muted" style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {activeBot?.name || activeBot?.url || "—"}
          </span>
        </div>
      </div>
      <Btn icon="refresh" tone="ghost" size="sm" onClick={onRefresh} title="Refresh"/>
      <Btn icon="logout" tone="ghost" size="sm" onClick={onLogout} title="Disconnect"/>
    </header>
  );
}

function FreqtradeMark() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" style={{ flexShrink: 0 }}>
      <rect x="0" y="0" width="30" height="30" rx="8" fill="var(--accent)"/>
      <path d="M7 19l4-5 4 3 8-9" stroke="#062523" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="23" cy="8" r="2" fill="#062523"/>
    </svg>
  );
}

// ── Bot switcher dropdown ─────────────────────────────────────────────────────
function BotSwitcher({ activeBot, onSwitch }) {
  const [open, setOpen] = aUseState(false);
  const bots = loadBots();
  if (bots.length <= 1) {
    // Just show the active bot name (no dropdown if only one)
    return activeBot ? (
      <div style={{
        display: "flex", alignItems: "center", gap: 6, padding: "5px 10px",
        borderRadius: 8, background: "var(--panel)", border: "1px solid var(--border)",
        fontSize: 13, color: "var(--text)",
      }}>
        <Icon name="bot" size={13}/>
        <span style={{ fontWeight: 600 }}>{activeBot.name || activeBot.url}</span>
      </div>
    ) : null;
  }

  const otherBots = bots.filter(b => b.url !== activeBot?.url);

  return (
    <div style={{ position: "relative" }}>
      <button type="button" onClick={() => setOpen(!open)} style={{
        display: "flex", alignItems: "center", gap: 6, padding: "5px 10px",
        borderRadius: 8, background: "var(--panel)", border: "1px solid var(--border)",
        fontSize: 13, color: "var(--text)", cursor: "pointer", fontFamily: "inherit",
      }}>
        <Icon name="bot" size={13}/>
        <span style={{ fontWeight: 600 }}>{activeBot?.name || activeBot?.url || "Select bot"}</span>
        <span style={{ fontSize: 10, marginLeft: 2, opacity: .6 }}>▼</span>
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{
            position: "fixed", inset: 0, zIndex: 100,
          }}/>
          <div style={{
            position: "absolute", top: "calc(100% + 4px)", right: 0, zIndex: 101,
            background: "var(--panel)", border: "1px solid var(--border)",
            borderRadius: 10, padding: 6, minWidth: 220,
            boxShadow: "0 8px 24px rgba(0,0,0,.4)",
          }}>
            <div className="muted" style={{ fontSize: 11, padding: "6px 10px", letterSpacing: ".05em" }}>
              SWITCH TO
            </div>
            {otherBots.map(b => (
              <button key={b.url} type="button"
                onClick={() => { setOpen(false); onSwitch(b); }}
                style={{
                  display: "flex", flexDirection: "column", alignItems: "flex-start",
                  width: "100%", padding: "8px 10px", background: "transparent",
                  border: 0, borderRadius: 6, cursor: "pointer", fontFamily: "inherit",
                  color: "var(--text)", textAlign: "left",
                }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{b.name || b.url}</span>
                <span className="muted" style={{ fontSize: 11 }}>{b.url}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Top header ─────────────────────────────────────────────────────────────────
function TopHeader({ tab, onRefresh, onLogout, connected, activeBot, onSwitchBot }) {
  const titles = {
    overview:    { t: "Dashboard",    s: "Live overview of bot activity, P&L and active positions" },
    chart:       { t: "Chart",        s: "Live candlestick chart with Bollinger Bands, volume and RSI / MFI" },
    signals:     { t: "Signals",       s: "Per-pair indicator state · which entry conditions are firing right now" },
    trades:      { t: "Trade history", s: "Closed and cancelled trades · filter, sort, export" },
    performance: { t: "Performance",  s: "All-time metrics, equity curve, strategy breakdown" },
    locks:       { t: "Pair locks",    s: "Pairs currently blocked by protections — unlock from here" },
  };
  const cur = titles[tab];
  const [now, setNow] = aUseState(new Date());
  aUseEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="chrome" style={{
      display: "flex", alignItems: "center", gap: 14, padding: "14px 24px",
      borderBottom: "1px solid var(--border)", background: "var(--bg)", flexShrink: 0,
    }}>
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
        <h1 style={{ margin: 0, fontSize: 19, fontWeight: 600, letterSpacing: "-.005em" }}>{cur.t}</h1>
        <span className="muted" style={{ fontSize: 12.5 }}>{cur.s}</span>
      </div>

      <BotSwitcher activeBot={activeBot} onSwitch={onSwitchBot}/>

      <div style={{
        display: "flex", alignItems: "center", gap: 8, padding: "5px 10px", borderRadius: 8,
        background: "var(--panel)", border: "1px solid var(--border)",
      }}>
        <span style={{ display: "inline-block", width: 6, height: 6, borderRadius: 99, background: connected ? "var(--up)" : "var(--warn)" }}/>
        <span className="num" style={{ fontSize: 12.5, color: "var(--muted)" }}>
          {connected ? "live · refreshes every 5s" : "disconnected"}
        </span>
        <span className="num" style={{ fontSize: 12, color: "var(--dim)", marginLeft: 4 }}>
          {now.toLocaleTimeString("en-US", { hour12: false })}
        </span>
      </div>

      <Btn icon="refresh" tone="ghost" size="sm" title="Refresh now" onClick={onRefresh}/>
      <Btn icon="logout" tone="ghost" size="sm" title="Disconnect" onClick={onLogout}/>
    </header>
  );
}

// ── App ────────────────────────────────────────────────────────────────────────
function App() {
  const { isMobile } = useBreakpoint();
  const [activeBot, setActiveBot] = aUseState(() => loadConfig());
  const [authed, setAuthed] = aUseState(() => !!sessionStorage.getItem("ft_token"));
  const [tab, setTab] = aUseState("overview");
  const [timeRange, setTimeRange] = aUseState("30d");
  const [compactNav, setCompactNav] = aUseState(true);
  const [chartPair, setChartPair] = aUseState("");
  const [tradeFocus, setTradeFocus] = aUseState(null);

  // Centralized callback: any view can call goToChart(pair) to deep-link
  // into the Chart tab with that pair pre-selected.
  const goToChart = aUseCallback((pair) => {
    setChartPair(pair);
    setTab("chart");
  }, []);

  // Deep-link into the Trades tab, scrolled to and highlighting one trade.
  const goToTrade = aUseCallback((tradeId) => {
    setTradeFocus(tradeId);
    setTab("trades");
  }, []);

  const baseUrl = activeBot?.url ?? null;
  const data = useFreqtradeData(authed && baseUrl ? baseUrl : null);

  const handleLogin = aUseCallback((url) => {
    setActiveBot(loadConfig());
    setAuthed(true);
  }, []);

  const handleLogout = aUseCallback(() => {
    clearConfig();
    setAuthed(false);
    setActiveBot(null);
  }, []);

  const handleSwitchBot = aUseCallback(async (bot) => {
    sessionStorage.removeItem("ft_token");
    sessionStorage.removeItem("ft_refresh");
    try {
      await login(bot.url, bot.username, bot.password);
      saveConfig(bot);
      setActiveBot(bot);
      setAuthed(true);
    } catch (err) {
      console.error("Bot switch failed:", err);
      setAuthed(false);
      setActiveBot(null);
    }
  }, []);

  aUseEffect(() => {
    if (authed && data.error === "auth") {
      setAuthed(false);
    }
  }, [data.error, authed]);

  if (!authed || !baseUrl) {
    return <LoginScreen onLogin={handleLogin}/>;
  }

  const connected = !data.error && !!data.lastUpdated;

  const errorBanner = data.error && data.error !== "auth" && (
    <div className="disconnect-banner">
      <Icon name="warn" size={14}/>
      <span>Connection error{!isMobile && `: ${data.error}`}</span>
      <button onClick={data.refresh} style={{
        marginLeft: "auto", background: "rgba(255,183,74,.18)", border: "1px solid rgba(255,183,74,.4)",
        color: "var(--warn)", borderRadius: 6, padding: "3px 10px", fontSize: 12, cursor: "pointer", fontFamily: "inherit",
      }}>Retry</button>
    </div>
  );

  const views = (
    <>
      {tab === "overview"    && <OverviewView    data={data} setTab={setTab}    isMobile={isMobile} goToChart={goToChart} goToTrade={goToTrade}/>}
      {tab === "chart"       && <ChartView       data={data} baseUrl={baseUrl}  isMobile={isMobile} selectedPair={chartPair} onPairChange={setChartPair}/>}
      {tab === "signals"     && <SignalsView     data={data} baseUrl={baseUrl}  isMobile={isMobile} goToChart={goToChart}/>}
      {tab === "trades"      && <TradesView      data={data}                    isMobile={isMobile} goToChart={goToChart} focusTradeId={tradeFocus} clearFocus={() => setTradeFocus(null)}/>}
      {tab === "performance" && <PerformanceView data={data} timeRange={timeRange} setTimeRange={setTimeRange} isMobile={isMobile} goToChart={goToChart}/>}
      {tab === "locks"       && <LocksView       data={data}                    isMobile={isMobile} goToChart={goToChart}/>}
    </>
  );

  // ── Mobile layout ──────────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        {/* Fills the status-bar zone so our background shows behind it */}
        <div className="safe-top"/>
        <MobileTopBar tab={tab} connected={connected} onRefresh={data.refresh}
                      activeBot={activeBot} onLogout={handleLogout}/>
        {errorBanner}
        <div style={{
          flex: 1, overflow: "auto", WebkitOverflowScrolling: "touch",
          padding: "12px 14px",
          paddingBottom: "calc(68px + max(env(safe-area-inset-bottom, 0px), 8px))",
        }}>
          {views}
        </div>
        <MobileNav tab={tab} setTab={setTab}/>
      </div>
    );
  }

  // ── Desktop layout ─────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", height: "100%", minHeight: 0 }}>
      <Sidebar tab={tab} setTab={setTab} compact={compactNav}/>

      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", background: "var(--bg)" }}>
        <TopHeader tab={tab} onRefresh={data.refresh} onLogout={handleLogout} connected={connected}
                   activeBot={activeBot} onSwitchBot={handleSwitchBot}/>
        {errorBanner}

        <div style={{ flex: 1, minHeight: 0, padding: 24, overflow: "auto" }}>
          {views}
        </div>
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App/>);
