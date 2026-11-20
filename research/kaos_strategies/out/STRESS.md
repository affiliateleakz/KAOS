# Cost and payout stress (out-of-sample)

Expectancy per trade; PF = profit factor. Cost is charged on entry and exit.

| Strategy | cost 0.000 ATR/side | cost 0.020 ATR/side | cost 0.050 ATR/side | cost 0.100 ATR/side |
|---|---|---|---|---|
| KAOS Pulse - range mean reversion | +0.050 (PF 1.04) | +0.010 (PF 1.01) | -0.050 (PF 0.96) | -0.150 (PF 0.89) |
| KAOS Drive - trend pullback | +0.022 (PF 1.03) | -0.018 (PF 0.97) | -0.078 (PF 0.89) | -0.178 (PF 0.77) |
| KAOS ORB - US opening range breakout | +0.269 (PF 1.46) | +0.229 (PF 1.38) | +0.169 (PF 1.26) | +0.069 (PF 1.10) |
| KAOS FX Session - London open range breakout | +0.036 (PF 1.05) | -0.004 (PF 0.99) | -0.064 (PF 0.91) | -0.164 (PF 0.80) |
| KAOS Ignition - volatility expansion breakout | +0.146 (PF 1.16) | +0.106 (PF 1.11) | +0.046 (PF 1.05) | -0.054 (PF 0.95) |

## Binary options

Binary bets pay `payout` on a win and lose the stake on a loss, so break-even win rate is
`1/(1+payout)`. A rule below that line loses money however it is staked.

| Strategy | payout 60% | payout 80% | payout 92% |
|---|---|---|---|
| KAOS Binary - range fade, fixed expiry | -0.230 (WR 48.1% vs 62.5%) | -0.134 (WR 48.1% vs 55.6%) | -0.077 (WR 48.1% vs 52.1%) |
