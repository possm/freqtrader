// Tab views: Overview, Positions, Trades, Performance.
// All views receive data as props from the App's data context.

const { useState: vUseState, useMemo: vUseMemo } = React;

const TABLE_STYLE = { width: "100%", borderCollapse: "separate", borderSpacing: 0, fontSize: 13.5, lineHeight: 1.3 };
const TD = { padding: "0 14px", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap", height: "var(--row-h)", verticalAlign: "middle" };

// ════════════════════════════════════════════════════════════════════════════
//                         POSITIONS TABLE + EXPAND
// ════════════════════════════════════════════════════════════════════════════

function PositionsTable({ rows, expandable = true, compact = false, goToChart, refresh }) {
  const [sort, setSort] = vUseState({ key: "pnlPct", dir: "desc" });
  const [expanded, setExpanded] = vUseState(null);
  const [selling, setSelling] = vUseState(null);
  const sorted = vUseMemo(() => applySort(rows, sort), [rows, sort]);

  const onSell = async (e, p) => {
    e.stopPropagation();
    if (selling) return;
    if (!window.confirm(`Are you sure you want to force sell ${p.pair} at market price?`)) return;
    try {
      setSelling(p.id);
      const cfg = loadConfig();
      await forceExit(cfg?.url || "", p.id);
      if (refresh) await refresh();
    } catch (err) {
      console.error("Force exit failed", err);
      alert("Failed to force exit position.");
    } finally {
      setSelling(null);
    }
  };

  if (rows.length === 0) {
    return (
      <div style={{ display: "grid", placeItems: "center", padding: 40, color: "var(--muted)", fontSize: 14 }}>
        No open positions
      </div>
    );
  }

  return (
    <div style={{ overflow: "auto", flex: 1, minHeight: 0 }}>
      <table style={TABLE_STYLE}>
        <thead>
          <tr style={{ background: "var(--panel)", position: "sticky", top: 0, zIndex: 1 }}>
            <ColHead sortKey="id" sort={sort} setSort={setSort}>ID</ColHead>
            <ColHead sortKey="openedAt" sort={sort} setSort={setSort}>Age</ColHead>
            <ColHead sortKey="pair" sort={sort} setSort={setSort}>Pair</ColHead>
            <ColHead sortKey="entry" sort={sort} setSort={setSort} align="right">Entry</ColHead>
            {!compact && <ColHead sortKey="notional" sort={sort} setSort={setSort} align="right">Size</ColHead>}
            {!compact && <ColHead sortKey="stakeAmount" sort={sort} setSort={setSort} align="right">Cost</ColHead>}
            <ColHead sortKey="pnlPct" sort={sort} setSort={setSort} align="right">Result</ColHead>
            <ColHead align="right" style={{ width: 60 }}>Action</ColHead>
            <ColHead align="right" style={{ width: 40 }}></ColHead>
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => {
            const isOpen = expanded === p.id;
            const pos = p.pnlAbs >= 0;
            const slDist = p.current > 0 ? ((p.current - p.sl) / p.current) * 100 : 0;
            const tpDist = p.current > 0 ? ((p.tp - p.current) / p.current) * 100 : 0;
            return (
              <React.Fragment key={p.id}>
                <tr onClick={() => expandable && setExpanded(isOpen ? null : p.id)}
                    style={{ cursor: expandable ? "pointer" : "default", background: isOpen ? "var(--panel-2)" : "transparent" }}>
                  <td style={{ ...TD, color: "var(--muted)" }} className="num">
                    <span style={{ fontSize: 13 }}>#{p.id}</span>
                  </td>
                  <td style={TD}>
                    <span className="num" style={{ fontSize: 13 }}>{fmtDuration(Date.now() - p.openedAt)}</span>
                  </td>
                  <td style={TD}><PairLabel pair={p.pair} size={26} onClick={goToChart}/></td>
                  <td style={{ ...TD, textAlign: "right" }} className="num">{fmtPrice(p.entry)}</td>
                  {!compact && (
                    <td style={{ ...TD, textAlign: "right" }}>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", padding: "4px 0" }}>
                        <span className="num" style={{ fontSize: 13.5 }}>{fmtUsd(p.notional)}</span>
                        <span className="num muted" style={{ fontSize: 11.5 }}>
                          {p.size.toLocaleString(typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US", { maximumFractionDigits: 4 })} {p.pair.split("/")[0]}
                        </span>
                      </div>
                    </td>
                  )}
                  {!compact && (
                    <td style={{ ...TD, textAlign: "right" }} className="num">
                      <span style={{ fontSize: 13.5 }}>{fmtUsd(p.stakeAmount)}</span>
                    </td>
                  )}
                  <td style={{ ...TD, textAlign: "right" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", padding: "4px 0" }}>
                      <span className="num" style={{ fontSize: 14, fontWeight: 600, color: pos ? "var(--up)" : "var(--down)" }}>
                        {fmtPct(p.pnlPct)}
                      </span>
                      <span className="num muted" style={{ fontSize: 11.5 }}>
                        {fmtSignedUsd(p.pnlAbs)}
                      </span>
                    </div>
                  </td>
                  <td style={{ ...TD, textAlign: "right" }}>
                    <Btn size="sm" tone="ghost" disabled={selling === p.id} onClick={(e) => onSell(e, p)}>
                      {selling === p.id ? "..." : "Sell"}
                    </Btn>
                  </td>
                  <td style={{ ...TD, textAlign: "right", color: "var(--muted)" }}>
                    {expandable && <Icon name={isOpen ? "chevron-up" : "chevron-down"} size={14}/>}
                  </td>
                </tr>
                {expandable && isOpen && (
                  <tr style={{ background: "var(--panel-2)" }}>
                    <td colSpan={compact ? 7 : 9} style={{ padding: 0, borderBottom: "1px solid var(--border)" }}>
                      <ExpandedPosition p={p} slDist={slDist} tpDist={tpDist}/>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ExpandedPosition({ p, slDist, tpDist }) {
  const pos = p.pnlAbs >= 0;
  const series = vUseMemo(() => sparkSeries(p.entry, p.current, 80, p.id + "x"), [p.id, p.entry, p.current]);
  return (
    <div style={{ padding: "20px 24px", display: "grid", gridTemplateColumns: "1.6fr 1.1fr 1fr", gap: 32, borderTop: "1px solid var(--border)" }}>
      <div style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 500, letterSpacing: ".02em", color: "var(--muted)", textTransform: "uppercase" }}>Trend (last 6h)</span>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}>
          <PositionPriceChart p={p} series={series}/>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <span style={{ fontSize: 13, fontWeight: 500, letterSpacing: ".02em", color: "var(--muted)", textTransform: "uppercase", marginBottom: -2 }}>Position Details</span>
        <KV label="Opened" value={fmtTime(p.openedAt)} sub={fmtDuration(Date.now() - p.openedAt) + " ago"}/>
        <KV label="Direction" value={<Chip tone={p.side === "long" ? "up" : "down"} icon={p.side === "long" ? "up" : "down"}>{p.side.toUpperCase()}</Chip>} raw/>
        <KV label="Entry Price" value={fmtPrice(p.entry)} mono/>
        <KV label="Current Price" value={fmtPrice(p.current)} mono valueColor={pos ? "var(--up)" : "var(--down)"}/>
        <KV label="Position Size" value={fmtUsd(p.notional)} sub={`${p.size.toLocaleString(typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US", { maximumFractionDigits: 4 })} ${p.pair.split("/")[0]}`} mono/>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <span style={{ fontSize: 13, fontWeight: 500, letterSpacing: ".02em", color: "var(--muted)", textTransform: "uppercase", marginBottom: -2 }}>Risk Management</span>
        <div style={{ marginBottom: 4 }}>
          <SLTPBars p={p}/>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
          <KV label="Risk / Reward" value={(Math.abs(slDist) > 0 ? tpDist / Math.abs(slDist) : 0).toFixed(2)} mono />
          <KV label="Distance to Stop Loss" value={`${slDist.toFixed(2)}%`} valueColor="var(--down)" mono />
          <KV label="Distance to Target" value={`+${tpDist.toFixed(2)}%`} valueColor="var(--up)" mono />
        </div>
      </div>
    </div>
  );
}

function KV({ label, value, sub, mono, raw, valueColor }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
      <span className="muted" style={{ fontSize: 13, paddingTop: 1 }}>{label}</span>
      <div style={{ textAlign: "right" }}>
        {raw ? value :
          <div className={mono ? "num" : ""} style={{ fontSize: 14, color: valueColor || "var(--text)", fontWeight: mono ? 600 : 400 }}>{value}</div>}
        {sub && <div className="muted num" style={{ fontSize: 12, marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

function SLTPBars({ p }) {
  const lo = Math.min(p.sl, p.entry, p.current) * 0.997;
  const hi = Math.max(p.tp, p.entry, p.current) * 1.003;
  const range = hi - lo || 1;
  const pct = (v) => ((v - lo) / range) * 100;
  return (
    <div>
      <div style={{ position: "relative", height: 6, background: "var(--panel-3)", borderRadius: 999, overflow: "hidden" }}>
        <div style={{
          position: "absolute", left: `${pct(p.sl)}%`, right: `${100 - pct(p.tp)}%`, top: 0, bottom: 0,
          background: "linear-gradient(90deg, var(--down-soft), var(--accent-soft), var(--up-soft))",
        }}/>
        <SLTick x={pct(p.sl)} color="var(--down)" />
        <SLTick x={pct(p.entry)} color="var(--muted)" />
        <SLTick x={pct(p.current)} color={p.pnlAbs >= 0 ? "var(--up)" : "var(--down)"} big />
        <SLTick x={pct(p.tp)} color="var(--up)" />
      </div>
      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 4, fontSize: 11.5 }}>
        <SLStop label="STOP"   v={p.sl}      color="var(--down)"                                  align="left"/>
        <SLStop label="ENTRY"  v={p.entry}   color="var(--muted)"                                 align="center"/>
        <SLStop label="MARK"   v={p.current} color={p.pnlAbs >= 0 ? "var(--up)" : "var(--down)"} align="center"/>
        <SLStop label="TARGET" v={p.tp}      color="var(--up)"                                    align="right"/>
      </div>
    </div>
  );
}
function SLTick({ x, color, big }) {
  return <span style={{
    position: "absolute", left: `calc(${x}% - ${big ? 5 : 3}px)`,
    top: big ? -3 : -1, bottom: big ? -3 : -1, width: big ? 10 : 6,
    borderRadius: 99, background: color,
    boxShadow: big ? `0 0 0 3px ${color}33` : "none",
  }}/>;
}
function SLStop({ label, v, color, align }) {
  return (
    <div style={{ textAlign: align, color: "var(--muted)" }}>
      <div style={{ fontSize: 10.5, letterSpacing: ".08em" }}>{label}</div>
      <div className="num" style={{ color, fontSize: 12.5, fontWeight: 600 }}>{fmtPrice(v)}</div>
    </div>
  );
}

function PositionPriceChart({ p, series }) {
  const wrapRef = React.useRef(null);
  const [w, setW] = React.useState(400);
  React.useLayoutEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(() => setW(wrapRef.current.clientWidth));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);
  const h = 180, pad = { l: 56, r: 12, t: 10, b: 22 };
  const innerW = Math.max(0, w - pad.l - pad.r);
  const innerH = h - pad.t - pad.b;
  const allVals = [...series, p.sl, p.tp];
  const min = Math.min(...allVals), max = Math.max(...allVals);
  const yPad = (max - min) * 0.06;
  const yMin = min - yPad, yMax = max + yPad;
  const ys = (v) => pad.t + innerH - ((v - yMin) / (yMax - yMin)) * innerH;
  const xs = (i) => pad.l + (i / (series.length - 1)) * innerW;
  const pos = p.pnlAbs >= 0;
  const c = pos ? "var(--up)" : "var(--down)";
  const line = series.map((v, i) => `${i ? "L" : "M"}${xs(i)} ${ys(v)}`).join(" ");
  const area = line + ` L${xs(series.length-1)} ${pad.t + innerH} L${xs(0)} ${pad.t + innerH} Z`;
  return (
    <div ref={wrapRef} style={{ width: "100%" }}>
      <svg width={w} height={h}>
        <defs>
          <linearGradient id={`pf-${p.id}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={c} stopOpacity=".22"/>
            <stop offset="100%" stopColor={c} stopOpacity="0"/>
          </linearGradient>
        </defs>
        {[{ v: p.tp, c: "var(--up)", l: "TP" }, { v: p.entry, c: "var(--muted)", l: "ENTRY", dashed: true }, { v: p.sl, c: "var(--down)", l: "SL" }].map((b, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - pad.r} y1={ys(b.v)} y2={ys(b.v)} stroke={b.c} strokeWidth="1" opacity={b.dashed ? .5 : .7} strokeDasharray={b.dashed ? "3 3" : "none"}/>
            <text x={pad.l - 8} y={ys(b.v) + 3.5} textAnchor="end" fontSize="11" fill={b.c} fontFamily="var(--mono)">{fmtPrice(b.v)}</text>
            <text x={w - pad.r} y={ys(b.v) - 3} textAnchor="end" fontSize="10.5" fill={b.c} letterSpacing=".12em">{b.l}</text>
          </g>
        ))}
        <path d={area} fill={`url(#pf-${p.id})`}/>
        <path d={line} stroke={c} strokeWidth="1.8" fill="none" strokeLinecap="round"/>
        <circle cx={xs(series.length-1)} cy={ys(p.current)} r="4" fill="var(--bg)" stroke={c} strokeWidth="2"/>
      </svg>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                              TRADES TABLE
// ════════════════════════════════════════════════════════════════════════════

function TradesTable({ rows, goToChart, highlightId }) {
  const [sort, setSort] = vUseState({ key: "closedAt", dir: "desc" });
  const sorted = vUseMemo(() => applySort(rows, sort), [rows, sort]);
  const focusRef = React.useRef(null);

  // Scroll the deep-linked trade into view once its row is rendered.
  React.useEffect(() => {
    if (highlightId != null && focusRef.current) {
      focusRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightId, sorted]);

  if (rows.length === 0) {
    return (
      <div style={{ display: "grid", placeItems: "center", padding: 40, color: "var(--muted)", fontSize: 14 }}>
        No trade history
      </div>
    );
  }

  return (
    <div style={{ overflow: "auto", flex: 1, minHeight: 0 }}>
      <table style={TABLE_STYLE}>
        <thead>
          <tr style={{ background: "var(--panel)", position: "sticky", top: 0, zIndex: 1 }}>
            <ColHead sortKey="id" sort={sort} setSort={setSort}>ID</ColHead>
            <ColHead sortKey="openedAt" sort={sort} setSort={setSort}>Opened</ColHead>
            <ColHead sortKey="closedAt" sort={sort} setSort={setSort}>Closed</ColHead>
            <ColHead sortKey="pair" sort={sort} setSort={setSort}>Pair</ColHead>
            <ColHead sortKey="entry" sort={sort} setSort={setSort} align="right">Entry</ColHead>
            <ColHead sortKey="exit" sort={sort} setSort={setSort} align="right">Exit</ColHead>
            <ColHead sortKey="durMin" sort={sort} setSort={setSort} align="right">Duration</ColHead>
            <ColHead sortKey="pnlAbs" sort={sort} setSort={setSort} align="right">PNL €</ColHead>
            <ColHead sortKey="pnlPct" sort={sort} setSort={setSort} align="right">PNL %</ColHead>
            <ColHead sortKey="reason" sort={sort} setSort={setSort}>Exit reason</ColHead>
            <ColHead align="right" style={{ width: 36 }}></ColHead>
          </tr>
        </thead>
        <tbody>
          {sorted.map((t) => {
            const pos = t.pnlAbs >= 0;
            const isFocus = highlightId != null && String(t.id) === String(highlightId);
            return (
              <tr key={t.id} ref={isFocus ? focusRef : undefined}
                  style={isFocus ? { background: "var(--accent-soft)", boxShadow: "inset 2px 0 0 var(--accent)" } : undefined}>
                <td style={{ ...TD, color: "var(--muted)" }} className="num">
                  <span style={{ fontSize: 13 }}>#{t.id}</span>
                </td>
                <td style={TD}>
                  <span style={{ fontSize: 13.3 }}>{fmtTime(t.openedAt)}</span>
                </td>
                <td style={TD}>
                  <div style={{ display: "flex", flexDirection: "column" }}>
                    <span style={{ fontSize: 13.3 }}>{fmtTime(t.closedAt)}</span>
                    <span className="muted" style={{ fontSize: 11.8 }}>{fmtTimeAgo(t.closedAt)}</span>
                  </div>
                </td>
                <td style={TD}><PairLabel pair={t.pair} size={22} onClick={goToChart}/></td>
                <td style={{ ...TD, textAlign: "right" }} className="num">{fmtPrice(t.entry)}</td>
                <td style={{ ...TD, textAlign: "right" }} className="num">{fmtPrice(t.exit)}</td>
                <td style={{ ...TD, textAlign: "right", color: "var(--text-2)" }} className="num">
                  {fmtDuration(t.durMin * 60000)}
                </td>
                <td style={{ ...TD, textAlign: "right" }} className="num">
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: pos ? "var(--up)" : "var(--down)" }}>
                    {fmtSignedUsd(t.pnlAbs)}
                  </span>
                </td>
                <td style={{ ...TD, textAlign: "right" }} className="num">
                  <span style={{ fontSize: 13.5, fontWeight: 600, color: pos ? "var(--up)" : "var(--down)" }}>
                    {fmtPct(t.pnlPct)}
                  </span>
                </td>
                <td style={TD}>
                  <Chip tone={t.reason === "ROI" || t.reason === "Take-profit" ? "up" : t.reason === "Stop-loss" ? "down" : "default"}>
                    {t.reason}
                  </Chip>
                </td>
                <td style={{ ...TD, textAlign: "right", color: "var(--muted)" }}>
                  <Icon name="external" size={13}/>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                                OVERVIEW
// ════════════════════════════════════════════════════════════════════════════

function OverviewView({ data, setTab, isMobile, goToChart, goToTrade }) {
  const { positions, trades, summary, bot, strats, locks, loading } = data;
  const pnlSpark  = vUseMemo(() => summary ? sparkSeries(summary.totalPnl * .6, summary.totalPnl, 40, "pnlspark") : [], [summary]);
  const winSpark  = vUseMemo(() => summary ? sparkSeries(summary.winRate - 6, summary.winRate, 40, "winspark") : [], [summary]);
  const balSpark  = vUseMemo(() => bot ? sparkSeries(bot.balance * .92, bot.balance, 40, "balspark") : [], [bot]);
  const pfSpark   = vUseMemo(() => summary ? sparkSeries(summary.profitFactor * .7, summary.profitFactor, 40, "pfspark") : [], [summary]);

  const [search, setSearch] = vUseState("");
  const [strat, setStrat] = vUseState("All");

  const filtered = vUseMemo(() => positions.filter(p =>
    (strat === "All" || p.strategy === strat) &&
    (!search || p.pair.toLowerCase().includes(search.toLowerCase()) || p.strategy.toLowerCase().includes(search.toLowerCase()))
  ), [positions, search, strat]);

  return (
    <div style={{ display: "grid", gap: "var(--gap)", height: isMobile ? "auto" : "100%", minHeight: 0,
                  gridTemplateRows: isMobile ? "auto" : "auto 1fr" }}>
      <div style={{ display: "grid", gap: "var(--gap)",
                    gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(5, 1fr)" }}>
        <KpiCard label="Total P&L" loading={loading}
                 tone={summary?.totalPnl >= 0 ? "up" : "down"}
                 value={summary ? fmtSignedUsd(summary.totalPnl) : "—"}
                 sub={summary ? `ROI ${fmtPct(summary.roiPct)}` : "—"}
                 spark={pnlSpark} big info="Total closed profit over all time."/>
        <KpiCard label="Unrealized" loading={loading}
                 tone={positions.reduce((a, p) => a + p.pnlAbs, 0) >= 0 ? "up" : "down"}
                 value={fmtSignedUsd(positions.reduce((a, p) => a + p.pnlAbs, 0))}
                 sub={`${positions.length} position${positions.length !== 1 ? "s" : ""}`}/>
        <KpiCard label="Balance" loading={loading}
                 value={bot ? fmtUsd(bot.balance) : "—"}
                 sub={bot ? `${fmtUsd(bot.available)} free · ${fmtUsd(bot.allocated)} alloc` : "—"}
                 spark={balSpark} info="Total equity (including unrealized profit)."/>
        <KpiCard label="Win rate" loading={loading}
                 tone="up"
                 value={summary ? summary.winRate.toFixed(1) + "%" : "—"}
                 sub={summary ? `${summary.wins}W · ${summary.losses}L` : "—"}
                 spark={winSpark} info="Percentage of closed trades that were profitable."/>
        <KpiCard label="Profit factor" loading={loading}
                 value={summary ? summary.profitFactor.toFixed(2) : "—"}
                 sub={summary ? `avg win ${fmtUsd(summary.avgWin)}` : "—"}
                 spark={pfSpark} info="Gross winning profit divided by gross losing profit."
                 style={isMobile ? { gridColumn: "1 / -1" } : undefined}/>
      </div>

      <div style={{ display: "grid", gap: "var(--gap)", minHeight: 0,
                    gridTemplateColumns: isMobile ? "1fr" : "300px 1fr" }}>
        <Card title="Bot status">
          {bot ? <BotStatus bot={bot} trades={trades} locks={locks} setTab={setTab} goToTrade={goToTrade}/> : <div style={{ flex: 1, display: "grid", placeItems: "center" }}><span className="muted" style={{ fontSize: 13 }}>Loading…</span></div>}
        </Card>
        <Card title={`Active positions · ${filtered.length}`}
              sub={bot ? `${bot.usedSlots} of ${bot.openSlots} slots used` : "—"}
              pad={isMobile}
              right={!isMobile && (
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <SearchInput value={search} onChange={setSearch} placeholder="Search pair or strategy"/>
                  <select value={strat} onChange={e => setStrat(e.target.value)}
                    style={{
                      background: "var(--panel-2)", border: "1px solid var(--border-2)", color: "var(--text)",
                      borderRadius: 8, padding: "6px 28px 6px 10px", fontFamily: "inherit", fontSize: 13, appearance: "none",
                      backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%237d869c' d='M0 0h10L5 6z'/></svg>")`,
                      backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center",
                    }}>
                    <option>All</option>
                    {strats.map(s => <option key={s}>{s}</option>)}
                  </select>
                </div>
              )}>
          {isMobile
            ? (filtered.length === 0
                ? <div style={{ padding: "20px 0", color: "var(--muted)", fontSize: 14, textAlign: "center" }}>No open positions</div>
                : filtered.map(p => <MobilePositionCard key={p.id} p={p} onPairClick={goToChart} refresh={data.refresh}/>))
            : <PositionsTable rows={filtered} expandable={true} compact={false} goToChart={goToChart} refresh={data.refresh}/>
          }
        </Card>
      </div>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                               PAIR LOCKS VIEW
// ════════════════════════════════════════════════════════════════════════════

function LocksView({ data, isMobile, goToChart }) {
  const { locks, loading } = data;
  return (
    <div style={{ display: "grid", height: isMobile ? "auto" : "100%", minHeight: 0 }}>
      {loading && !locks?.length
        ? <Card title="Pair locks"><div style={{ flex: 1, display: "grid", placeItems: "center" }}><span className="muted" style={{ fontSize: 13 }}>Loading…</span></div></Card>
        : <PairLocksCard locks={locks || []} refresh={data.refresh} goToChart={goToChart}/>}
    </div>
  );
}

function PairLocksCard({ locks = [], refresh, goToChart }) {
  const [unlocking, setUnlocking] = vUseState(null);
  const onUnlock = async (lockId) => {
    if (lockId == null) return;
    try {
      setUnlocking(lockId);
      const cfg = loadConfig();
      await deleteLock(cfg?.url || "", lockId);
      if (refresh) await refresh();
    } catch (e) {
      console.error("Failed to delete lock", e);
    } finally {
      setUnlocking(null);
    }
  };

  return (
    <Card title="Pair locks" sub={locks.length ? `${locks.length} active` : "None active"} pad={false}>
      {locks.length === 0 ? (
        <div style={{ padding: "16px 18px", color: "var(--muted)", fontSize: 13 }}>No active locks</div>
      ) : (
        <div style={{ overflow: "auto", maxHeight: 240 }}>
          <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0, fontSize: 13.5 }}>
            <thead>
              <tr style={{ background: "var(--panel)", position: "sticky", top: 0, zIndex: 1 }}>
                {["Pair", "Until", "Reason", "Actions"].map((h, i) => (
                  <th key={h} style={{
                    textAlign: i === 3 ? "right" : "left",
                    fontSize: 11.5, fontWeight: 600, letterSpacing: ".09em",
                    textTransform: "uppercase", color: "var(--muted)",
                    borderBottom: "1px solid var(--border)",
                    padding: "10px 14px", whiteSpace: "nowrap",
                    width: i === 0 ? 160 : i === 1 ? 120 : i === 3 ? 120 : undefined,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {locks.map(l => {
                const clickable = goToChart && l.pair && l.pair !== "*";
                return (
                <tr key={l.id ?? l.pair + l.until}
                    onClick={clickable ? () => goToChart(l.pair) : undefined}
                    style={{ cursor: clickable ? "pointer" : "default" }}>
                  <td style={{
                    ...TD, fontSize: 13.5,
                    color: clickable ? "var(--text)" : "var(--text)",
                    textDecoration: clickable ? "none" : "none",
                  }}>{l.pair}{l.side && l.side !== "*" ? ` · ${l.side}` : ""}</td>
                  <td className="num" style={{ ...TD, color: "var(--text-2)" }}>
                    {l.until ? fmtDuration(l.until - Date.now()) : "—"}
                  </td>
                  <td style={{ ...TD, color: "var(--text-2)", maxWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }} title={l.reason}>
                    {humanizeLockReason(l.reason)}
                  </td>
                  <td style={{ ...TD, textAlign: "right" }}>
                    {l.id != null && (
                      <Btn size="sm" tone="danger" icon="x-circle"
                           disabled={unlocking === l.id}
                           onClick={(e) => { e.stopPropagation(); onUnlock(l.id); }}>
                        {unlocking === l.id ? "…" : "Unlock"}
                      </Btn>
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// Freqtrade protection reasons come back as raw log strings like
//   "0.116 passed 0.04 in 96 candles, locking for 96 candles."
// Turn known patterns into something a human can read at a glance. Patterns
// are intentionally permissive (no ^/$ anchors, units optional) so variants
// with min/minutes/candles, different spacing, and trailing text all match.
function humanizeLockReason(raw) {
  if (!raw) return "—";
  const r = String(raw).trim();
  const pct = (x, d = 1) => (parseFloat(x) * 100).toFixed(d) + "%";

  // CooldownPeriod — must be checked first; some variants include numbers.
  if (/cooldown/i.test(r)) return "Cooldown after trade";

  // Strategy / manual force-exit lock
  if (/force[\s-]?exit/i.test(r)) return "Force-exited by strategy";

  // StoplossGuard — "N stoplosses in T min/candles, locking …"
  let m = r.match(/(\d+)\s+stop[\s_-]?losses?\b/i);
  if (m) return `${m[1]} recent stop-losses`;

  // LowProfitPairs — "<profit> < <required> in T …"
  m = r.match(/(-?[\d.]+)\s*<\s*(-?[\d.]+)/);
  if (m) return `Profit ${pct(m[1], 2)} below ${pct(m[2], 2)} threshold`;

  // MaxDrawdown — "<drawdown> passed <max> in N candles/min, locking …"
  m = r.match(/(-?[\d.]+)\s+passed\s+(-?[\d.]+)/i);
  if (m) return `Drawdown ${pct(m[1])} over ${pct(m[2])} limit`;

  // MaxDrawdown variant — "drawdown <X> > <Y>" / "exceeded"
  m = r.match(/drawdown[^\d-]*(-?[\d.]+)[^\d-]+(-?[\d.]+)/i);
  if (m) return `Drawdown ${pct(m[1])} over ${pct(m[2])} limit`;

  // Generic "below/under threshold" phrasing
  m = r.match(/(-?[\d.]+)\s+(?:below|under)\s+(-?[\d.]+)/i);
  if (m) return `Profit ${pct(m[1], 2)} below ${pct(m[2], 2)} threshold`;

  // Generic "exceeded/over" phrasing
  m = r.match(/(-?[\d.]+)\s+(?:exceeded|over|above)\s+(-?[\d.]+)/i);
  if (m) return `Value ${pct(m[1])} over ${pct(m[2])} limit`;

  // Fallback: tidy up — capitalise, drop the trailing "locking for …" clause
  // which is already conveyed by the "Until" column.
  let tidy = r.replace(/,?\s*locking\s+(?:for|pair[^,]*)\s*[^,.]*\.?$/i, "").trim();
  tidy = tidy.replace(/\.$/, "");
  if (tidy.length > 0) tidy = tidy[0].toUpperCase() + tidy.slice(1);
  return tidy || r;
}

function BotStatus({ bot, trades, locks = [], setTab, goToTrade }) {
  const slotPct = bot.openSlots > 0 ? (bot.usedSlots / bot.openSlots) * 100 : 0;
  // Sort by close time descending so "Recent activity" actually shows the most
  // recently closed trades (Freqtrade's /trades response isn't guaranteed sorted).
  const recent = vUseMemo(
    () => [...trades].sort((a, b) => (b.closedAt ?? 0) - (a.closedAt ?? 0)).slice(0, 4),
    [trades]
  );
  // A lock with pair === "*" is a global lock — it blocks new entries on EVERY
  // pair, so it's the most important state to surface at a glance.
  const hasGlobalLock = locks.some(l => l.pair === "*");
  const lockColor = hasGlobalLock ? "var(--down)" : "var(--up)";
  const lockBg    = hasGlobalLock ? "var(--down-soft)" : "var(--up-soft)";
  const lockLine  = hasGlobalLock ? "var(--down-line)" : "var(--up-line)";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18, height: "100%" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <StatusDot kind="up" pulse/>
        <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>Running</span>
          <span className="muted" style={{ fontSize: 12.5 }}>{bot.exchange} · {bot.mode}</span>
        </div>
        <button
          type="button"
          onClick={() => setTab && setTab("locks")}
          title={hasGlobalLock ? "Global lock active — click to manage" : "No global locks — click to view pair locks"}
          style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            width: 30, height: 30, borderRadius: 8,
            background: lockBg, border: `1px solid ${lockLine}`, color: lockColor,
            cursor: "pointer", padding: 0, flexShrink: 0,
          }}>
          <Icon name={hasGlobalLock ? "lock" : "unlock"} size={15}/>
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <Mini label="Exchange" value={bot.exchange}/>
        <Mini label="Mode" value={<Chip tone="accent">{bot.mode}</Chip>}/>
        <Mini label="Stake" value={bot.stake} mono/>
        <Mini label="Slots" value={`${bot.usedSlots} / ${bot.openSlots}`} mono/>
      </div>

      <div>
        <div className="muted" style={{ fontSize: 11.5, letterSpacing: ".09em", textTransform: "uppercase", marginBottom: 6 }}>
          Slot utilization
        </div>
        <div style={{ height: 6, background: "var(--panel-3)", borderRadius: 99, overflow: "hidden" }}>
          <div style={{ width: slotPct + "%", height: "100%", background: "linear-gradient(90deg, var(--accent), var(--up))" }}/>
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <div className="muted" style={{ fontSize: 11.5, letterSpacing: ".09em", textTransform: "uppercase", marginBottom: 8 }}>
          Recent activity
        </div>
        {recent.length === 0 ? <span className="muted" style={{ fontSize: 13 }}>No recent trades</span> : (
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {recent.map(t => (
              <div key={t.id}
                   onClick={goToTrade ? () => goToTrade(t.id) : undefined}
                   title={goToTrade ? "View trade in history" : undefined}
                   style={{
                     display: "flex", alignItems: "center", gap: 10,
                     padding: "8px 0", borderBottom: "1px solid var(--border)",
                     cursor: goToTrade ? "pointer" : "default",
                   }}>
                <PairToken pair={t.pair} size={20}/>
                <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: 13 }}>{t.pair}</span>
                  <span className="muted" style={{ fontSize: 11.8 }}>closed · {t.reason} · {fmtTimeAgo(t.closedAt)}</span>
                </div>
                <span className="num" style={{ fontSize: 13, fontWeight: 600, color: t.pnlAbs >= 0 ? "var(--up)" : "var(--down)" }}>
                  {fmtPct(t.pnlPct)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Mini({ label, value, mono }) {
  return (
    <div style={{ background: "var(--panel-2)", border: "1px solid var(--border)", borderRadius: 8, padding: "8px 10px", display: "flex", flexDirection: "column", gap: 2 }}>
      <span className="muted" style={{ fontSize: 11.5, letterSpacing: ".06em", textTransform: "uppercase" }}>{label}</span>
      <span className={mono ? "num" : ""} style={{ fontSize: 13.5, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                               POSITIONS VIEW
// ════════════════════════════════════════════════════════════════════════════

function PositionsView({ data, goToChart }) {
  const { positions, strats, bot, loading } = data;
  const [search, setSearch] = vUseState("");
  const [strat, setStrat] = vUseState("All");

  const filtered = vUseMemo(() => positions.filter(p =>
    (strat === "All" || p.strategy === strat) &&
    (!search || p.pair.toLowerCase().includes(search.toLowerCase()) || p.strategy.toLowerCase().includes(search.toLowerCase()))
  ), [positions, search, strat]);

  const totalPnl = filtered.reduce((a, p) => a + p.pnlAbs, 0);
  const totalNotional = filtered.reduce((a, p) => a + p.notional, 0);
  const wins = filtered.filter(p => p.pnlAbs >= 0).length;

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto 1fr", gap: "var(--gap)", height: "100%", minHeight: 0 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "var(--gap)" }}>
        <KpiCard label="Open positions" loading={loading} value={filtered.length} sub={bot ? `${bot.openSlots - filtered.length} slots free` : "—"}/>
        <KpiCard label="Unrealized P&L" loading={loading} tone={totalPnl >= 0 ? "up" : "down"}
                 value={fmtSignedUsd(totalPnl)} sub={`across ${filtered.length} positions`}/>
        <KpiCard label="Total exposure" loading={loading}
                 value={fmtUsd(totalNotional)}
                 sub={bot ? `${((totalNotional / (bot.balance || 1)) * 100).toFixed(1)}% of wallet` : "—"}/>
        <KpiCard label="Winners" loading={loading}
                 value={`${wins} / ${filtered.length}`}
                 sub={filtered.length ? `${((wins / filtered.length) * 100).toFixed(0)}% currently in profit` : "—"}
                 tone={filtered.length && wins / filtered.length >= 0.5 ? "up" : undefined}/>
      </div>

      <Card pad={false} title="All positions" sub="Click any row to expand"
            right={
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <SearchInput value={search} onChange={setSearch} placeholder="Search pair or strategy"/>
                <select value={strat} onChange={e => setStrat(e.target.value)}
                  style={{
                    background: "var(--panel-2)", border: "1px solid var(--border-2)", color: "var(--text)",
                    borderRadius: 8, padding: "6px 28px 6px 10px", fontFamily: "inherit", fontSize: 13, appearance: "none",
                    backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%237d869c' d='M0 0h10L5 6z'/></svg>")`,
                    backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center",
                  }}>
                  <option>All</option>
                  {strats.map(s => <option key={s}>{s}</option>)}
                </select>
                <Btn icon="download" size="sm" tone="ghost">Export</Btn>
              </div>
            }>
        <PositionsTable rows={filtered} goToChart={goToChart} refresh={data.refresh}/>
      </Card>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                                TRADES VIEW
// ════════════════════════════════════════════════════════════════════════════

function TradesView({ data, isMobile, goToChart, focusTradeId, clearFocus }) {
  const { trades, strats, loading } = data;
  const [search, setSearch] = vUseState("");
  const [strat, setStrat] = vUseState("All");
  const [result, setResult] = vUseState("All");
  // When deep-linked to a specific trade, widen the window so it can't be
  // filtered out, and remember which row to highlight.
  const [range, setRange] = vUseState(focusTradeId != null ? "All" : "30d");
  const [highlightId] = vUseState(focusTradeId ?? null);

  // Consume the deep-link once so revisiting the tab doesn't re-highlight.
  React.useEffect(() => { if (focusTradeId != null && clearFocus) clearFocus(); }, []);

  const filtered = vUseMemo(() => {
    const now = Date.now();
    const cutoff = range === "24h" ? now - 86400_000 : range === "7d" ? now - 7*86400_000 : range === "30d" ? now - 30*86400_000 : 0;
    return trades.filter(t =>
      (!search || t.pair.toLowerCase().includes(search.toLowerCase()) || t.strategy.toLowerCase().includes(search.toLowerCase()) || t.id.includes(search)) &&
      (strat === "All" || t.strategy === strat) &&
      (result === "All" || (result === "Wins" ? t.pnlAbs > 0 : t.pnlAbs <= 0)) &&
      (cutoff === 0 || t.closedAt >= cutoff)
    );
  }, [trades, search, strat, result, range]);

  const totalPnl = filtered.reduce((a, t) => a + t.pnlAbs, 0);
  const wins = filtered.filter(t => t.pnlAbs > 0);
  const winRate = filtered.length ? (wins.length / filtered.length) * 100 : 0;
  const avgDur = filtered.length ? filtered.reduce((a, t) => a + t.durMin, 0) / filtered.length : 0;

  const exportCsv = () => {
    const header = "ID,Pair,Strategy,Entry,Exit,Duration (min),PnL ($),PnL (%),Exit reason,Closed at\n";
    const rows = filtered.map(t =>
      [t.id, t.pair, t.strategy, t.entry, t.exit, t.durMin, t.pnlAbs.toFixed(2), t.pnlPct.toFixed(2), t.reason, new Date(t.closedAt).toISOString()].join(",")
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `trades_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
  };

  return (
    <div style={{ display: "grid", gap: "var(--gap)", height: isMobile ? "auto" : "100%", minHeight: 0,
                  gridTemplateRows: isMobile ? "auto" : "auto 1fr" }}>
      <div style={{ display: "grid", gap: "var(--gap)",
                    gridTemplateColumns: isMobile ? "1fr 1fr" : "repeat(4, 1fr)" }}>
        <KpiCard label="Trades" loading={loading} value={filtered.length} sub={`window · ${range}`}/>
        <KpiCard label="Realized P&L" loading={loading} tone={totalPnl >= 0 ? "up" : "down"}
                 value={fmtSignedUsd(totalPnl)}
                 sub={`avg ${fmtSignedUsd(totalPnl / (filtered.length || 1))}`}/>
        <KpiCard label="Win rate" loading={loading} tone="up" value={winRate.toFixed(1) + "%"}
                 sub={`${wins.length}W · ${filtered.length - wins.length}L`}/>
        <KpiCard label="Avg duration" loading={loading}
                 value={fmtDuration(avgDur * 60000)} sub="per trade"/>
      </div>

      {isMobile && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Segmented value={range} options={["24h","7d","30d","All"]} onChange={setRange} size="sm"/>
          <Segmented value={result} options={["All","Wins","Losses"]} onChange={setResult} size="sm"/>
        </div>
      )}

      <Card pad={isMobile} title="Trade history" sub={`${filtered.length} of ${trades.length} trades`}
            right={!isMobile && (
              <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <Segmented value={range} options={["24h","7d","30d","All"]} onChange={setRange} size="sm"/>
                <Segmented value={result} options={["All","Wins","Losses"]} onChange={setResult} size="sm"/>
                <SearchInput value={search} onChange={setSearch} placeholder="Pair, strategy, or ID"/>
                <Btn icon="download" size="sm" tone="ghost" onClick={exportCsv}>Export CSV</Btn>
              </div>
            )}>
        {isMobile
          ? (filtered.length === 0
              ? <div style={{ padding: "20px 0", color: "var(--muted)", fontSize: 14, textAlign: "center" }}>No trades</div>
              : filtered.map(t => <MobileTradeCard key={t.id} t={t} onPairClick={goToChart}
                  highlight={highlightId != null && String(t.id) === String(highlightId)}/>))
          : <TradesTable rows={filtered} goToChart={goToChart} highlightId={highlightId}/>
        }
      </Card>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                              PERFORMANCE VIEW
// ════════════════════════════════════════════════════════════════════════════

function PerformanceView({ data, timeRange, setTimeRange, isMobile, goToChart }) {
  const { equity, daily, summary, bot, trades, positions, loading } = data;

  const s = summary;

  return (
    <div style={{ display: "grid", gap: "var(--gap)", minHeight: 0,
                  gridTemplateRows: "auto auto auto" }}>
      
      <div style={{ display: "grid", gap: "var(--gap)", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr" }}>
        
        {/* FINANCIALS */}
        <Card title="Financial Performance" sub="All-time bottom line">
          {loading || !s ? <div className="skeleton" style={{ height: 132, width: "100%" }}/> : (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div className="num" style={{ fontSize: isMobile ? 32 : 44, fontWeight: 600, color: (s.totalPnl + (positions?.reduce((a,p)=>a+p.pnlAbs,0)||0)) >= 0 ? "var(--up)" : "var(--down)", letterSpacing: "-.015em", lineHeight: 1.1 }}>
                {fmtSignedUsd(s.totalPnl + (positions?.reduce((a,p)=>a+p.pnlAbs,0)||0))}
              </div>
              
              <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", borderTop: "1px dashed var(--border)", paddingTop: 16 }}>
                <div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Closed Profit</div>
                  <div className="num" style={{ fontSize: 16, fontWeight: 500, color: s.totalPnl >= 0 ? "var(--up)" : "var(--down)" }}>
                    {fmtSignedUsd(s.totalPnl)}
                  </div>
                </div>
                <div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Unrealized</div>
                  <div className="num" style={{ fontSize: 16, fontWeight: 500, color: (positions?.reduce((a, p) => a + p.pnlAbs, 0) >= 0) ? "var(--up)" : "var(--down)" }}>
                    {positions ? fmtSignedUsd(positions.reduce((a, p) => a + p.pnlAbs, 0)) : "—"}
                  </div>
                </div>
                <div>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>Trades</div>
                  <div className="num" style={{ fontSize: 16, fontWeight: 500 }}>
                    {s.trades}
                  </div>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* STRATEGY */}
        <Card title="Strategy Metrics" sub="Win rate & expectancy">
          {loading || !s ? <div className="skeleton" style={{ height: 132, width: "100%" }}/> : (
            <div style={{ display: "flex", alignItems: "center", gap: 24, flex: 1, minHeight: 0 }}>
              <WinLossDonut wins={s.wins} losses={s.losses} size={isMobile ? 100 : 132} stroke={isMobile ? 11 : 14}/>
              <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
                <SplitRow color="var(--accent)" label="Profit Factor" count={s.profitFactor.toFixed(2)} sub="gross win ÷ gross loss" />
                <SplitRow color="var(--up)" label="Expectancy" count={fmtSignedUsd((s.avgWin * s.winRate + s.avgLoss * s.lossRate) / 100)} sub="avg per trade" />
                <SplitRow color="var(--muted)" label="Avg Win / Loss" count={`${fmtUsd(s.avgWin)} / ${fmtUsd(Math.abs(s.avgLoss))}`} sub="winning vs losing" />
              </div>
            </div>
          )}
        </Card>
      </div>

      <div style={{ display: "grid", gap: "var(--gap)", minHeight: 0,
                    gridTemplateColumns: isMobile ? "1fr" : "1.5fr 1fr" }}>
        <Card title="Equity curve" sub="Wallet value over time"
              right={<Segmented value={timeRange} options={["24h","7d","30d","All"]} onChange={setTimeRange} size="sm"/>}>
          <EquityChart data={equity} height={isMobile ? 160 : 200}/>
        </Card>
        <Card title="Daily P&L" sub="Last 30 days">
          <DailyBars data={daily} height={isMobile ? 140 : 200}/>
        </Card>
      </div>

      <Card title="Best & worst trades">
        {s ? <BestWorst summary={s} goToChart={goToChart}/> : <div className="skeleton" style={{ height: 80, width: "100%" }}/>}
      </Card>
    </div>
  );
}

function calcSharpe(daily) {
  if (daily.length < 2) return 0;
  const vals = daily.map(d => d.v);
  const mean = vals.reduce((a, v) => a + v, 0) / vals.length;
  const variance = vals.reduce((a, v) => a + (v - mean) ** 2, 0) / vals.length;
  const std = Math.sqrt(variance) || 1;
  return (mean / std) * Math.sqrt(252);
}

function SplitRow({ color, label, count, sub }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ width: 8, height: 8, background: color, borderRadius: 99, boxShadow: `0 0 0 3px ${color}22`, flexShrink: 0 }}/>
      <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <span style={{ fontSize: 13.5, fontWeight: 500 }}>{label}</span>
          <span className="num" style={{ fontSize: 15, fontWeight: 600 }}>{count}</span>
        </div>
        <span className="muted" style={{ fontSize: 12 }}>{sub}</span>
      </div>
    </div>
  );
}

function StrategyTable({ stats }) {
  const [sort, setSort] = vUseState({ key: "pnl", dir: "desc" });
  const rows = vUseMemo(() => applySort(stats, sort), [stats, sort]);
  const maxPnl = Math.max(...stats.map(s => Math.abs(s.pnl))) || 1;
  return (
    <div style={{ overflow: "auto", flex: 1, minHeight: 0 }}>
      <table style={TABLE_STYLE}>
        <thead>
          <tr style={{ background: "var(--panel)", position: "sticky", top: 0, zIndex: 1 }}>
            <ColHead sortKey="name" sort={sort} setSort={setSort}>Strategy</ColHead>
            <ColHead sortKey="trades" sort={sort} setSort={setSort} align="right">Trades</ColHead>
            <ColHead sortKey="winRate" sort={sort} setSort={setSort} align="right">Win rate</ColHead>
            <ColHead sortKey="avgPct" sort={sort} setSort={setSort} align="right">Avg %</ColHead>
            <ColHead sortKey="pnl" sort={sort} setSort={setSort} align="right">P&amp;L</ColHead>
            <ColHead style={{ minWidth: 120 }}></ColHead>
          </tr>
        </thead>
        <tbody>
          {rows.map(s => (
            <tr key={s.name}>
              <td style={TD}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ width: 6, height: 24, background: s.pnl >= 0 ? "var(--up)" : "var(--down)", borderRadius: 2 }}/>
                  <span style={{ fontSize: 13.5, fontWeight: 500 }}>{s.name}</span>
                </div>
              </td>
              <td style={{ ...TD, textAlign: "right", color: "var(--text-2)" }} className="num">{s.trades}</td>
              <td style={{ ...TD, textAlign: "right" }} className="num">{s.winRate.toFixed(1)}%</td>
              <td style={{ ...TD, textAlign: "right" }}>
                <span className="num" style={{ color: s.avgPct >= 0 ? "var(--up)" : "var(--down)" }}>{fmtPct(s.avgPct)}</span>
              </td>
              <td style={{ ...TD, textAlign: "right" }}>
                <span className="num" style={{ fontWeight: 600, color: s.pnl >= 0 ? "var(--up)" : "var(--down)" }}>
                  {fmtSignedUsd(s.pnl)}
                </span>
              </td>
              <td style={TD}>
                <BarTrace v={s.pnl} max={maxPnl}/>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BarTrace({ v, max }) {
  const pct = (Math.abs(v) / max) * 100;
  const pos = v >= 0;
  return (
    <div style={{ position: "relative", height: 6, background: "var(--panel-3)", borderRadius: 99, overflow: "hidden", minWidth: 100 }}>
      <span style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--border-2)" }}/>
      <span style={{
        position: "absolute", top: 0, bottom: 0,
        left: pos ? "50%" : `calc(50% - ${pct / 2}%)`,
        width: `${pct / 2}%`,
        background: pos ? "var(--up)" : "var(--down)",
      }}/>
    </div>
  );
}

function BestWorst({ summary: s, goToChart }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, flex: 1, minHeight: 0 }}>
      {s.best  && <BW row={s.best}  kind="up"   title="Best trade"  goToChart={goToChart}/>}
      {s.worst && <BW row={s.worst} kind="down" title="Worst trade" goToChart={goToChart}/>}
    </div>
  );
}

function BW({ row, kind, title, goToChart }) {
  return (
    <div
      onClick={goToChart ? () => goToChart(row.pair) : undefined}
      style={{
        padding: 12, borderRadius: 10,
        background: kind === "up" ? "var(--up-soft)" : "var(--down-soft)",
        border: `1px solid ${kind === "up" ? "var(--up-line)" : "var(--down-line)"}`,
        display: "flex", flexDirection: "column", gap: 6,
        cursor: goToChart ? "pointer" : "default",
      }}>
      <span style={{ fontSize: 11.5, letterSpacing: ".08em", textTransform: "uppercase", color: kind === "up" ? "var(--up)" : "var(--down)", fontWeight: 600 }}>{title}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <PairToken pair={row.pair} size={22}/>
        <span style={{ fontSize: 13.5, fontWeight: 500 }}>{row.pair}</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span className="num" style={{ fontSize: 19, fontWeight: 600, color: kind === "up" ? "var(--up)" : "var(--down)" }}>
          {fmtSignedUsd(row.pnlAbs)}
        </span>
        <span className="num" style={{ fontSize: 13, color: kind === "up" ? "var(--up)" : "var(--down)", opacity: .85 }}>
          {fmtPct(row.pnlPct)}
        </span>
      </div>
    </div>
  );
}

// ── Signals view ──────────────────────────────────────────────────────────────
// Per-pair live indicator state for the active strategy. Reads /api/v1/pair_candles
// per pair and /api/v1/plot_config to discover indicator columns automatically.
// No per-strategy config needed: columns come from the strategy's plot_config and
// "READY" is driven by the enter_long (or legacy buy) column in the analyzed candle.

const isOne = (v) => v === 1 || v === 1.0 || v === "1" || v === true;

// Freqtrade OHLCV and system columns — never treated as strategy indicators.
const SIGNAL_SKIP_COLS = new Set([
  "date", "open", "high", "low", "close", "volume",
  "enter_long", "exit_long", "enter_short", "exit_short",
  "enter_tag", "exit_tag",
  "buy", "sell", "buy_tag",
]);

// Snake_case column name → readable label with known abbreviations uppercased.
function fmtColLabel(col) {
  return col
    .replace(/_/g, " ")
    .replace(/\b(ema|rsi|macd|mfi|adx|atr|cci|sma|wma|bb|kc|kelt|btc)\b/gi, s => s.toUpperCase())
    .replace(/\b(\w)/g, c => c.toUpperCase());
}

// Infer display type from actual candle values across multiple pairs.
function classifyCol(col, candles, inMainPlot) {
  const vals = candles.map(c => c[col]).filter(v => v != null);
  if (!vals.length) return inMainPlot ? "price" : "decimal";
  if (vals.every(v => v === 0 || v === 1 || v === true || v === false)) return "binary";
  return inMainPlot ? "price" : "decimal";
}

// Build signal definitions from plot_config + candle data — no per-strategy code needed.
// Falls back to all non-system candle columns (capped at 12, binary-first) if no plot_config.
function buildSignalDefs(plotCfg, rows) {
  const candles = rows.filter(r => r.ok && r.data?.candle).map(r => r.data.candle);
  const defs = [];
  const seen = new Set();

  function addCol(col, sub, inMainPlot) {
    if (seen.has(col) || SIGNAL_SKIP_COLS.has(col)) return;
    if (candles.length && !(col in candles[0])) return;
    seen.add(col);
    const type = classifyCol(col, candles, inMainPlot);
    defs.push({
      key: col, label: fmtColLabel(col), sub,
      type,
      getValue: (c) => c[col],
      isFired: type === "binary" ? (c) => isOne(c[col]) : () => false,
    });
  }

  const hasPlotCfg = plotCfg && (
    Object.keys(plotCfg.main_plot || {}).length + Object.keys(plotCfg.subplots || {}).length > 0
  );

  if (hasPlotCfg) {
    for (const col of Object.keys(plotCfg.main_plot || {})) addCol(col, "overlay", true);
    for (const [name, cols] of Object.entries(plotCfg.subplots || {})) {
      for (const col of Object.keys(cols || {})) addCol(col, name, false);
    }
  }

  return defs;
}

// True if the strategy is signaling a long entry on this candle.
function getEntrySignal(c) {
  if (c.enter_long != null) return isOne(c.enter_long);
  if (c.buy != null) return isOne(c.buy);
  return false;
}

function SignalsView({ data, baseUrl, isMobile, goToChart }) {
  const stratName = data?.bot?.strategy || data?.strats?.[0] || null;
  const timeframe = data?.bot?.timeframe || "4h";

  const [signals, setSignals] = vUseState({
    loading: true, rows: [], plotCfg: null, lastUpdated: null, error: null,
  });

  const refresh = React.useCallback(async () => {
    if (!baseUrl) return;
    setSignals(s => ({ ...s, loading: true, error: null }));
    try {
      const [pairs, plotCfg] = await Promise.all([
        fetchWhitelist(baseUrl),
        fetchPlotConfig(baseUrl),
      ]);
      const rows = await fetchAllPairSignals(baseUrl, pairs, timeframe);
      setSignals({ loading: false, rows, plotCfg, lastUpdated: Date.now(), error: null });
    } catch (e) {
      setSignals(s => ({ ...s, loading: false, error: e.message || "Failed to load signals" }));
    }
  }, [baseUrl, timeframe]);

  React.useEffect(() => {
    refresh();
    // Candles update at most every `timeframe`; polling every minute is plenty.
    const id = setInterval(refresh, 60_000);
    return () => clearInterval(id);
  }, [refresh]);

  const signalDefs = vUseMemo(
    () => buildSignalDefs(signals.plotCfg, signals.rows),
    [signals.plotCfg, signals.rows]
  );

  const processed = vUseMemo(() => signals.rows.map(r => {
    if (!r.ok || !r.data?.candle) return { pair: r.pair, ok: false, error: r.error };
    const c = r.data.candle;
    const cells = signalDefs.map(def => ({
      key: def.key, label: def.label, type: def.type,
      value: def.getValue(c), on: def.isFired(c),
    }));
    const binaryFired = cells.filter(x => x.on).length;
    const binaryTotal = cells.filter(x => x.type === "binary").length;
    return {
      pair: r.pair, ok: true, candle: c,
      close: c.close, rsi: c.rsi,
      cells, fired: binaryFired, total: binaryTotal,
      ready: getEntrySignal(c),
      lastAnalyzed: r.data.lastAnalyzed,
    };
  }), [signals.rows, signalDefs]);

  // Sort: entry signal first, then most binary signals on, then most oversold by RSI, errors last.
  const sorted = vUseMemo(() => {
    const arr = [...processed];
    arr.sort((a, b) => {
      if (!a.ok && !b.ok) return 0;
      if (!a.ok) return 1;
      if (!b.ok) return -1;
      if (a.ready !== b.ready) return a.ready ? -1 : 1;
      if (b.fired !== a.fired) return b.fired - a.fired;
      return (a.rsi ?? 100) - (b.rsi ?? 100);
    });
    return arr;
  }, [processed]);

  const readyCount = processed.filter(p => p.ok && p.ready).length;
  const hasPlotCfg = signals.plotCfg != null && (
    Object.keys(signals.plotCfg?.main_plot || {}).length +
    Object.keys(signals.plotCfg?.subplots || {}).length > 0
  );
  const subtitle = `${stratName || "—"} · ${timeframe} · ${processed.length} pair${processed.length === 1 ? "" : "s"} · ${readyCount} entry signal${readyCount === 1 ? "" : "s"}`;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <Card
        title="Entry signals"
        sub={subtitle}
        right={(
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {signals.lastUpdated && (
              <span className="muted" style={{ fontSize: 12.5 }}>
                Updated {fmtTimeAgo(signals.lastUpdated)}
              </span>
            )}
            <Btn icon="refresh" tone="ghost" size="sm" onClick={refresh} disabled={signals.loading}>
              {signals.loading ? "Loading…" : "Refresh"}
            </Btn>
          </div>
        )}
        pad={false}
      >
        {signals.rows.length > 0 && !hasPlotCfg && (
          <div style={{
            margin: "12px 18px", padding: "9px 12px",
            background: "rgba(255,183,74,.12)", border: "1px solid rgba(255,183,74,.32)",
            color: "var(--warn)", borderRadius: 8, fontSize: 13,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <Icon name="warn" size={14}/>
            No <code>plot_config</code> defined for <strong style={{ fontFamily: "var(--mono)" }}>{stratName}</strong>.
            Add a <code>plot_config</code> to your strategy to show indicator columns here.
          </div>
        )}

        {signals.error && (
          <div style={{
            margin: "12px 18px", padding: "9px 12px",
            background: "var(--down-soft)", border: "1px solid var(--down-line)",
            color: "var(--down)", borderRadius: 8, fontSize: 13.5,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <Icon name="warn" size={14}/>
            {signals.error}
          </div>
        )}

        {signals.loading && !processed.length ? (
          <div style={{ padding: "24px 18px" }}>
            <span className="muted" style={{ fontSize: 13 }}>Loading per-pair signals…</span>
          </div>
        ) : !processed.length ? (
          <div style={{ padding: "24px 18px" }}>
            <span className="muted" style={{ fontSize: 13 }}>No pairs in the bot's whitelist.</span>
          </div>
        ) : isMobile ? (
          <div style={{ padding: "0 14px" }}>
            {sorted.map(r => <MobileSignalCard key={r.pair} r={r} onPairClick={goToChart}/>)}
          </div>
        ) : (
          <div style={{ overflow: "auto" }}>
            <table style={TABLE_STYLE}>
              <thead>
                <tr style={{ background: "var(--panel)", position: "sticky", top: 0, zIndex: 1 }}>
                  <SignalHeaderCell label="Pair"   align="left"  w={180}/>
                  <SignalHeaderCell label="Close"  align="right" w={110}/>
                  {signalDefs.map(def => (
                    <SignalHeaderCell key={def.key}
                      label={def.label}
                      sub={def.sub}
                      align={def.type === "binary" ? "center" : "right"}
                      w={def.type === "price" ? 130 : 110}/>
                  ))}
                  <SignalHeaderCell label="Signal" align="right" w={140}/>
                </tr>
              </thead>
              <tbody>
                {sorted.map(r => <SignalRow key={r.pair} r={r} goToChart={goToChart}/>)}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function SignalHeaderCell({ label, sub, align, w }) {
  return (
    <th style={{
      textAlign: align,
      fontSize: 11.5, fontWeight: 600, letterSpacing: ".09em",
      textTransform: "uppercase", color: "var(--muted)",
      borderBottom: "1px solid var(--border)",
      padding: "10px 14px", whiteSpace: "nowrap", width: w,
    }}>
      <div style={{
        display: "flex", flexDirection: "column", gap: 2,
        alignItems: align === "right" ? "flex-end" : align === "center" ? "center" : "flex-start",
      }}>
        <span>{label}</span>
        {sub && (
          <span style={{ fontSize: 10.5, letterSpacing: ".05em", color: "var(--dim)", textTransform: "none", fontWeight: 400 }}>
            {sub}
          </span>
        )}
      </div>
    </th>
  );
}

function SignalRow({ r, goToChart }) {
  if (!r.ok) {
    return (
      <tr>
        <td style={TD}><PairLabel pair={r.pair} size={22} onClick={goToChart}/></td>
        <td colSpan={99} style={{ ...TD, color: "var(--muted)" }}>
          — {r.error || "no candle data"}
        </td>
      </tr>
    );
  }
  const bg = r.ready ? "rgba(42,208,123,.05)" : undefined;
  const summaryText = r.ready ? "ENTRY" : r.total > 0 ? `${r.fired}/${r.total}` : "—";
  const summaryTone = r.ready ? "up" : (r.fired > 0 && r.total > 0) ? "warn" : "default";
  return (
    <tr style={{ background: bg }}>
      <td style={TD}><PairLabel pair={r.pair} size={22} onClick={goToChart}/></td>
      <td className="num" style={{ ...TD, textAlign: "right" }}>
        {r.close != null ? fmtPrice(r.close) : "—"}
      </td>
      {r.cells.map(cell => <SignalCell key={cell.key} cell={cell}/>)}
      <td style={{ ...TD, textAlign: "right" }}>
        <Chip tone={summaryTone}>{summaryText}</Chip>
      </td>
    </tr>
  );
}

function SignalCell({ cell }) {
  if (cell.type === "binary") {
    if (cell.value == null) {
      return <td style={{ ...TD, textAlign: "center", color: "var(--muted)" }}>—</td>;
    }
    return (
      <td style={{ ...TD, textAlign: "center" }}>
        <Chip tone={cell.on ? "up" : "default"}>{cell.on ? "ON" : "OFF"}</Chip>
      </td>
    );
  }
  if (cell.value == null) {
    return <td style={{ ...TD, textAlign: "right", color: "var(--muted)" }}>—</td>;
  }
  const txt = cell.type === "price" ? fmtPrice(cell.value) : Number(cell.value).toFixed(1);
  return (
    <td className="num" style={{
      ...TD, textAlign: "right",
      color: cell.on ? "var(--up)" : "var(--text-2)",
      fontWeight: cell.on ? 600 : 400,
    }}>{txt}</td>
  );
}

// ════════════════════════════════════════════════════════════════════════════
//                              CHART VIEW
// ════════════════════════════════════════════════════════════════════════════
// Renders the strategy's plot_config exactly as the strategy author defined it:
//   • plot_config.main_plot.<col>  → line overlay on the main candle chart
//   • plot_config.subplots.<name>  → its own small SVG sub-panel below
// No auto-detection, no defaults — only what the strategy declares.

// ── Timestamp helper ─────────────────────────────────────────────────────────
// Freqtrade returns dates in milliseconds; LW Charts wants seconds.
function toTimeSec(d) {
  if (typeof d === "string") return Math.floor(new Date(d).getTime() / 1000);
  if (typeof d === "number") return d > 1e12 ? Math.floor(d / 1000) : Math.floor(d);
  return 0;
}

// Returns true if every non-null value of `col` in `rows` is exactly 0 or 1.
// Binary "regime filter" indicators (e.g. btc_uptrend_4h) authors sometimes
// drop into plot_config.main_plot — drawing those as a price line is
// meaningless and squishes the candles, so we render them as ON/OFF in the
// legend instead.
function isBinaryColumn(rows, col) {
  let seen = false;
  for (const r of rows) {
    const v = r[col];
    if (v == null) continue;
    seen = true;
    if (v !== 0 && v !== 1 && v !== true && v !== false) return false;
  }
  return seen;
}

// Fallback color cycles when plot_config entries omit `color`.
const FALLBACK_OVERLAY_COLORS = [
  "rgba(255,183,74,0.85)", "rgba(180,100,255,0.80)", "rgba(100,190,255,0.80)",
  "rgba(255,93,108,0.80)", "rgba(42,208,123,0.80)", "rgba(255,140,200,0.80)",
];
const FALLBACK_SUBPLOT_COLORS = ["#b6becf","#ffb74a","#2bd4c5","#a77cff","#ff79c6","#5eead4","#fb923c"];

// Normalize plot_config colors → CSS-acceptable strings.
// Freqtrade strategies often write hex (#fff), named ("red"), or rgba(...).
// LW Charts and SVG both accept all of these directly; we just trim whitespace.
function normalizeColor(c, fallback) {
  if (!c || typeof c !== "string") return fallback;
  return c.trim();
}

// Up / down RGB triples — mirror the --up / --down CSS vars, since
// LightweightCharts can't resolve CSS custom properties.
const UP_RGB = "42,208,123";
const DOWN_RGB = "255,93,108";

function toHeikinAshi(sorted) {
  const ha = [];
  for (let i = 0; i < sorted.length; i++) {
    const r = sorted[i];
    const haClose = (r.open + r.high + r.low + r.close) / 4;
    const haOpen  = i === 0
      ? (r.open + r.close) / 2
      : (ha[i - 1].open + ha[i - 1].close) / 2;
    const haHigh  = Math.max(r.high, haOpen, haClose);
    const haLow   = Math.min(r.low,  haOpen, haClose);
    ha.push({ ...r, open: haOpen, high: haHigh, low: haLow, close: haClose });
  }
  return ha;
}

// Hidden full-height histogram that shades the chart background green when a
// binary 0/1 column is ON, red when OFF (e.g. regime filters like btc_uptrend_4h).
function addBinaryBgSeries(chart, scaleId, rows, col, t) {
  const series = chart.addHistogramSeries({
    priceScaleId: scaleId,
    lastValueVisible: false,
    priceLineVisible: false,
    crosshairMarkerVisible: false,
    base: 0,
  });
  chart.priceScale(scaleId).applyOptions({ scaleMargins: { top: 0, bottom: 0 }, visible: false });
  series.setData(rows.map(r => ({
    time: t(r),
    value: 1,
    color: isOne(r[col]) ? `rgba(${UP_RGB},0.10)` : `rgba(${DOWN_RGB},0.10)`,
  })));
  return series;
}

// ── CandleChart ──────────────────────────────────────────────────────────────
// Uses plot_config.main_plot to drive which extra series to overlay.
// `positions` is an array of open positions for the selected pair, used to
// draw horizontal Entry / SL / TP price lines on the candle series.
function CandleChart({ data, mainPlot, positions, heikinAshi }) {
  const containerRef  = React.useRef(null);
  const chartRef      = React.useRef(null);
  const baseSeriesRef = React.useRef(null);   // { candles, volume }
  const linesRef      = React.useRef(new Map()); // col → LW series
  const priceLinesRef = React.useRef([]);     // open-position price lines
  const viewKeyRef    = React.useRef(null);   // pair|timeframe the viewport was set for

  React.useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el || !window.LightweightCharts) return;
    const LC = window.LightweightCharts;

    const style = getComputedStyle(document.documentElement);
    const bg = style.getPropertyValue("--panel").trim() || "#10172a";
    const text = style.getPropertyValue("--text-2").trim() || "#b6becf";
    const gridLine = style.getPropertyValue("--border-2").trim() || "rgba(255,255,255,0.04)";

    const chart = LC.createChart(el, {
      width:  Math.max(el.clientWidth,  300),
      height: Math.max(el.clientHeight, 300),
      layout: { background: { type: "solid", color: bg }, textColor: text, fontSize: 12 },
      grid: {
        vertLines: { color: gridLine },
        horzLines: { color: gridLine },
      },
      crosshair: { mode: LC.CrosshairMode.Normal },
      rightPriceScale: { borderColor: gridLine, scaleMargins: { top: 0.06, bottom: 0.20 } },
      timeScale: { borderColor: gridLine, timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;

    const candles = chart.addCandlestickSeries({
      upColor: "#2ad07b", downColor: "#ff5d6c",
      borderUpColor: "#2ad07b", borderDownColor: "#ff5d6c",
      wickUpColor: "#2ad07b", wickDownColor: "#ff5d6c",
    });
    const volume = chart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "vol" });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.80, bottom: 0 } });
    baseSeriesRef.current = { candles, volume };

    const ro = new ResizeObserver(entries => {
      for (const e of entries) {
        const { width, height } = e.contentRect;
        if (width > 0 && height > 0 && chartRef.current) {
          chartRef.current.resize(width, height);
        }
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      baseSeriesRef.current = null;
      linesRef.current.clear();
    };
  }, []);

  React.useEffect(() => {
    const chart = chartRef.current;
    const base  = baseSeriesRef.current;
    if (!chart || !base || !data?.rows?.length) return;

    const sorted = [...data.rows].sort((a, b) => a.date - b.date);
    const display = heikinAshi ? toHeikinAshi(sorted) : sorted;
    const t = r => toTimeSec(r.date);

    base.candles.setData(
      display.filter(r => r.open != null).map(r => ({
        time: t(r), open: r.open, high: r.high, low: r.low, close: r.close,
      }))
    );

    base.volume.setData(
      display.filter(r => r.volume != null).map(r => ({
        time: t(r), value: r.volume,
        color: (r.close ?? 0) >= (r.open ?? 0) ? "rgba(42,208,123,0.24)" : "rgba(255,93,108,0.24)",
      }))
    );

    // Entry / exit markers from the analyzed dataframe
    const markers = [];
    sorted.forEach(r => {
      if (r.enter_long  || r.buy)  markers.push({ time: t(r), position: "belowBar", color: "#2ad07b", shape: "arrowUp",   text: "L" });
      if (r.exit_long   || r.sell) markers.push({ time: t(r), position: "aboveBar", color: "#ff5d6c", shape: "arrowDown", text: "X" });
      if (r.enter_short)           markers.push({ time: t(r), position: "aboveBar", color: "#ffb74a", shape: "arrowDown", text: "S" });
    });
    base.candles.setMarkers(markers.sort((a, b) => a.time - b.time));

    // ── Rebuild main_plot overlay series ───────────────────────────────
    linesRef.current.forEach(s => chart.removeSeries(s));
    linesRef.current.clear();

    const entries = mainPlot ? Object.entries(mainPlot) : [];
    entries.forEach(([col, opts], i) => {
      // Binary regime filters (0/1) shade the background instead of drawing a
      // line — a near-vertical step would otherwise wreck the candle axis.
      if (isBinaryColumn(sorted, col)) {
        linesRef.current.set(col, addBinaryBgSeries(chart, `bg_${i}`, sorted, col, t));
        return;
      }

      const color = normalizeColor(opts?.color, FALLBACK_OVERLAY_COLORS[i % FALLBACK_OVERLAY_COLORS.length]);
      const series = chart.addLineSeries({
        color,
        lineWidth: 1.5,
        priceLineVisible: false,
        lastValueVisible: false,         // labels are rendered in the top legend instead
        crosshairMarkerVisible: false,
        // no title — keeps the right axis clean
      });
      const lineData = sorted.filter(r => r[col] != null && isFinite(r[col]))
        .map(r => ({ time: t(r), value: r[col] }));
      series.setData(lineData);
      linesRef.current.set(col, series);
    });

    // Strategies often define no plot_config, so also shade any binary column
    // found directly in the data that mainPlot didn't already cover.
    const SKIP_COLS = new Set([
      "open","high","low","close","volume","date",
      "enter_long","exit_long","enter_short","exit_short","buy","sell",
      ...Object.keys(mainPlot || {}),
    ]);
    const autoBinaryCols = sorted.length > 0
      ? Object.keys(sorted[0]).filter(c => !SKIP_COLS.has(c) && isBinaryColumn(sorted, c))
      : [];
    autoBinaryCols.forEach((col, bi) => {
      linesRef.current.set(`__bg_${col}`, addBinaryBgSeries(chart, `autobg_${bi}`, sorted, col, t));
    });

    // ── Initial viewport: match FreqUI's default ─────────────────────────
    // Show the most recent ~300 candles and let the user scroll left for the
    // rest of the fetched history. A fixed candle count (not a time span)
    // keeps the window consistent across timeframes. Only (re)apply on a
    // pair/timeframe change — a background poll refresh must not snap the
    // user's scroll position back to the right edge.
    const viewKey = `${data.pair}|${data.timeframe}`;
    if (viewKeyRef.current !== viewKey) {
      viewKeyRef.current = viewKey;
      const count = sorted.length;
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, count - 300),
        to:   count - 1 + 3,
      });
    }
  }, [data, mainPlot, heikinAshi]);

  // ── Entry / SL / TP price lines for open positions on this pair ─────
  React.useEffect(() => {
    const chart = chartRef.current;
    const base = baseSeriesRef.current;
    if (!chart || !base || !base.candles) return;

    // Clear previous lines
    priceLinesRef.current.forEach(line => {
      try { base.candles.removePriceLine(line); } catch {}
    });
    priceLinesRef.current = [];

    if (!positions || positions.length === 0) return;

    const LC = window.LightweightCharts;
    const dashed = LC?.LineStyle?.Dashed ?? 2;
    const dotted = LC?.LineStyle?.Dotted ?? 1;

    // For each open position on this pair, draw three horizontal lines.
    // When there are multiple positions the trade id is suffixed in the label.
    const multi = positions.length > 1;
    positions.forEach((p) => {
      const idLabel = multi ? ` #${p.id}` : "";
      // Entry
      if (p.entry != null && isFinite(p.entry)) {
        priceLinesRef.current.push(base.candles.createPriceLine({
          price: p.entry,
          color: "rgba(125,134,156,0.85)",
          lineWidth: 1, lineStyle: dotted,
          axisLabelVisible: true,
          title: `ENTRY${idLabel}`,
        }));
      }
      // Take Profit
      if (p.tp != null && isFinite(p.tp)) {
        priceLinesRef.current.push(base.candles.createPriceLine({
          price: p.tp,
          color: "#2ad07b",
          lineWidth: 1, lineStyle: dashed,
          axisLabelVisible: true,
          title: `TP${idLabel}`,
        }));
      }
      // Stop Loss
      if (p.sl != null && isFinite(p.sl)) {
        priceLinesRef.current.push(base.candles.createPriceLine({
          price: p.sl,
          color: "#ff5d6c",
          lineWidth: 1, lineStyle: dashed,
          axisLabelVisible: true,
          title: `SL${idLabel}`,
        }));
      }
    });
  }, [positions]);

  // No min-height — the chart must shrink with its flex parent. With a
  // hard minimum, smaller browser windows force the container taller than
  // the Card, and the Card's overflow clips the bottom (volume + time axis).
  return <div ref={containerRef} style={{ width: "100%", height: "100%", minHeight: 0 }}/>;
}

// ── SubplotChart ─────────────────────────────────────────────────────────────
// Renders ONE subplot from plot_config — its title + N traces.
// Trace `type`s supported: "scatter" (default → line), "bar" (histogram).
function SubplotChart({ title, traces, rows, height = 130 }) {
  const wrapRef = React.useRef(null);
  const [w, setW] = vUseState(600);
  const [tip, setTip] = vUseState(null); // { x, y, label, type }

  React.useLayoutEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(() => { if (wrapRef.current) setW(wrapRef.current.clientWidth); });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  if (!rows?.length || !traces || !Object.keys(traces).length) {
    return (
      <div ref={wrapRef} style={{ padding: "12px 18px", color: "var(--muted)", fontSize: 13, height }}>
        <strong style={{ color: "var(--text-2)" }}>{title}</strong> — no data
      </div>
    );
  }

  const cols = Object.keys(traces);
  const colors = cols.map((col, i) => normalizeColor(traces[col]?.color, FALLBACK_SUBPLOT_COLORS[i % FALLBACK_SUBPLOT_COLORS.length]));
  const types  = cols.map(col => (traces[col]?.type || "scatter").toLowerCase());

  const allVals = cols.flatMap(col => rows.map(r => r[col]).filter(v => v != null && isFinite(v)));
  if (!allVals.length) {
    return (
      <div ref={wrapRef} style={{ padding: "12px 18px", color: "var(--muted)", fontSize: 13, height }}>
        <strong style={{ color: "var(--text-2)" }}>{title}</strong> — no values for this timeframe
      </div>
    );
  }

  // ── Binary "regime filter" lane rendering ────────────────────────────
  // If every trace in this subplot is a 0/1 series (e.g. uptrend filters),
  // skip the oscillator grid entirely and render each trace as its own
  // horizontal lane with colored bars where the value is ON.
  const binaryFlags = cols.map(col => isBinaryColumn(rows, col));
  const allBinary   = binaryFlags.length > 0 && binaryFlags.every(Boolean);
  if (allBinary) {
    const padB = { l: 8, r: 12, t: 20, b: 16 };
    const innerWB = Math.max(0, w - padB.l - padB.r);
    const innerHB = height - padB.t - padB.b;
    const laneH = innerHB / cols.length;
    const xsB = i => padB.l + (i / Math.max(1, rows.length - 1)) * innerWB;

    // Format a row's date → short "May 14" or full "May 14 12:00 UTC"
    const rowDt = (row) => {
      if (!row?.date) return null;
      const d = row.date;
      return typeof d === "number" ? new Date(d > 1e12 ? d : d * 1000) : new Date(d);
    };
    const shortDate = (row) => {
      const dt = rowDt(row);
      return dt ? dt.toLocaleString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }) : "";
    };
    const fullDate = (row) => {
      const dt = rowDt(row);
      return dt ? dt.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }) + " UTC" : "";
    };
    // "<start> -> <end>" label for a [s, e] stretch; end is "now" if it runs to the last row.
    const stretchLabel = (s, e) =>
      fullDate(rows[s]) + " -> " + (e < rows.length - 1 ? fullDate(rows[e + 1]) : "now");

    return (
      <div ref={wrapRef} style={{ width: "100%", position: "relative" }}>
        <div style={{
          position: "absolute", top: 4, left: 10,
          fontSize: 11.5, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase",
          color: "var(--text-2)", pointerEvents: "none", zIndex: 1,
        }}>{title}</div>

        <svg width={w} height={height} style={{ display: "block" }} onMouseLeave={() => setTip(null)}>
          {cols.map((col, i) => {
            const color = colors[i];
            const laneTop = padB.t + i * laneH;
            const barTop = laneTop + Math.max(2, laneH * 0.12);
            const barH = laneH - Math.max(4, laneH * 0.24);
            const laneCenter = laneTop + laneH / 2;

            // Build contiguous ON-stretches
            const stretches = [];
            let startIdx = null;
            for (let idx = 0; idx < rows.length; idx++) {
              const on = isOne(rows[idx][col]);
              if (on && startIdx === null) startIdx = idx;
              else if (!on && startIdx !== null) { stretches.push([startIdx, idx - 1]); startIdx = null; }
            }
            if (startIdx !== null) stretches.push([startIdx, rows.length - 1]);

            // Minimum pixel spacing per label track (above vs below)
            const MIN_PX = 68;
            let lastAboveX = -MIN_PX, lastBelowX = -MIN_PX;

            // Latest state for the ON/OFF chip
            let lastVal = null;
            for (let j = rows.length - 1; j >= 0; j--) {
              if (rows[j][col] != null) { lastVal = rows[j][col]; break; }
            }
            const isOn = isOne(lastVal);

            // Build OFF-stretches (gaps between ON-stretches)
            const offStretches = [];
            if (stretches.length === 0) {
              offStretches.push([0, rows.length - 1]);
            } else {
              if (stretches[0][0] > 0) offStretches.push([0, stretches[0][0] - 1]);
              for (let si = 0; si < stretches.length - 1; si++) {
                offStretches.push([stretches[si][1] + 1, stretches[si + 1][0] - 1]);
              }
              if (stretches[stretches.length - 1][1] < rows.length - 1)
                offStretches.push([stretches[stretches.length - 1][1] + 1, rows.length - 1]);
            }

            return (
              <g key={col}>
                {/* Lane background */}
                <rect x={padB.l} y={barTop} width={innerWB} height={barH} fill="rgba(255,255,255,0.025)" rx="2"/>

                {/* ON periods — green */}
                {stretches.map(([s, e], si) => {
                  const x1 = xsB(s);
                  const x2 = xsB(Math.min(e + 1, rows.length - 1));
                  const xOff = e < rows.length - 1 ? xsB(e + 1) : null;
                  const barW = Math.max(1, x2 - x1);

                  const showOnLabel  = (x1 - lastAboveX) >= MIN_PX;
                  if (showOnLabel) lastAboveX = x1;
                  const showOffLabel = xOff != null && (xOff - lastBelowX) >= MIN_PX;
                  if (showOffLabel) lastBelowX = xOff;

                  const onAnchor  = x1 > w - 55 ? "end" : "start";
                  const offAnchor = xOff != null && xOff > w - 55 ? "end" : "start";

                  const tipLabel = stretchLabel(s, e);

                  return (
                    <g key={si}>
                      <rect x={x1} y={barTop} width={barW} height={barH}
                            fill={color} opacity={0.55}/>
                      <rect x={x1} y={barTop} width={barW} height={barH}
                            fill="transparent" style={{ cursor: "pointer" }}
                            onMouseEnter={() => setTip({ x: x1, barW, y: barTop, label: tipLabel, color: "#2ad07b" })}
                            onMouseLeave={() => setTip(null)}/>
                      {showOnLabel && (
                        <text x={x1 + (onAnchor === "end" ? -3 : 3)} y={barTop - 3}
                              textAnchor={onAnchor} fontSize="9.5"
                              fill="#2ad07b" fontFamily="monospace" fontWeight="600">
                          {shortDate(rows[s])}
                        </text>
                      )}
                      {showOffLabel && xOff != null && (
                        <text x={xOff + (offAnchor === "end" ? -3 : 3)} y={barTop + barH + 11}
                              textAnchor={offAnchor} fontSize="9.5"
                              fill="#ff5d6c" fontFamily="monospace" fontWeight="600">
                          {shortDate(rows[e + 1])}
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* OFF periods — red, with hover tooltip */}
                {offStretches.map(([s, e], oi) => {
                  const x1 = xsB(s);
                  const x2 = xsB(Math.min(e + 1, rows.length - 1));
                  const barW = Math.max(1, x2 - x1);
                  const tipLabel = stretchLabel(s, e);
                  return (
                    <g key={oi}>
                      <rect x={x1} y={barTop} width={barW} height={barH}
                            fill="#ff5d6c" opacity={0.3}/>
                      <rect x={x1} y={barTop} width={barW} height={barH}
                            fill="transparent" style={{ cursor: "pointer" }}
                            onMouseEnter={() => setTip({ x: x1, barW, y: barTop, label: tipLabel, color: "#ff5d6c" })}
                            onMouseLeave={() => setTip(null)}/>
                    </g>
                  );
                })}

                {/* Lane label — top-left inside the bar */}
                <text x={padB.l + 6} y={barTop + 11}
                      fontSize="10.5" fill="rgba(255,255,255,0.65)" fontFamily="monospace" fontWeight="600">
                  {col}
                </text>

                {/* ON/OFF chip on the right */}
                <g>
                  <rect x={w - padB.r - 30} y={laneCenter - 7} width={30} height={14} rx="3"
                        fill={isOn ? `${color}33` : "rgba(255,255,255,0.04)"}
                        stroke={isOn ? color : "rgba(255,255,255,0.10)"} strokeWidth="1"/>
                  <text x={w - padB.r - 15} y={laneCenter + 3} textAnchor="middle"
                        fontSize="10" fontFamily="monospace" fontWeight="700"
                        fill={isOn ? color : "#535b71"}>
                    {isOn ? "ON" : "OFF"}
                  </text>
                </g>
              </g>
            );
          })}

          {/* Hover tooltip over ON period */}
          {tip && (() => {
            const tipW = Math.min(Math.max(tip.label.length * 6.5 + 16, 180), w - 20);
            const tipH = 22;
            const tx = Math.min(tip.x + tip.barW / 2 - tipW / 2, w - tipW - padB.r);
            const ty = tip.y - tipH - 5;
            return (
              <g style={{ pointerEvents: "none" }}>
                <rect x={Math.max(padB.l, tx)} y={ty} width={tipW} height={tipH} rx="4"
                      fill="rgba(11,16,26,0.95)" stroke={tip.color} strokeWidth="1"/>
                <text x={Math.max(padB.l, tx) + 8} y={ty + 14} fontSize="11"
                      fill={tip.color} fontFamily="monospace" fontWeight="600">
                  {tip.label}
                </text>
              </g>
            );
          })()}
        </svg>
      </div>
    );
  }

  const rawMin = Math.min(...allVals), rawMax = Math.max(...allVals);
  // 0–100 oscillator-like? give it a fixed scale w/ the standard 30/50/70 grid
  const isBounded = rawMin >= -2 && rawMax <= 102;
  const yMin = isBounded ? 0 : rawMin - (rawMax - rawMin) * 0.08;
  const yMax = isBounded ? 100 : rawMax + (rawMax - rawMin) * 0.08;
  const yRange = yMax - yMin || 1;

  const pad = { l: 44, r: 12, t: 18, b: 12 };
  const innerW = Math.max(0, w - pad.l - pad.r);
  const innerH = height - pad.t - pad.b;
  const ys = v => pad.t + innerH * (1 - (v - yMin) / yRange);
  const xs = i => pad.l + (i / Math.max(1, rows.length - 1)) * innerW;

  const buildPath = (col) => {
    let d = "", moved = false;
    rows.forEach((r, i) => {
      const v = r[col];
      if (v == null || !isFinite(v)) { moved = false; return; }
      d += moved ? `L${xs(i).toFixed(1)} ${ys(v).toFixed(1)}` : `M${xs(i).toFixed(1)} ${ys(v).toFixed(1)}`;
      moved = true;
    });
    return d;
  };

  const buildBars = (col, color) => {
    const barW = Math.max(1, innerW / rows.length * 0.7);
    const yZero = ys(Math.max(0, yMin));
    return rows.map((r, i) => {
      const v = r[col];
      if (v == null || !isFinite(v)) return null;
      const x = xs(i);
      const yVal = ys(v);
      return (
        <rect key={i} x={x - barW / 2} y={Math.min(yZero, yVal)} width={barW}
              height={Math.max(0.5, Math.abs(yZero - yVal))}
              fill={color}
              opacity={v >= 0 ? 0.7 : 0.55}/>
      );
    });
  };

  // Y-axis labels
  const yTicks = isBounded ? [30, 50, 70] : (yMin < 0 && yMax > 0 ? [yMin, 0, yMax] : [yMin, (yMin + yMax) / 2, yMax]);
  const showZero = !isBounded && yMin < 0 && yMax > 0;

  return (
    <div ref={wrapRef} style={{ width: "100%", position: "relative" }}>
      {/* Title in the top-left corner */}
      <div style={{
        position: "absolute", top: 5, left: 10,
        fontSize: 11.5, fontWeight: 600, letterSpacing: ".08em", textTransform: "uppercase",
        color: "var(--text-2)", pointerEvents: "none", zIndex: 1,
      }}>{title}</div>

      <svg width={w} height={height} style={{ display: "block" }}>
        {/* Y-axis grid */}
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - pad.r} y1={ys(v)} y2={ys(v)}
                  stroke={isBounded && (v === 30 || v === 70)
                    ? (v === 70 ? "rgba(255,93,108,0.20)" : "rgba(42,208,123,0.20)")
                    : "rgba(255,255,255,0.05)"}
                  strokeWidth="1" strokeDasharray="3 4"/>
            <text x={pad.l - 5} y={ys(v) + 3.5} textAnchor="end" fontSize="10" fill="#535b71" fontFamily="monospace">
              {Number(v).toFixed(Math.abs(v) >= 10 ? 0 : 2)}
            </text>
          </g>
        ))}
        {showZero && (
          <line x1={pad.l} x2={w - pad.r} y1={ys(0)} y2={ys(0)}
                stroke="rgba(255,255,255,0.14)" strokeWidth="1"/>
        )}

        {/* Traces */}
        {cols.map((col, i) => {
          if (types[i] === "bar" || types[i] === "histogram") {
            return <g key={col}>{buildBars(col, colors[i])}</g>;
          }
          return (
            <path key={col} d={buildPath(col)}
                  stroke={colors[i]} strokeWidth={i === 0 ? 1.5 : 1.3}
                  fill="none" strokeLinecap="round"
                  opacity={i === 0 ? 1 : 0.85}/>
          );
        })}

        {/* Legend chips, top-right */}
        {cols.map((col, i) => {
          const v = rows.slice().reverse().find(r => r[col] != null && isFinite(r[col]))?.[col];
          const label = col.toUpperCase().slice(0, 7);
          const chipW = 70;
          const lx = w - pad.r - (cols.length - i) * (chipW + 4);
          return (
            <g key={col}>
              <rect x={lx} y={4} width={chipW} height={14} rx="3" fill="rgba(10,16,30,0.75)"/>
              <circle cx={lx + 7} cy={11} r={2.8} fill={colors[i]}/>
              <text x={lx + 13} y={14} fontSize="10" fill={colors[i]} fontFamily="monospace">
                {label} {v != null ? Number(v).toFixed(Math.abs(v) >= 10 ? 1 : 2) : "—"}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ── ChartView ────────────────────────────────────────────────────────────────
function ChartView({ data, baseUrl, isMobile, selectedPair, onPairChange }) {
  const defaultTf = data?.bot?.timeframe || "4h";
  const [pairs,      setPairs]      = vUseState([]);
  const [pair,       setLocalPair]  = vUseState(selectedPair || "");
  const [timeframe,  setTimeframe]  = vUseState(defaultTf);
  const [chartData,  setChartData]  = vUseState(null);
  const [plotConfig, setPlotConfig] = vUseState(null);
  const [loading,    setLoading]    = vUseState(false);
  const [error,      setError]      = vUseState(null);
  const [updatedAt,  setUpdatedAt]  = vUseState(null);
  const [haMode,     setHaMode]     = vUseState(true);

  // Wrapped setter so the App's chartPair stays in sync with the dropdown
  const setPair = React.useCallback((p) => {
    setLocalPair(p);
    if (onPairChange) onPairChange(p);
  }, [onPairChange]);

  // External pair selection (deep-link from another view) overrides local state
  React.useEffect(() => {
    if (selectedPair && selectedPair !== pair) setLocalPair(selectedPair);
  }, [selectedPair]);

  // Load whitelist per bot. Keep the current pair only if the new bot offers
  // it; otherwise fall back to its first pair (switching bots can invalidate it).
  React.useEffect(() => {
    if (!baseUrl) return;
    fetchWhitelist(baseUrl)
      .then(wl => {
        setPairs(wl);
        const next = (pair && wl.includes(pair)) ? pair : (wl[0] || "");
        if (next !== pair) setPair(next);
      })
      .catch(e => setError(e.message));
  }, [baseUrl]);

  // Load plot_config once per baseUrl (strategy-defined)
  React.useEffect(() => {
    if (!baseUrl) return;
    fetchPlotConfig(baseUrl).then(pc => setPlotConfig(pc)).catch(() => setPlotConfig(null));
  }, [baseUrl]);

  // Snap the timeframe to the bot's strategy timeframe whenever the bot changes.
  // Fires only when the value actually changes, so a manual selection sticks.
  React.useEffect(() => {
    const tf = data?.bot?.timeframe;
    if (tf) setTimeframe(tf);
  }, [data?.bot?.timeframe]);

  // Bumped on each request so a slow in-flight fetch (e.g. for the previous
  // bot/pair during a switch) can't overwrite the latest result.
  const reqIdRef = React.useRef(0);
  const loadChart = React.useCallback(async (p, tf) => {
    if (!baseUrl || !p) return;
    const reqId = ++reqIdRef.current;
    setLoading(true); setError(null);
    try {
      const d = await fetchChartCandles(baseUrl, p, tf, 1000);
      if (reqId !== reqIdRef.current) return;
      setChartData(d);
      setUpdatedAt(Date.now());
    } catch (e) {
      if (reqId === reqIdRef.current) setError(e.message || "Failed to load chart data");
    } finally {
      if (reqId === reqIdRef.current) setLoading(false);
    }
  }, [baseUrl]);

  React.useEffect(() => { if (pair) loadChart(pair, timeframe); }, [pair, timeframe, loadChart]);
  React.useEffect(() => {
    const id = setInterval(() => { if (pair) loadChart(pair, timeframe); }, 120_000);
    return () => clearInterval(id);
  }, [pair, timeframe, loadChart]);

  const mainPlot = plotConfig?.main_plot || {};
  const subplots = plotConfig?.subplots  || {};
  const subplotEntries = Object.entries(subplots);
  const overlayCols = Object.keys(mainPlot);

  // Open positions on the currently displayed pair.
  const allPositions = data ? data.positions : [];
  const pairPositions = vUseMemo(
    () => allPositions.filter(p => p.pair === pair),
    [allPositions, pair]
  );

  const TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"];
  const selectStyle = {
    background: "var(--panel-2)", border: "1px solid var(--border-2)", color: "var(--text)",
    borderRadius: 8, padding: "6px 28px 6px 10px", fontFamily: "inherit", fontSize: 13,
    appearance: "none", cursor: "pointer",
    backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%237d869c' d='M0 0h10L5 6z'/></svg>")`,
    backgroundRepeat: "no-repeat", backgroundPosition: "right 10px center",
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", gap: 8,
      height: isMobile ? "auto" : "100%", minHeight: 0,
    }}>
      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", flexShrink: 0 }}>
        <select value={pair} onChange={e => setPair(e.target.value)} style={{ ...selectStyle, minWidth: 130 }}>
          {pairs.map(p => <option key={p}>{p}</option>)}
        </select>
        <Segmented value={timeframe} options={TIMEFRAMES} onChange={setTimeframe} size="sm"/>
        <Btn tone={haMode ? "accent" : "ghost"} size="sm" onClick={() => setHaMode(v => !v)}>HA</Btn>
        <Btn icon="refresh" tone="ghost" size="sm" disabled={loading || !pair} onClick={() => loadChart(pair, timeframe)}>
          {loading ? "Loading…" : "Refresh"}
        </Btn>
        {plotConfig === null && !loading && (
          <span className="muted" style={{ fontSize: 12 }}>· no plot_config</span>
        )}
        {pairPositions.length > 0 && (
          <span style={{
            fontSize: 11.5, fontWeight: 600, padding: "2px 8px", borderRadius: 5,
            background: "var(--up-soft)", border: "1px solid var(--up-line)", color: "var(--up)",
          }}>
            {pairPositions.length} open · SL {fmtPrice(pairPositions[0].sl)} · TP {fmtPrice(pairPositions[0].tp)}
          </span>
        )}
        {updatedAt && !loading && (
          <span className="muted" style={{ fontSize: 12, marginLeft: isMobile ? 0 : "auto" }}>
            Updated {fmtTimeAgo(updatedAt)}
          </span>
        )}
      </div>

      {error && (
        <div style={{
          padding: "8px 12px", background: "var(--down-soft)", border: "1px solid var(--down-line)",
          borderRadius: 8, color: "var(--down)", fontSize: 13,
          display: "flex", alignItems: "center", gap: 8, flexShrink: 0,
        }}>
          <Icon name="warn" size={13}/>{error}
        </div>
      )}

      {/* ── Main candle chart ────────────────────────────────────────── */}
      <Card pad={false} style={{
        flex: isMobile ? "none" : 1, minHeight: 0,
        height: isMobile ? 420 : undefined,
        display: "flex", flexDirection: "column",
      }}>
        {chartData && (
          <div style={{
            padding: "8px 14px 7px", display: "flex", alignItems: "center", gap: 10,
            flexShrink: 0, borderBottom: "1px solid var(--border)", flexWrap: "wrap",
          }}>
            <PairLabel pair={chartData.pair} size={22}/>
            <span className="muted" style={{ fontSize: 12 }}>· {chartData.timeframe}</span>
            {chartData.strategy && <span className="muted" style={{ fontSize: 12 }}>· {chartData.strategy}</span>}

            {/* Legend chips for main_plot overlays — shows the latest value of each */}
            {overlayCols.length > 0 && (() => {
              return (
                <div style={{ display: "flex", gap: 6, alignItems: "center", marginLeft: "auto", flexWrap: "wrap" }}>
                  {overlayCols.map((col, i) => {
                    const fallback = FALLBACK_OVERLAY_COLORS[i % FALLBACK_OVERLAY_COLORS.length];
                    const color = normalizeColor(mainPlot[col]?.color, fallback);
                    // Walk backwards to find last non-null value for this column
                    const v = (() => {
                      for (let j = chartData.rows.length - 1; j >= 0; j--) {
                        const x = chartData.rows[j][col];
                        if (x != null && isFinite(x)) return x;
                      }
                      return null;
                    })();
                    const binary = isBinaryColumn(chartData.rows, col);
                    if (binary) {
                      // ON / OFF chip — these aren't drawn as lines, so the legend
                      // is the only place this filter's state is visible.
                      const isOn = v === 1 || v === true;
                      const tone = isOn ? "var(--up)" : "var(--muted)";
                      const bg   = isOn ? "rgba(42,208,123,0.10)" : "rgba(255,255,255,0.03)";
                      return (
                        <span key={col} title={`${col} = ${isOn ? "ON" : "OFF"}`} style={{
                          padding: "2px 7px", borderRadius: 5, fontSize: 11.5, fontWeight: 600,
                          color: tone, border: `1px solid ${isOn ? "rgba(42,208,123,0.30)" : "rgba(255,255,255,0.08)"}`,
                          background: bg,
                          display: "inline-flex", alignItems: "center", gap: 5,
                        }}>
                          <span style={{
                            display: "inline-block", width: 6, height: 6, borderRadius: 99,
                            background: tone,
                            boxShadow: isOn ? "0 0 0 3px rgba(42,208,123,0.18)" : "none",
                          }}/>
                          <span>{col}</span>
                          <span className="num" style={{ opacity: .9 }}>{isOn ? "ON" : "OFF"}</span>
                        </span>
                      );
                    }
                    return (
                      <span key={col} style={{
                        padding: "2px 7px", borderRadius: 5, fontSize: 11.5, fontWeight: 600,
                        color, border: `1px solid ${color}55`,
                        background: "rgba(255,255,255,0.04)",
                        display: "inline-flex", alignItems: "center", gap: 5,
                      }}>
                        <span style={{ display: "inline-block", width: 8, height: 2, background: color, borderRadius: 1 }}/>
                        <span>{col}</span>
                        <span className="num" style={{ opacity: .9 }}>{v != null ? fmtPrice(v) : "—"}</span>
                      </span>
                    );
                  })}
                  <span className="muted" style={{ fontSize: 11.5 }}>{chartData.rows?.length} candles</span>
                </div>
              );
            })()}
          </div>
        )}

        {!chartData && !loading && (
          <div style={{ flex: 1, display: "grid", placeItems: "center", color: "var(--muted)", fontSize: 14 }}>
            Select a pair above to load the chart
          </div>
        )}
        {loading && !chartData && (
          <div style={{ flex: 1, display: "grid", placeItems: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <div className="skeleton" style={{ width: 200, height: 10, borderRadius: 6 }}/>
              <div className="skeleton" style={{ width: 140, height: 10, borderRadius: 6 }}/>
              <span className="muted" style={{ fontSize: 13, marginTop: 4 }}>Loading candles…</span>
            </div>
          </div>
        )}
        {chartData && (
          <div style={{ flex: 1, minHeight: 0 }}>
            <CandleChart data={chartData} mainPlot={mainPlot} positions={pairPositions} heikinAshi={haMode}/>
          </div>
        )}
      </Card>

      {/* ── Subplots — one card per plot_config.subplots entry ────────── */}
      {chartData && subplotEntries.length > 0 && subplotEntries.map(([title, traces]) => (
        <Card key={title} pad={false} style={{ flexShrink: 0, height: isMobile ? 90 : 105 }}>
          <SubplotChart title={title} traces={traces} rows={chartData.rows} height={isMobile ? 88 : 103}/>
        </Card>
      ))}

      {/* If plot_config is empty or has no subplots and no overlays, hint to user */}
      {chartData && overlayCols.length === 0 && subplotEntries.length === 0 && (
        <div style={{
          padding: "10px 14px", background: "rgba(255,183,74,0.08)",
          border: "1px solid rgba(255,183,74,0.25)", borderRadius: 8,
          color: "var(--warn)", fontSize: 13, flexShrink: 0,
        }}>
          <Icon name="info" size={13} style={{ marginRight: 6, verticalAlign: "-2px" }}/>
          Strategy <strong>{chartData.strategy}</strong> has no <code>plot_config</code>.
          Define <code>main_plot</code> / <code>subplots</code> in the strategy to render indicators here.
        </div>
      )}
    </div>
  );
}

Object.assign(window, {
  OverviewView, PositionsView, TradesView, PerformanceView, LocksView,
  SignalsView, ChartView,
});
