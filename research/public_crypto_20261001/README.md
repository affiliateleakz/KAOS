# Public crypto candle history

Downloaded from Binance's public spot-data archive, covering **October 1–7, 2026 (UTC)**. No API key, account connection or trade execution was used. Data is separate from Pocket Option OTC prices and does not verify a broker-specific binary strategy.

| Market | Complete five-second bars with trades |
|---|---:|
| BTC/USDT | 120,918 |
| ETH/USDT | 118,814 |
| SOL/USDT | 117,902 |
| Total | 357,634 |

Download `downloads/KAOS-Public-Crypto-5s-2026-10-01-to-07.zip` for three JSON market files and the source manifest. Each JSON uses `markets: {symbol: [bars]}`. Bars contain millisecond `ts`, exclusive `closeTs`, OHLC, base volume and trade count. Rows are sorted, duplicates rejected. Symbols and dates are fixed; no per-market selection based on backtest returns was performed.

The collector downloaded 21 official daily one-second kline ZIPs and checked each SHA-256 against its published `.CHECKSUM` file. It handles the provider's microsecond timestamps explicitly. It aggregates only buckets containing exactly five source seconds, excludes five-second buckets with no trades, and does not interpolate gaps. Provider-carried zero-trade seconds inside a nonempty bucket can still affect its opening price; candle opens are not executable broker quotes. This is historical price research, not verified order fills or observed binary payouts.

`manifest.json` records source URLs, checksums, retrieval time, per-file counts and final JSON hashes. The distributed ZIP and all three JSON hashes were independently checked after packaging. Raw source archives are cached locally outside the repository, not added to the extension or website bundles.

Reproduce with Python and httpx:

```bash
python scripts/collect_public_candles.py --start 2026-10-01 --days 7 --out /private/kaos-public-candles --cache /private/kaos-source-cache
python -m pytest scripts/tests/test_public_candles.py -q
```

No strategy was fitted or promoted using this new dataset during collection. Freeze the next experiment and its chronological development/validation/test split before evaluating it. One week alone is limited evidence for robust cross-regime performance; the collector supports up to 31 completed days per run for a larger follow-up dataset. Live trading and hosting remain unchanged.

Source format/documentation: https://github.com/binance/binance-public-data
