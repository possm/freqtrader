// Shared UI primitives — formatters, icons, sparklines, charts, table chrome.

const { useState, useEffect, useMemo, useRef, useLayoutEffect } = React;

// ── Breakpoint hook ───────────────────────────────────────────────────────────
function useBreakpoint() {
  const [w, setW] = useState(() => window.innerWidth);
  useEffect(() => {
    const handler = () => setW(window.innerWidth);
    window.addEventListener("resize", handler, { passive: true });
    return () => window.removeEventListener("resize", handler);
  }, []);
  return { isMobile: w < 768, isTablet: w >= 768 && w < 1200, width: w };
}

// ── currency symbol (updated once bot config loads) ─────────────────────────
const STAKE_SYMBOLS = {
  USDT: "$", USDC: "$", USD: "$", BUSD: "$",
  EUR: "€", GBP: "£", JPY: "¥", CHF: "Fr ",
  AUD: "A$", CAD: "C$", SGD: "S$", HKD: "HK$",
  BTC: "₿", ETH: "Ξ", BNB: "BNB ", SOL: "SOL ",
};

let _currencySymbol = "$";
const setCurrency = (stake) => {
  _currencySymbol = STAKE_SYMBOLS[stake?.toUpperCase()] ?? stake + " " ?? "$";
};
const getCurrency = () => _currencySymbol;

// ── formatters ─────────────────────────────────────────────────────────────
const fmtMoney = (n, decimals = 2) => {
  if (n == null || isNaN(n)) return "—";
  const sign = n < 0 ? "-" : "";
  const v = Math.abs(n);
  const locale = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US";
  return sign + v.toLocaleString(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};
const fmtUsd        = (n, d = 2) => _currencySymbol + fmtMoney(n, d);
const fmtSignedUsd  = (n, d = 2) => (n >= 0 ? "+" : "−") + _currencySymbol + fmtMoney(Math.abs(n), d);
const fmtPct        = (n, d = 2) => (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(d) + "%";

const pnlColor = (v) => (v === true || (typeof v === "number" && v >= 0)) ? "var(--up)" : "var(--down)";
const pnlTone = (v) => (v === true || (typeof v === "number" && v >= 0)) ? "up" : "down";

const fmtPrice = (n) => {
  if (n == null) return "—";
  const locale = typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US";
  if (n >= 1000) return n.toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n >= 1)    return n.toLocaleString(locale, { minimumFractionDigits: 3, maximumFractionDigits: 4 });
  return n.toLocaleString(locale, { minimumFractionDigits: 4, maximumFractionDigits: 5 });
};

const fmtCompact = (n) => {
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(2) + "K";
  return n.toFixed(2);
};

const fmtDuration = (ms) => {
  const totalMin = Math.floor(ms / 60000);
  const d = Math.floor(totalMin / 1440);
  const h = Math.floor((totalMin % 1440) / 60);
  const m = totalMin % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};

const fmtTimeAgo = (ts) => fmtDuration(Date.now() - ts) + " ago";

const fmtTime = (ts) => {
  const d = new Date(ts);
  const day = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${day} · ${time}`;
};

// ── Deterministic spark series for client-side position charts ──────────────
function mulberry32(seed) {
  let a = seed | 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashStr(s) {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
function sparkSeries(start, end, n, seed) {
  const rng = mulberry32(hashStr(String(seed)));
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const linear = start + (end - start) * t;
    const noise = (rng() - 0.5) * (Math.abs(end - start) * 1.4 + start * 0.003);
    pts.push(linear + noise);
  }
  pts[0] = start; pts[n - 1] = end;
  return pts;
}

// ── Icons (inline SVG, stroke-based) ────────────────────────────────────────
const Icon = ({ name, size = 16, style: s, ...rest }) => {
  const common = {
    width: size, height: size, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor",
    strokeWidth: 1.6, strokeLinecap: "round", strokeLinejoin: "round",
    style: { display: "inline-block", flexShrink: 0, ...s },
    ...rest,
  };
  switch (name) {
    case "dashboard": return <svg {...common}><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>;
    case "positions": return <svg {...common}><path d="M3 12h4l3-7 4 14 3-7h4"/></svg>;
    case "trades":    return <svg {...common}><path d="M4 7h12"/><path d="M13 4l3 3-3 3"/><path d="M20 17H8"/><path d="M11 20l-3-3 3-3"/></svg>;
    case "perf":      return <svg {...common}><path d="M3 20h18"/><path d="M6 16V9"/><path d="M11 16V5"/><path d="M16 16v-8"/></svg>;
    case "bot":       return <svg {...common}><rect x="4" y="7" width="16" height="12" rx="2.5"/><circle cx="9" cy="13" r="1"/><circle cx="15" cy="13" r="1"/><path d="M12 4v3"/><path d="M9 19v2"/><path d="M15 19v2"/></svg>;
    case "settings":  return <svg {...common}><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M2 12h3M19 12h3M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"/></svg>;
    case "search":    return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>;
    case "bell":      return <svg {...common}><path d="M6 8a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10 21h4"/></svg>;
    case "refresh":   return <svg {...common}><path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 01-15 6.7L3 16"/><path d="M3 21v-5h5"/></svg>;
    case "logout":    return <svg {...common}><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>;
    case "chevron-down":  return <svg {...common}><path d="M6 9l6 6 6-6"/></svg>;
    case "chevron-up":    return <svg {...common}><path d="M6 15l6-6 6 6"/></svg>;
    case "chevron-right": return <svg {...common}><path d="M9 6l6 6-6 6"/></svg>;
    case "filter":    return <svg {...common}><path d="M3 5h18M6 12h12M10 19h4"/></svg>;
    case "download":  return <svg {...common}><path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/></svg>;
    case "external":  return <svg {...common}><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M19 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1h5"/></svg>;
    case "shield":    return <svg {...common}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/></svg>;
    case "target":    return <svg {...common}><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/></svg>;
    case "x-circle":  return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/></svg>;
    case "up":        return <svg {...common}><path d="M7 14l5-5 5 5"/></svg>;
    case "down":      return <svg {...common}><path d="M7 10l5 5 5-5"/></svg>;
    case "clock":     return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "info":      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 8.5h.01M11 12h1v5h1"/></svg>;
    case "warn":      return <svg {...common}><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4"/><circle cx="12" cy="17" r=".5" fill="currentColor"/></svg>;
    case "key":       return <svg {...common}><circle cx="7.5" cy="15.5" r="5.5"/><path d="M21 2l-9.6 9.6M15.5 7.5l3 3"/></svg>;
    case "lock":      return <svg {...common}><rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/></svg>;
    case "unlock":    return <svg {...common}><rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V8a4 4 0 014-4 4 4 0 014 3"/></svg>;
    case "candles":   return <svg {...common}><line x1="4" y1="5" x2="4" y2="19"/><rect x="2" y="8" width="4" height="7" rx="0.5"/><line x1="12" y1="3" x2="12" y2="21"/><rect x="10" y="6" width="4" height="9" rx="0.5"/><line x1="20" y1="6" x2="20" y2="18"/><rect x="18" y="9" width="4" height="6" rx="0.5"/></svg>;
    default: return <svg {...common}/>;
  }
};

// ── Pair token ───────────────────────────────────────────────────────────────
const PAIR_COLORS = {
  BTC:   ["#f7931a", "#3a1d04"],
  ETH:   ["#8a8fd9", "#15173a"],
  SOL:   ["#11d29a", "#062a23"],
  AVAX:  ["#e84142", "#370c0d"],
  LINK:  ["#2a5ada", "#0b1738"],
  ARB:   ["#28a0f0", "#062235"],
  OP:    ["#ff0420", "#2a0407"],
  MATIC: ["#8247e5", "#190c33"],
  DOGE:  ["#c2a633", "#2d240a"],
  ADA:   ["#0033ad", "#091633"],
  NEAR:  ["#fafafa", "#1c1c1c"],
  INJ:   ["#00f2fe", "#062a2e"],
  BNB:   ["#f0b90b", "#2d2208"],
  XRP:   ["#346aa9", "#081525"],
  DOT:   ["#e6007a", "#2d0018"],
  ATOM:  ["#2e3148", "#9ba0c0"],
  LTC:   ["#bfbbbb", "#1a1a1a"],
  UNI:   ["#ff007a", "#2d0016"],
  AAVE:  ["#b6509e", "#1d0d1a"],
};

function PairToken({ pair, size = 26, onClick }) {
  const sym = pair.split("/")[0];
  const [fg, bg] = PAIR_COLORS[sym] || ["#9aa5b9", "#1d2740"];
  const [imgOk, setImgOk] = useState(true);
  // React reuses instances across table re-sorts; reset the fallback when the coin changes.
  useEffect(() => { setImgOk(true); }, [sym]);
  const imgUrl = `https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@master/32/color/${sym.toLowerCase()}.png`;
  const label = sym.length <= 3 ? sym : sym.slice(0, 3);
  const clickable = !!onClick;
  return (
    <span
      onClick={clickable ? (e) => { e.stopPropagation(); onClick(pair); } : undefined}
      title={clickable ? `Open ${pair} chart` : undefined}
      style={{
        display: "inline-grid", placeItems: "center",
        width: size, height: size, borderRadius: "50%",
        background: imgOk ? "rgba(255,255,255,0.06)" : bg,
        color: fg,
        fontFamily: "var(--mono)", fontSize: size * 0.34, fontWeight: 600,
        flexShrink: 0,
        boxShadow: "inset 0 0 0 1px rgba(255,255,255,.06)",
        cursor: clickable ? "pointer" : "default",
        overflow: "hidden",
      }}>
      {imgOk
        ? <img src={imgUrl} width={size} height={size}
                style={{ display: "block", objectFit: "contain" }}
                onError={() => setImgOk(false)}/>
        : label}
    </span>
  );
}

function PairLabel({ pair, sub, size = 26, onClick }) {
  const clickable = !!onClick;
  return (
    <div
      onClick={clickable ? (e) => { e.stopPropagation(); onClick(pair); } : undefined}
      title={clickable ? `Open ${pair} chart` : undefined}
      onMouseEnter={clickable ? (e) => {
        e.currentTarget.style.background = "rgba(255,255,255,.04)";
        const nameEl = e.currentTarget.querySelector("[data-pair-name]");
        if (nameEl) nameEl.style.color = "var(--accent)";
      } : undefined}
      onMouseLeave={clickable ? (e) => {
        e.currentTarget.style.background = "transparent";
        const nameEl = e.currentTarget.querySelector("[data-pair-name]");
        if (nameEl) nameEl.style.color = "";
      } : undefined}
      style={{
        display: "inline-flex", alignItems: "center", gap: 10, minWidth: 0,
        cursor: clickable ? "pointer" : "default",
        padding: clickable ? "3px 8px 3px 3px" : 0,
        marginLeft: clickable ? -3 : 0,
        borderRadius: 7,
        transition: "background .14s ease",
      }}>
      <PairToken pair={pair} size={size} />
      <div style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
        <span data-pair-name style={{
          fontWeight: 500, letterSpacing: ".01em",
          transition: "color .14s ease",
        }}>{pair}</span>
        {sub && <span className="muted" style={{ fontSize: 12.5 }}>{sub}</span>}
      </div>
    </div>
  );
}

// ── Card ─────────────────────────────────────────────────────────────────────
function Card({ title, sub, right, children, pad = true, style }) {
  return (
    <section style={{
      background: "var(--panel)", border: "1px solid var(--border)",
      borderRadius: 14, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden",
      ...style,
    }}>
      {(title || right) && (
        <header style={{
          padding: "14px 18px 12px", display: "flex", alignItems: "center", gap: 14,
          borderBottom: "1px solid var(--border)",
        }}>
          <div style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
            {title && <div style={{ fontSize: 14.5, fontWeight: 600, letterSpacing: ".005em" }}>{title}</div>}
            {sub && <div className="muted" style={{ fontSize: 12.5, marginTop: 2 }}>{sub}</div>}
          </div>
          {right}
        </header>
      )}
      <div style={{ padding: pad ? "var(--pad-card)" : 0, flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        {children}
      </div>
    </section>
  );
}

// ── PnL pill ─────────────────────────────────────────────────────────────────
function PnlPill({ value, pct, size = "md" }) {
  const pos = (value ?? pct) >= 0;
  const dims = size === "sm"
    ? { fs: 11, pad: "2px 7px", gap: 4, ic: 11 }
    : { fs: 12.5, pad: "3px 9px", gap: 5, ic: 13 };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: dims.gap,
      padding: dims.pad, borderRadius: 6,
      background: pos ? "var(--up-soft)" : "var(--down-soft)",
      color: pnlColor(value ?? pct),
      fontSize: dims.fs, fontWeight: 600,
      fontFamily: "var(--mono)", fontVariantNumeric: "tabular-nums",
    }}>
      <Icon name={pos ? "up" : "down"} size={dims.ic} />
      {pct != null ? fmtPct(pct) : fmtSignedUsd(value)}
    </span>
  );
}

// ── Table Cell Stack ──────────────────────────────────────────────────────────
function TableStack({ top, sub, topColor, topBold = false, align = "right" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: align === "right" ? "flex-end" : "flex-start", padding: "4px 0" }}>
      <span className="num" style={{ fontSize: topBold ? 14 : 13.5, fontWeight: topBold ? 600 : undefined, color: topColor }}>
        {top}
      </span>
      <span className="num muted" style={{ fontSize: 11.5 }}>
        {sub}
      </span>
    </div>
  );
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
function Sparkline({ data, width = 96, height = 28, color, fill = true, strokeWidth = 1.4 }) {
  if (!data || data.length < 2) return <span/>;
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const last = data[data.length - 1];
  const c = color || (last >= data[0] ? "var(--up)" : "var(--down)");
  const xs = (i) => (i / (data.length - 1)) * (width - 2) + 1;
  const ys = (v) => height - 2 - ((v - min) / range) * (height - 4);
  const line = data.map((v, i) => `${i ? "L" : "M"}${xs(i).toFixed(2)} ${ys(v).toFixed(2)}`).join(" ");
  const area = line + ` L${(width - 1).toFixed(2)} ${height} L1 ${height} Z`;
  const gid = "sg-" + Math.random().toString(36).slice(2, 8);
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={c} stopOpacity=".35"/>
          <stop offset="100%" stopColor={c} stopOpacity="0"/>
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#${gid})`} />}
      <path d={line} stroke={c} strokeWidth={strokeWidth} fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── Status dot ───────────────────────────────────────────────────────────────
function StatusDot({ kind = "up", pulse = false }) {
  const c = kind === "up" ? "var(--up)" : kind === "warn" ? "var(--warn)" : "var(--down)";
  return (
    <span style={{ position: "relative", width: 8, height: 8, display: "inline-block", flexShrink: 0 }}>
      <span style={{ position: "absolute", inset: 0, borderRadius: 8, background: c, boxShadow: `0 0 0 3px ${c}22` }}/>
      {pulse && (
        <span style={{
          position: "absolute", inset: -4, borderRadius: 999,
          border: `1.5px solid ${c}`, opacity: .55,
          animation: "ftPulse 1.6s ease-out infinite",
        }}/>
      )}
    </span>
  );
}

// ── Equity chart ─────────────────────────────────────────────────────────────
function EquityChart({ data, height = 260 }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(800);
  const [hover, setHover] = useState(null);

  useLayoutEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(() => setW(wrapRef.current.clientWidth));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);

  if (!data || data.length < 2) return (
    <div ref={wrapRef} style={{ width: "100%", height, display: "grid", placeItems: "center" }}>
      <span className="muted" style={{ fontSize: 13 }}>No equity data</span>
    </div>
  );

  const plotData = data; // Left = Oldest, Right = Newest

  const pad = { l: 62, r: 28, t: 14, b: 28 }; // increased pad.r from 16 to 28
  const innerW = Math.max(0, w - pad.l - pad.r);
  const innerH = height - pad.t - pad.b;
  const min = Math.min(...plotData.map(d => Math.min(d.v, d.v + (d.unrealized || 0))));
  const max = Math.max(...plotData.map(d => Math.max(d.v, d.v + (d.unrealized || 0))));
  const yPad = (max - min) * 0.08 || max * 0.05;
  const yMin = min - yPad, yMax = max + yPad;

  const xs = (i) => pad.l + (i / (plotData.length - 1)) * innerW;
  const ys = (v) => pad.t + innerH - ((v - yMin) / (yMax - yMin)) * innerH;

  const line = plotData.map((d, i) => `${i ? "L" : "M"}${xs(i).toFixed(2)} ${ys(d.v).toFixed(2)}`).join(" ");
  const area = line + ` L${xs(plotData.length - 1).toFixed(2)} ${pad.t + innerH} L${xs(0).toFixed(2)} ${pad.t + innerH} Z`;
  const yTicks = Array.from({ length: 5 }, (_, i) => yMin + (i / 4) * (yMax - yMin));

  const fmtDateLabel = (dateStr) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString(typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US", { month: "short", day: "numeric" });
  };

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const x = clientX - rect.left;
    // We allow hovering slightly into the right padding to catch the live unrealized point
    const i = Math.max(0, Math.min(plotData.length - 1, Math.round(((x - pad.l) / innerW) * (plotData.length - 1))));
    
    // If hovering way off to the right, just lock to the last point
    if (x >= pad.l && x <= w - 8) {
      // Find exact X of the point, but if it's the last point and it has unrealized, offset it
      let px = xs(i);
      let py = ys(plotData[i].v);
      if (i === plotData.length - 1 && plotData[i].unrealized && x > px) {
        px += 14;
        py = ys(plotData[i].v + plotData[i].unrealized);
      }
      setHover({ i, x: px, y: py, isLive: (i === plotData.length - 1 && x > xs(i)) });
    }
    else setHover(null);
  };

  // newest is last (right)
  const up = plotData[plotData.length - 1].v >= plotData[0].v;
  const c = up ? "var(--up)" : "var(--down)";
  const today = plotData[plotData.length - 1];
  const hasUnrealized = !!today.unrealized;
  const nextX = xs(plotData.length - 1) + 14;
  const nextY = ys(today.v + today.unrealized);

  return (
    <div ref={wrapRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} onMouseMove={onMove} onMouseLeave={() => setHover(null)} onTouchMove={onMove} onTouchStart={onMove}>
        <defs>
          <linearGradient id="eq-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={c} stopOpacity=".22"/>
            <stop offset="100%" stopColor={c} stopOpacity="0"/>
          </linearGradient>
        </defs>
        {yTicks.map((v, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - 12} y1={ys(v)} y2={ys(v)} stroke="var(--border)" />
            <text x={pad.l - 8} y={ys(v) + 4} textAnchor="end" fontSize="11.5" fill="var(--muted)" fontFamily="var(--mono)">
              {_currencySymbol}{Math.round(v).toLocaleString()}
            </text>
          </g>
        ))}
        {[0, .33, .66, 1].map((t, i) => {
          const idx = Math.round(t * (plotData.length - 1));
          const label = idx === plotData.length - 1 ? "today" : fmtDateLabel(plotData[idx].date);
          return (
            <text key={i} x={xs(idx)} y={height - 8} textAnchor="middle" fontSize="11.5" fill="var(--muted)">
              {label}
            </text>
          );
        })}
        <path d={area} fill="url(#eq-fill)" />
        <path d={line} stroke={c} strokeWidth="2" fill="none" strokeLinecap="round"/>
        {hasUnrealized && (
          <g>
            <path d={`M ${xs(plotData.length - 1)},${ys(today.v)} C ${xs(plotData.length - 1)+6},${ys(today.v)} ${nextX-6},${nextY} ${nextX},${nextY}`} 
                  fill="none" stroke={pnlColor(today.unrealized)} 
                  strokeWidth="2.5" strokeDasharray="4 4" />
            <circle cx={nextX} cy={nextY} r="3.5" fill="var(--bg)" stroke={pnlColor(today.unrealized)} strokeWidth="2.5"/>
            <circle cx={nextX} cy={nextY} r="6" fill={pnlColor(today.unrealized)} opacity="0.2"/>
          </g>
        )}
        {hover && (
          <g>
            <line x1={hover.x} x2={hover.x} y1={pad.t} y2={pad.t + innerH} stroke="var(--border-3)" strokeDasharray="2 3"/>
            <circle cx={hover.x} cy={hover.y} r="4" fill="var(--bg)" stroke={hover.isLive ? (pnlColor(today.unrealized)) : c} strokeWidth="2"/>
          </g>
        )}
      </svg>
      {hover && (
        <div style={{
          position: "absolute",
          left: Math.min(w - 180, Math.max(0, hover.x + 12)), 
          top: Math.max(8, hover.y - ((hover.isLive || plotData[hover.i].unrealized) ? 90 : 42)),
          background: "var(--panel-3)", border: "1px solid var(--border-2)",
          borderRadius: 8, padding: "8px 12px", fontSize: 12.5,
          pointerEvents: "none", boxShadow: "0 6px 20px rgba(0,0,0,.4)",
          whiteSpace: "nowrap", zIndex: 10
        }}>
          <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>
            {hover.i === plotData.length - 1 ? (hover.isLive ? "live (net)" : "today (closed)") : fmtDateLabel(plotData[hover.i].date)}
          </div>
          {plotData[hover.i].unrealized ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span className="muted">Balance</span>
                <span className="num" style={{ fontWeight: 600 }}>{fmtUsd(plotData[hover.i].v, 0)}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span className="muted">Unrealized</span>
                <span className="num" style={{ fontWeight: 600, color: pnlColor(plotData[hover.i].unrealized) }}>
                  {plotData[hover.i].unrealized >= 0 ? "+" : ""}{fmtUsd(plotData[hover.i].unrealized, 0)}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, marginTop: 3, paddingTop: 3, borderTop: "1px dashed var(--border)" }}>
                <span className="muted">Equity</span>
                <span className="num" style={{ fontWeight: 600 }}>{fmtUsd(plotData[hover.i].v + plotData[hover.i].unrealized, 0)}</span>
              </div>
            </div>
          ) : (
            <div className="num" style={{ fontWeight: 600 }}>{fmtUsd(plotData[hover.i].v, 0)}</div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Daily P&L bars ────────────────────────────────────────────────────────────
function DailyBars({ data, height = 200 }) {
  const wrapRef = useRef(null);
  const [w, setW] = useState(600);
  const [hover, setHover] = useState(null);

  useLayoutEffect(() => {
    if (!wrapRef.current) return;
    const ro = new ResizeObserver(() => setW(wrapRef.current.clientWidth));
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, []);
  
  if (!data || data.length === 0) return <div ref={wrapRef} style={{ width: "100%", height }}/>;
  
  const pad = { l: 52, r: 8, t: 10, b: 22 };
  const innerW = Math.max(0, w - pad.l - pad.r);
  const innerH = height - pad.t - pad.b;
  const max = Math.max(...data.map(d => Math.abs(d.v))) || 1;
  const yMax = max * 1.1;
  const ys = (v) => pad.t + innerH / 2 - (v / yMax) * (innerH / 2);
  const barW = innerW / data.length - 3;

  const fmtDateLabel = (dateStr) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString(typeof navigator !== "undefined" && navigator.language ? navigator.language : "en-US", { month: "short", day: "numeric" });
  };

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const x = clientX - rect.left;
    const i = Math.max(0, Math.min(data.length - 1, Math.floor(((x - pad.l) / innerW) * data.length)));
    if (x >= pad.l && x <= w - pad.r) {
      setHover({ i, x: pad.l + (i / data.length) * innerW + barW / 2 });
    }
    else setHover(null);
  };

  return (
    <div ref={wrapRef} style={{ width: "100%", position: "relative" }}>
      <svg width={w} height={height} onMouseMove={onMove} onMouseLeave={() => setHover(null)} onTouchMove={onMove} onTouchStart={onMove}>
        <line x1={pad.l} x2={w - pad.r} y1={pad.t + innerH / 2} y2={pad.t + innerH / 2} stroke="var(--border-2)" />
        {[yMax, 0, -yMax].map((v, i) => (
          <text key={i} x={pad.l - 6} y={ys(v) + 3.5} textAnchor="end" fontSize="11" fill="var(--muted)" fontFamily="var(--mono)">
            {v === 0 ? "0" : (v > 0 ? "+" : "−") + _currencySymbol + Math.round(Math.abs(v))}
          </text>
        ))}
        {data.map((d, i) => {
          const x = pad.l + (i / data.length) * innerW + 1.5;
          const zero = pad.t + innerH / 2;
          const y = d.v >= 0 ? ys(d.v) : zero;
          const h = Math.max(1, Math.abs(ys(d.v) - zero));
          const c = pnlColor(d.v);

          return (
            <g key={i}>
              <rect x={x} y={y} width={Math.max(2, barW)} height={h} rx="1.5" fill={c} opacity={Math.abs(d.v) / max * 0.55 + 0.45}/>
            </g>
          );
        })}
        {[0, .5, 1].map((t, i) => {
          const idx = Math.round(t * (data.length - 1));
          const d = data[idx];
          const label = d.daysAgo === 0 ? "today" : (d.date ? fmtDateLabel(d.date) : `${d.daysAgo}d`);
          return (
            <text key={i} x={pad.l + (idx / data.length) * innerW + barW / 2}
                  y={height - 6} textAnchor="middle" fontSize="11" fill="var(--muted)">
              {label}
            </text>
          );
        })}
        {hover && (
          <line x1={hover.x} x2={hover.x} y1={pad.t} y2={pad.t + innerH} stroke="var(--border-3)" strokeDasharray="2 3"/>
        )}
      </svg>
      {hover && (
        <div style={{
          position: "absolute",
          left: Math.min(w - 180, Math.max(0, hover.x + 12)), 
          top: Math.max(8, pad.t + innerH / 2 - 42),
          background: "var(--panel-3)", border: "1px solid var(--border-2)",
          borderRadius: 8, padding: "8px 12px", fontSize: 12.5,
          pointerEvents: "none", boxShadow: "0 6px 20px rgba(0,0,0,.4)",
          whiteSpace: "nowrap", zIndex: 10
        }}>
          <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>
            {data[hover.i].daysAgo === 0 ? "today" : fmtDateLabel(data[hover.i].date)}
          </div>
          <div className="num" style={{ fontWeight: 600 }}>{fmtUsd(data[hover.i].v, 0)}</div>
        </div>
      )}
    </div>
  );
}

// ── Win/Loss donut ────────────────────────────────────────────────────────────
function WinLossDonut({ wins, losses, size = 132, stroke = 14 }) {
  const total = wins + losses || 1;
  const winFrac = wins / total;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size/2} cy={size/2} r={r} stroke="var(--down)" strokeWidth={stroke} fill="none" opacity=".25"/>
        <circle cx={size/2} cy={size/2} r={r} stroke="var(--up)" strokeWidth={stroke} fill="none"
                strokeDasharray={`${winFrac * c} ${c}`} strokeDashoffset={c * 0.25}
                transform={`rotate(-90 ${size/2} ${size/2})`}/>
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div className="num" style={{ fontSize: 25, fontWeight: 600, color: "var(--up)" }}>{(winFrac * 100).toFixed(0)}%</div>
          <div className="muted" style={{ fontSize: 12 }}>win rate</div>
        </div>
      </div>
    </div>
  );
}

// ── Sortable column header ────────────────────────────────────────────────────
function ColHead({ children, sortKey, sort, setSort, align = "left", style }) {
  const active = !!(sortKey && sort && sort.key === sortKey);
  const dir = active ? sort.dir : null;
  return (
    <th style={{
      textAlign: align, padding: "0 14px",
      fontSize: 11.5, fontWeight: 600, letterSpacing: ".09em",
      textTransform: "uppercase", color: "var(--muted)",
      borderBottom: "1px solid var(--border)",
      whiteSpace: "nowrap", height: 36,
      ...style,
    }}>
      {sortKey ? (
        <button type="button"
          onClick={() => setSort({ key: sortKey, dir: active && dir === "desc" ? "asc" : "desc" })}
          style={{
            background: "none", border: 0, color: active ? "var(--text)" : "inherit",
            font: "inherit", letterSpacing: "inherit", textTransform: "inherit",
            cursor: "pointer", padding: 0,
            display: "inline-flex", alignItems: "center", gap: 4,
          }}>
          {children}
          <span style={{ display: "inline-flex", flexDirection: "column", marginLeft: 1, opacity: active ? 1 : .4 }}>
            <Icon name="chevron-up" size={9} style={{ marginBottom: -3, opacity: dir === "asc" ? 1 : .45 }}/>
            <Icon name="chevron-down" size={9} style={{ marginTop: -3, opacity: dir === "desc" ? 1 : .45 }}/>
          </span>
        </button>
      ) : children}
    </th>
  );
}

// ── Segmented control ─────────────────────────────────────────────────────────
function Segmented({ value, options, onChange, size = "md" }) {
  const pad = size === "sm" ? "5px 10px" : "7px 13px";
  const fs = size === "sm" ? 11.5 : 12.5;
  return (
    <div style={{ display: "inline-flex", padding: 3, borderRadius: 9, background: "var(--panel-2)", border: "1px solid var(--border)" }}>
      {options.map(o => {
        const v = typeof o === "object" ? o.value : o;
        const l = typeof o === "object" ? o.label : o;
        const on = v === value;
        return (
          <button key={v} type="button" onClick={() => onChange(v)} style={{
            padding: pad, fontSize: fs, fontWeight: 500, border: 0, borderRadius: 7,
            background: on ? "var(--panel-3)" : "transparent",
            color: on ? "var(--text)" : "var(--muted)",
            boxShadow: on ? "0 1px 0 rgba(255,255,255,.04) inset, 0 0 0 1px var(--border-2)" : "none",
            cursor: "pointer", fontFamily: "inherit",
          }}>{l}</button>
        );
      })}
    </div>
  );
}

// ── Chip ─────────────────────────────────────────────────────────────────────
function Chip({ children, tone = "default", icon }) {
  const tones = {
    default: { bg: "var(--panel-2)", fg: "var(--text-2)", bd: "var(--border)" },
    accent:  { bg: "var(--accent-soft)", fg: "var(--accent)", bd: "var(--accent-line)" },
    up:      { bg: "var(--up-soft)", fg: "var(--up)", bd: "var(--up-line)" },
    down:    { bg: "var(--down-soft)", fg: "var(--down)", bd: "var(--down-line)" },
    warn:    { bg: "rgba(255,183,74,.12)", fg: "var(--warn)", bd: "rgba(255,183,74,.32)" },
  };
  const t = tones[tone] || tones.default;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "3px 8px", borderRadius: 999,
      background: t.bg, color: t.fg, border: `1px solid ${t.bd}`,
      fontSize: 12, fontWeight: 500, whiteSpace: "nowrap",
    }}>
      {icon && <Icon name={icon} size={11}/>}
      {children}
    </span>
  );
}

// ── Button ────────────────────────────────────────────────────────────────────
function Btn({ children, icon, onClick, tone = "default", size = "md", title, style, disabled }) {
  const sz = size === "sm" ? { p: "5px 9px", fs: 11.5, ic: 12 }
           : size === "lg" ? { p: "9px 16px", fs: 13, ic: 14 }
           : { p: "7px 12px", fs: 12, ic: 13 };
  const tones = {
    default: { bg: "var(--panel-2)", fg: "var(--text)", bd: "var(--border-2)" },
    ghost:   { bg: "transparent", fg: "var(--text-2)", bd: "transparent" },
    accent:  { bg: "var(--accent)", fg: "#062523", bd: "var(--accent)" },
    danger:  { bg: "var(--down-soft)", fg: "var(--down)", bd: "var(--down-line)" },
  };
  const t = tones[tone] || tones.default;
  return (
    <button type="button" onClick={onClick} title={title} disabled={disabled}
      style={{
        display: "inline-flex", alignItems: "center", gap: 6,
        padding: sz.p, fontSize: sz.fs, fontWeight: 500,
        background: t.bg, color: t.fg, border: `1px solid ${t.bd}`,
        borderRadius: 8, cursor: disabled ? "not-allowed" : "pointer",
        letterSpacing: ".01em", fontFamily: "inherit",
        opacity: disabled ? .5 : 1,
        ...style,
      }}>
      {icon && <Icon name={icon} size={sz.ic}/>}
      {children}
    </button>
  );
}

// ── Search input ──────────────────────────────────────────────────────────────
function SearchInput({ value, onChange, placeholder }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      background: "var(--panel-2)", border: "1px solid var(--border-2)",
      borderRadius: 8, padding: "6px 10px", minWidth: "min(220px, 100%)",
    }}>
      <Icon name="search" size={13} style={{ color: "var(--muted)" }}/>
      <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        style={{
          background: "transparent", border: 0, outline: 0,
          color: "var(--text)", fontSize: 13, fontFamily: "inherit", flex: 1, minWidth: 0,
        }}/>
    </div>
  );
}

// ── KPI card ──────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, tone, spark, info, big, loading, style }) {
  const color = tone === "up" ? "var(--up)" : tone === "down" ? "var(--down)" : "var(--text)";
  return (
    <div style={{
      background: "var(--panel)", border: "1px solid var(--border)", borderRadius: 14,
      padding: "18px 20px", display: "flex", flexDirection: "column", gap: 4,
      position: "relative", overflow: "hidden", minWidth: 0,
      ...style,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--muted)" }}>
        <span style={{ fontSize: 12.5, letterSpacing: ".06em", textTransform: "uppercase", fontWeight: 500 }}>{label}</span>
        {info && (
          <span title={typeof info === 'string' ? info : undefined} style={{ cursor: "help", display: "inline-flex" }}>
            <Icon name="info" size={12} style={{ opacity: .55 }}/>
          </span>
        )}
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: big ? 36 : 28, width: "60%", marginTop: 4 }}/>
      ) : (
        <div className="num" style={{ fontSize: big ? 31 : 25, fontWeight: 600, color, letterSpacing: "-.01em", marginTop: 4 }}>{value}</div>
      )}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 4 }}>
        {loading ? <div className="skeleton" style={{ height: 12, width: "80%" }}/> :
          sub && <span style={{ fontSize: 12.5, color: "var(--muted)" }}>{sub}</span>}
        {!loading && spark && <div style={{ marginLeft: "auto" }}><Sparkline data={spark} width={90} height={26}/></div>}
      </div>
    </div>
  );
}


// ── Mobile row card ───────────────────────────────────────────────────────────
function MobileRowCard({ pair, pnlAbs, highlight, onClick, children }) {
  const ref = useRef(null);
  useEffect(() => {
    if (highlight && ref.current) ref.current.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight]);

  return (
    <div
      ref={ref}
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 12, padding: highlight ? "12px 8px" : "12px 0",
        borderBottom: "1px solid var(--border)",
        cursor: onClick ? "pointer" : "default",
        background: highlight ? "var(--accent-soft)" : undefined,
        boxShadow: highlight ? "inset 2px 0 0 var(--accent)" : undefined,
        borderRadius: highlight ? 6 : undefined,
      }}>
      <PairToken pair={pair} size={36}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 3 }}>
          <span style={{ fontWeight: 600, fontSize: 14.5 }}>{pair}</span>
          <span className="num" style={{ fontSize: 15, fontWeight: 700, color: pnlColor(pnlAbs) }}>
            {fmtSignedUsd(pnlAbs)}
          </span>
        </div>
        {children}
      </div>
    </div>
  );
}

// ── Mobile position card ──────────────────────────────────────────────────────
function MobilePositionCard({ p, onPairClick, refresh }) {
  const pos = p.pnlAbs >= 0;
  const [selling, setSelling] = useState(false);

  const onSell = async (e) => {
    e.stopPropagation();
    if (selling) return;
    if (!window.confirm(`Are you sure you want to force sell ${p.pair} at market price?`)) return;
    try {
      setSelling(true);
      const cfg = window.loadConfig?.() || JSON.parse(localStorage.getItem("ft_config") || "{}");
      await window.forceExit(cfg?.url || "", p.id);
      if (refresh) await refresh();
    } catch (err) {
      console.error("Force exit failed", err);
      alert("Failed to force exit position.");
    } finally {
      setSelling(false);
    }
  };

  return (
    <MobileRowCard pair={p.pair} pnlAbs={p.pnlAbs} onClick={onPairClick ? () => onPairClick(p.pair) : undefined}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="num muted" style={{ fontSize: 12 }}>
          {fmtPrice(p.entry)} → <span style={{ color: pnlColor(p.pnlPct) }}>{fmtPrice(p.current)}</span>
        </span>
        <PnlPill pct={p.pnlPct} size="sm"/>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
        <span className="muted" style={{ fontSize: 11.5 }}>
          {p.strategy} · {fmtDuration(Date.now() - p.openedAt)}
        </span>
        <button onClick={onSell} disabled={selling} style={{
          background: "transparent", border: "1px solid var(--border-3)", color: "var(--text)", 
          padding: "2px 8px", borderRadius: 4, fontSize: 11, cursor: "pointer", pointerEvents: "auto"
        }}>
          {selling ? "..." : "Sell"}
        </button>
      </div>
    </MobileRowCard>
  );
}

// ── Mobile trade card ─────────────────────────────────────────────────────────
function MobileTradeCard({ t, onPairClick, highlight }) {
  const pos = t.pnlAbs >= 0;
  return (
    <MobileRowCard pair={t.pair} pnlAbs={t.pnlAbs} highlight={highlight} onClick={onPairClick ? () => onPairClick(t.pair) : undefined}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span className="muted" style={{ fontSize: 12 }}>{fmtTimeAgo(t.closedAt)}</span>
        <Chip tone={pnlTone(t.pnlPct)}>{fmtPct(t.pnlPct)}</Chip>
      </div>
      <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>
        {t.reason} · {fmtDuration(t.durMin * 60000)}
      </div>
    </MobileRowCard>
  );
}

// ── Mobile signal card ────────────────────────────────────────────────────────
function MobileSignalCard({ r, onPairClick }) {
  if (!r.ok) {
    return (
      <div
        onClick={onPairClick ? () => onPairClick(r.pair) : undefined}
        style={{
          display: "flex", alignItems: "center", gap: 10, padding: "10px 0",
          borderBottom: "1px solid var(--border)",
          cursor: onPairClick ? "pointer" : "default",
        }}>
        <PairToken pair={r.pair} size={32}/>
        <span className="muted" style={{ fontSize: 12 }}>No candle data</span>
      </div>
    );
  }
  const summaryText = r.ready ? "ENTRY" : r.total > 0 ? `${r.fired}/${r.total}` : "—";
  const summaryTone = r.ready ? "up" : (r.fired > 0 && r.total > 0) ? "warn" : "default";
  return (
    <div
      onClick={onPairClick ? () => onPairClick(r.pair) : undefined}
      style={{
        display: "flex", alignItems: "center", gap: 12, padding: "11px 0",
        borderBottom: "1px solid var(--border)",
        background: r.ready ? "rgba(42,208,123,.04)" : undefined,
        cursor: onPairClick ? "pointer" : "default",
      }}>
      <PairToken pair={r.pair} size={34}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{r.pair}</span>
          <Chip tone={summaryTone}>{summaryText}</Chip>
        </div>
        <div className="muted" style={{ fontSize: 11.5 }}>
          {r.close != null ? `Close: ${fmtPrice(r.close)}` : "—"}
          {r.cells && r.cells.filter(c => c.type === "binary").map(c => ` · ${c.label}: ${c.on ? "✓" : "–"}`).join("")}
        </div>
      </div>
    </div>
  );
}

// ── Sort helper ───────────────────────────────────────────────────────────────
function applySort(rows, sort, accessor) {
  if (!sort) return rows;
  const a = accessor || ((r, k) => r[k]);
  const sign = sort.dir === "asc" ? 1 : -1;
  return [...rows].sort((x, y) => {
    const vx = a(x, sort.key), vy = a(y, sort.key);
    if (vx == null) return 1;
    if (vy == null) return -1;
    if (typeof vx === "number") return (vx - vy) * sign;
    return String(vx).localeCompare(String(vy)) * sign;
  });
}

Object.assign(window, {
  fmtMoney, fmtUsd, fmtSignedUsd, fmtPct, fmtPrice, fmtCompact,
  fmtDuration, fmtTimeAgo, fmtTime,
  setCurrency, getCurrency,
  sparkSeries, mulberry32, hashStr,
  Icon, PairToken, PairLabel, Card, PnlPill, TableStack, Sparkline, StatusDot,
  EquityChart, DailyBars, WinLossDonut,
  ColHead, Segmented, Chip, Btn, SearchInput, KpiCard, applySort,
  useBreakpoint,
  MobilePositionCard, MobileTradeCard, MobileSignalCard,
});
