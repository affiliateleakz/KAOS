# KAOS Trading 3.0 v0.5 — Whale & Insider Intelligence

**Development source, not a deployed or live-tested trading system.**
No collector here can place broker orders. Research priorities are not predicted returns or win rates.

## Included (new in v0.5)

1. `ethereum_worker.py` + `ethereum_whales.py` — optional native-ETH value transaction scanner for Ethereum **safe** blocks. Reads `eth_getBlockByNumber` through a customer-configured HTTPS Ethereum JSON-RPC node. Uses a durable safe-block cursor (`KAOS_ETH_CHECKPOINT`) and bounded incremental catch-up of up to 32 blocks per cycle. On the initial run, it samples the latest safe block only; historical scan coverage begins after the first successful checkpoint. Reports thresholded **native ETH transaction value** (default 500 ETH). This is **not** a verified investor identity, ETH buy/sell, exchange flow, token transfer, or proof of intent. ERC-20 transfers, internal calls, contract balance changes, L2s, Solana and wallets are out of scope.
2. `sec_insider_transactions.py` — attempts to parse *non-derivative* open-market Form 4 transaction-code `P` with acquired `A`, or `S` with disposed `D` from publicly available SEC primary ownership XML files. Reports reported **purchase versus sale** and **transaction date versus disclosure date**, but still submits **neutral** direction. Filing discovery remains intact even if ownership XML is not available. Does not parse Form 4/A amendments, derivative tables, grants, gifts, indirect ownership semantics, funds or full history. A stock's issuer CIK submissions may omit ownership filings filed under individuals' own CIKs. This adapter is incomplete market coverage.
3. Website + mobile: evidence filters for reported insider transactions, native ETH observations, and future options flow research; source-quality caveats clearly stated. Chrome extension trading execution unchanged.
4. Backend source-health: identifies `eth-mainnet` and `sec-form4-txn` event IDs separately.

## Configuration

Set (only on an always-on backend worker/VPS, not client-side):

```bash
export SEC_USER_AGENT='KAOS Research your-monitored-contact@example.com'
export KAOS_API_BASE='https://api.tradingwithkaos.com'
export KAOS_COLLECTOR_KEY='YOUR_PRIVATE_SERVER_SECRET'
export ETH_RPC_URL='https://YOUR_AUTHORIZED_ETHEREUM_NODE'
export KAOS_ETH_CHECKPOINT='/var/lib/kaos/ethereum_safe_checkpoint.json'
```

In `collectors/market_universe.example.json`, enable:

```json
"eth_whales_enabled": true,
"eth_whales_min_eth": 500
```

`SEC_USER_AGENT` must be a real monitored organization/contact string that satisfies SEC fair access; the example is a placeholder. `sec_watchlist` already exists for issuer CIK / ticker pairs and now also enables experimental Form 4 P/S XML parsing. Do not assume complete Form 4 coverage based on issuer CIK alone.

```bash
cd collectors
python market_collection_runner.py --config market_universe.example.json --dry-run
python market_collection_runner.py --config market_universe.example.json
# Only under a supervisor with a persistent checkpoint volume:
python market_collection_runner.py --config market_universe.example.json --loop --interval 300
```

**Dry run calls configured market-data providers but does not submit to KAOS or advance the Ethereum cursor.** Normal mode only commits the Ethereum cursor after all observations in that run have been acknowledged by KAOS, so failed delivery can be replayed with stable event IDs. The code must be deployed to a stable worker host with persistence, concurrency control (run a **single** worker for this checkpoint), and provider-appropriate rate limits.

## Provenance and known limitations

- No live network requests were run in build verification. Offline tests mock SEC and Ethereum JSON-RPC responses. Provider API schemes, quotas, tiers, and data fields can change.
- Ethereum scan is **only** one chain and native ETH `value`, does not include transfers inside smart contracts or ERC-20 transfers, and large transfers are not automatically purchases/sales. The scan uses `safe` block tag which the user's RPC must support. A time lag in RPC blocks can result in no observations; the user should monitor lag and backlog.
- This implementation limits catch-up to **32 blocks per pass**, on purpose for safety; backlogs require additional cycles. It is not a high-throughput Ethereum indexer; no guarantee of complete round-the-clock coverage under outages.
- SEC Form 4 XML primary documents can be non-XML, unavailable or omitted under issuer filings. The parser skips unknown transaction codes and does not infer beneficial ownership or price direction. `P`/`S` refer to *reported* buys/sells, not flow occurring at filing acceptance. No 13F holdings extraction or politician transaction parsing yet.
- Internal backend heuristics are research priorities only. Social scanning, unusual-options market-wide tape, licensed dark pool flow, institution 13F holdings and politician transactions remain later phases.

## Tests

```bash
cd collectors && python -m unittest discover -p 'test_*.py' -v
cd ../backend_foundation && python -m unittest test_kaos_opportunity_neutral test_kaos_source_health
```

Use public/free data where feasible. Verify rate limits, API terms and redistribution rights before exposing data on the commercial member site. All passwords and tokens belong on trusted server workers.
