# Website and extension paper model — 1.7.33

The owner research model now ships in the backend at `apps/api/research_models/micro_reversion_v1.json`. An authenticated super-admin-only GET endpoint (`/api/v1/ai/research/micro-reversion`) returns it with `Cache-Control: private, no-store`. It is not added to the normal model registry, and ordinary Pro/Ultimate members cannot request it.

After installing the latest website/backend package and restarting the API:

- Website: sign in as super admin → KAOS AI → Open experimental paper test. The model loads automatically; no JSON upload is needed.
- Extension: update the existing unpacked extension to 1.7.33 → Bot → Open paper test. It loads the same owner model through the authenticated background client. A manual model-file fallback remains available if the backend is unavailable.
- Choose a crypto market and click Start live paper feed, or replay a local five-second candle file. Defaults retain the known one-basis-point adverse entry assumption. Export before closing or changing tests.

Website testing runs in the browser with direct GET requests to the public Binance data host only after Start. It does not add polling or training work to the shared hosting server. The website and extension use the same paper engine and source-second aggregator. Model weights are not bundled into public website JavaScript or the extension package. Stop/unmount aborts requests and clears timers. These controls do not connect to a broker or execute orders.

The frozen model failed the adverse-fill gate and remains owner-only research. Neither installation nor model loading publishes it to members or enables live execution. The site/privacy source and deployment packages have been prepared; installing them on hosting is a separate terminal action.

Historical 1.7.32 manual setup notes follow for existing builds.

# Micro Reversion paper test — extension 1.7.32

This adds an isolated research test page to the existing KAOS extension. It does not replace the production KAOS Strategy, install a trained model for all members, connect to a broker, or submit orders. Official Chrome Store identity and Google sign-in configuration are retained.

## Owner test steps

1. Download `downloads/KAOS-Chrome-Extension-1.7.32.zip`, extract into your existing unpacked extension folder, then Reload under chrome://extensions. Use the existing official listing/key rather than creating a new store item. A Store-installed copy needs the normal developer submission/update process instead; no submission was made automatically.
2. Download `downloads/KAOS-Micro-Reversion-Paper-Model.json` as a file. This separate experimental research model is not loaded into regular member bots.
3. In the Bot menu, choose **Open paper test**, then load that JSON under **Experimental model JSON**. Do not choose the native XGBoost `selected_model.json` or an account backup.
4. Select BTCUSDT, ETHUSDT or SOLUSDT. Keep adverse entry at **1 basis point** initially to expose the known fill sensitivity. The payout is a hypothetical paper assumption, not an observed exchange or broker payout.
5. Click **Start live paper feed** and grant the optional permission to the exact public Binance-data host. This is public market-data access only, without trading credentials or API keys. Warmup history creates no retrospective forward-test trades. After 320 contiguous completed five-second candles, new data can generate paper entries at a following candle open and settlements 15 seconds later.
6. Click **Stop**, then **Export paper results** before closing/reloading or starting another test. Exported results include source mode, model ID, assumptions, unresolved positions, gaps/cancellations and simulated outcomes. No results are uploaded automatically.

The current model was trained on Binance BTC/ETH/SOL, not Pocket Option OTC. Do not interpret this screen as a Pocket Option strategy test. If the public host is unavailable, denied or region-restricted, the screen displays an error. You can instead expand **Replay a candle file**, unzip the public candle-history download and select one market's five-second JSON. Historical replay is clearly labeled and must not be presented as a new forward test.

## Execution and data boundaries

The paper core has no Chrome/broker messaging, order endpoints or execution calls. The page performs GET requests only to `https://data-api.binance.vision` after an explicit Start and runtime permission. Model files/candle files/results remain local. Source seconds are aggregated only into complete five-second buckets with actual trades. Missing intervals reset warmup and cancel unresolved positions. Network requests have a 15-second timeout and polls do not overlap. Stop cancels requests/timers; settings are locked during an active test. The page is intentionally not linked to the live trading Start button.

Optional feed access is declared under `optional_host_permissions`; existing installs are not forced to grant a new required host permission. Store privacy/use disclosures should describe the optional public-data feed. The website privacy source was updated, but no hosting files or Store submission were changed here.

## Verification

- Browser feature vectors and portable-tree scores match Python/XGBoost at 99 checkpoints over 2,000 public candles, including non-HOLD signals.
- Unit tests cover exact entry/expiry, adverse entry, gaps/cancellations, warmup-only history and unsupported markets.
- Browser fixtures cover explicit model import, permission only on Start, three bounded warmup requests, zero invented warmup trades, Stop, local replay/export and narrow-screen layout. These are simulated provider responses, not proof of availability on the user's network.
- ZIP checks verify official identity, include the paper UI, and exclude model weights and test fixtures from the extension package.

The historical candidate failed the 0.01% adverse-fill gate. See `research/crypto_strategy_v1/README.md` for the full results. The next valid evidence is new forward paper observation; no live approval is implied.
