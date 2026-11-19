# Broker connection menu — extension 1.7.40

The member broker picker separates:

- **Browser connections:** Pocket Option's existing browser-chart connection.
- **API-key brokers:** Coinbase has an implemented account/setup adapter; Kraken
  and Binance.US are labeled not active and cannot be selected for trading.
- **Other brokers:** catalog placeholders, disabled until their adapters and
  connection methods are implemented. No OAuth eligibility is implied.

Choosing active Coinbase opens the fixed KAOS member page
`https://tradingwithkaos.com/dashboard/api?broker=coinbase`. The extension no longer
asks members to paste keys. The authenticated website owns the existing encrypted
credential setup and, when configured, the pending Coinbase OAuth alternative.
There is also a **KAOS API Setup** entry in the member sidebar.

After setup, return to the extension and choose **Continue with saved Coinbase
connection**. The extension verifies the current member's saved Coinbase account
before selecting the broker. Setup/selection does not start trading. An existing
extension sign-in is not transferred to the website by putting tokens in a URL.
Password and Google website sign-in retain the fixed API setup destination.

Only implemented adapters are enabled; adding a menu item does not activate a
broker or bypass membership, credentials, broker permissions or order controls.
No hosting files were installed, new broker enabled or live orders sent by this
menu update. Syntax, production web build, and extension packaging checks are
performed; no new test suite is run under the owner's previous instruction.
