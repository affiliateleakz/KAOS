// Pure helpers for the KAOS Market Intelligence Centre. No data is invented here:
// null/undefined always renders as an em dash rather than a zero.

export const MAX_SCAN_SYMBOLS = 8;

export const CRYPTO_UNIVERSE = [
  "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD",
  "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD",
];

export const ALERT_KINDS = [
  { value: "price_above", label: "Price at or above", needsSymbol: true, needsThreshold: true },
  { value: "price_below", label: "Price at or below", needsSymbol: true, needsThreshold: true },
  { value: "breakout_20", label: "20-bar breakout", needsSymbol: false, needsThreshold: false },
  { value: "unusual_volume", label: "Unusual volume (2x median)", needsSymbol: false, needsThreshold: false },
  { value: "social_velocity", label: "Stored social acceleration", needsSymbol: false, needsThreshold: false },
  { value: "signal", label: "Specific technical signal", needsSymbol: false, needsThreshold: false },
];

export const SIGNAL_CODES = [
  "BREAKOUT_20", "BREAKDOWN_20", "FAILED_BREAKOUT", "UNUSUAL_VOLUME",
  "VOLUME_ANOMALY", "MOMENTUM_UP", "MOMENTUM_DOWN", "VOLATILITY_EXPANSION",
  "NEAR_RESISTANCE", "NEAR_SUPPORT", "TREND_UP", "TREND_DOWN",
];

const SYMBOL = /^[A-Z][A-Z0-9.-]{0,14}$/;

export function parseSymbols(input, { universe = null, max = MAX_SCAN_SYMBOLS } = {}) {
  const items = String(input || "")
    .split(",")
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean);
  const symbols = [...new Set(items)];
  if (!symbols.length) return { symbols: [], error: "Enter at least one symbol." };
  if (symbols.length > max) return { symbols: [], error: `At most ${max} symbols per scan.` };
  const bad = symbols.filter((symbol) => !SYMBOL.test(symbol));
  if (bad.length) return { symbols: [], error: `Invalid symbol: ${bad.join(", ")}` };
  if (universe) {
    const outside = symbols.filter((symbol) => !universe.includes(symbol));
    if (outside.length) {
      return { symbols: [], error: `Not in the public scan universe: ${outside.join(", ")}` };
    }
  }
  return { symbols, error: null };
}

export function formatPct(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  const number = Number(value);
  return `${number >= 0 ? "+" : ""}${number.toFixed(digits)}%`;
}

export function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

export function freshnessLabel(row) {
  if (!row || !row.as_of) return "—";
  if (row.freshness === "recent") return "Recent";
  if (row.freshness === "stale_or_market_closed") return "Stale / market closed";
  return "—";
}

// Stable sort; missing values always sort last in either direction.
export function sortRows(rows, key, direction = "desc") {
  const factor = direction === "asc" ? 1 : -1;
  return [...(rows || [])].sort((a, b) => {
    const left = a?.[key];
    const right = b?.[key];
    const leftMissing = left === null || left === undefined || Number.isNaN(left);
    const rightMissing = right === null || right === undefined || Number.isNaN(right);
    if (leftMissing && rightMissing) return 0;
    if (leftMissing) return 1;
    if (rightMissing) return -1;
    if (typeof left === "number" && typeof right === "number") return (left - right) * factor;
    return String(left).localeCompare(String(right)) * factor;
  });
}

export function filterRows(rows, { query = "", signalsOnly = false } = {}) {
  const needle = String(query || "").trim().toUpperCase();
  return (rows || []).filter((row) => {
    const symbol = String(row?.symbol || row?.asset || "").toUpperCase();
    if (needle && !symbol.includes(needle)) return false;
    if (signalsOnly && !(row?.signals || []).length) return false;
    return true;
  });
}

export function alertFormError(form) {
  const kind = ALERT_KINDS.find((entry) => entry.value === form?.kind);
  if (!form?.name || !String(form.name).trim()) return "Give the alert a name.";
  if (!kind) return "Choose an alert type.";
  if (kind.needsSymbol && !String(form.symbol || "").trim()) return "This alert needs a symbol.";
  if (kind.needsThreshold) {
    const threshold = Number(form.threshold);
    if (!Number.isFinite(threshold) || threshold <= 0) return "Enter a positive price threshold.";
  }
  if (form.kind === "signal" && !SIGNAL_CODES.includes(form.signal_code)) {
    return "Choose the technical signal to watch.";
  }
  return null;
}

export function buildAlertPayload(form) {
  const error = alertFormError(form);
  if (error) return { ok: false, error, payload: null };
  const kind = ALERT_KINDS.find((entry) => entry.value === form.kind);
  return {
    ok: true,
    error: null,
    payload: {
      name: String(form.name).trim(),
      kind: form.kind,
      symbol: String(form.symbol || "").trim().toUpperCase() || null,
      threshold: kind.needsThreshold ? Number(form.threshold) : null,
      signal_code: form.kind === "signal" ? form.signal_code : null,
    },
  };
}

export function sparkPath(values, width = 96, height = 28) {
  if (!Array.isArray(values) || values.length < 2) return null;
  // Null/NaN must break the chart rather than being coerced to 0.
  const points = values.map((value) => (typeof value === "number" ? value : Number.NaN));
  if (!points.every((value) => Number.isFinite(value))) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * width;
      const y = height - ((value - min) / span) * height;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function signalTone(direction) {
  if (direction === "bullish") return "text-[#2F8CFF] border-[#2F8CFF]/30 bg-[#2F8CFF]/10";
  if (direction === "bearish") return "text-[#C62828] border-[#C62828]/30 bg-[#C62828]/10";
  return "text-slate-300 border-[#3A3A3A] bg-[#151515]";
}
