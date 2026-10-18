import {
  CRYPTO_UNIVERSE, alertFormError, buildAlertPayload, filterRows, formatNumber,
  formatPct, parseSymbols, sortRows, sparkPath,
} from "./intel";

describe("parseSymbols", () => {
  test("uppercases, trims and de-duplicates", () => {
    expect(parseSymbols(" btc-usd, ETH-USD ,btc-usd ").symbols).toEqual(["BTC-USD", "ETH-USD"]);
  });

  test("never silently drops invalid or out-of-universe symbols", () => {
    expect(parseSymbols("AAPL;$DROP").error).toMatch(/Invalid symbol/);
    expect(parseSymbols("FAKE-USD", { universe: CRYPTO_UNIVERSE }).error).toMatch(/public scan universe/);
    expect(parseSymbols("").error).toMatch(/at least one/);
  });

  test("enforces the per-scan cap", () => {
    const nine = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD", "LINK-USD", "BTC-USDx"];
    expect(parseSymbols(nine.join(",")).error).toMatch(/At most 8/);
  });
});

describe("formatting keeps unknown values unknown", () => {
  test("null is an em dash, never zero", () => {
    expect(formatPct(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
    expect(formatPct(Number.NaN)).toBe("—");
  });

  test("percentages are signed", () => {
    expect(formatPct(1.234)).toBe("+1.23%");
    expect(formatPct(-0.5)).toBe("-0.50%");
  });
});

describe("sortRows", () => {
  const rows = [
    { symbol: "A", attention_score: 10 },
    { symbol: "B", attention_score: null },
    { symbol: "C", attention_score: 40 },
  ];

  test("sorts numerically and leaves the input untouched", () => {
    expect(sortRows(rows, "attention_score", "desc").map((r) => r.symbol)).toEqual(["C", "A", "B"]);
    expect(rows.map((r) => r.symbol)).toEqual(["A", "B", "C"]);
  });

  test("missing values sort last in both directions", () => {
    expect(sortRows(rows, "attention_score", "asc").map((r) => r.symbol)).toEqual(["A", "C", "B"]);
  });
});

describe("filterRows", () => {
  const rows = [
    { symbol: "BTC-USD", signals: [{ code: "BREAKOUT_20" }] },
    { symbol: "ETH-USD", signals: [] },
  ];

  test("filters by symbol and signal presence", () => {
    expect(filterRows(rows, { query: "eth" }).map((r) => r.symbol)).toEqual(["ETH-USD"]);
    expect(filterRows(rows, { signalsOnly: true }).map((r) => r.symbol)).toEqual(["BTC-USD"]);
    expect(filterRows(rows).length).toBe(2);
  });
});

describe("alert payloads", () => {
  const base = { name: "Breakout", kind: "price_above", symbol: "btc-usd", threshold: "100000" };

  test("price alerts need a symbol and a positive threshold", () => {
    expect(alertFormError(base)).toBeNull();
    expect(alertFormError({ ...base, symbol: "" })).toMatch(/symbol/i);
    expect(alertFormError({ ...base, threshold: "0" })).toMatch(/positive/);
    expect(alertFormError({ ...base, threshold: "abc" })).toMatch(/positive/);
  });

  test("signal alerts need a known code", () => {
    expect(alertFormError({ name: "s", kind: "signal", signal_code: "NOPE" })).toMatch(/signal/i);
    expect(alertFormError({ name: "s", kind: "signal", signal_code: "BREAKOUT_20" })).toBeNull();
  });

  test("payload normalises symbols and drops irrelevant fields", () => {
    const built = buildAlertPayload(base);
    expect(built.ok).toBe(true);
    expect(built.payload).toEqual({
      name: "Breakout", kind: "price_above", symbol: "BTC-USD", threshold: 100000, signal_code: null,
    });
    expect(buildAlertPayload({ name: "v", kind: "social_velocity", symbol: "aapl", threshold: "9" }).payload)
      .toEqual({ name: "v", kind: "social_velocity", symbol: "AAPL", threshold: null, signal_code: null });
    expect(buildAlertPayload({ name: "" }).ok).toBe(false);
  });
});

describe("sparkPath", () => {
  test("returns null instead of drawing invented data", () => {
    expect(sparkPath(null)).toBeNull();
    expect(sparkPath([1])).toBeNull();
    expect(sparkPath([1, null, NaN])).toBeNull();
  });

  test("maps values inside the SVG box", () => {
    const points = sparkPath([1, 2, 3], 100, 20).split(" ");
    expect(points).toHaveLength(3);
    const [lastX, lastY] = points[2].split(",").map(Number);
    expect(lastX).toBe(100);
    expect(lastY).toBeGreaterThanOrEqual(0);
    expect(lastY).toBeLessThanOrEqual(20);
  });
});
