# Connecting your own Coinbase Advanced account to KAOS (View-only)

You enter the key yourself on the KAOS website. It never goes through Devin, chat, GitHub or screenshots.
Nothing is deployed yet, so this runs on a local copy of PRs #9–#11 (or a staging server you approve).

## 1. Create a View-only key at Coinbase
1. Go to https://portal.cdp.coinbase.com → API Keys → Create API key.
2. Permissions: tick **View** only. Do not tick Trade or Transfer. KAOS refuses Transfer keys.
3. Signature algorithm: ECDSA (Ed25519 also accepted). Optionally restrict it to your IP address.
4. Download the key JSON (`name` + `privateKey`). Keep it on your own computer.

## 2. Run KAOS locally
```bash
git clone https://github.com/affiliateleakz/KAOS && cd KAOS
git checkout devin/1792353508-coinbase-order-lifecycle   # PR #11 (includes #9 and #10)
cp .env.example .env
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # paste as KAOS_BROKER_VAULT_KEY in .env
docker compose up -d --build
```
Open http://localhost:3000, sign in, then go to Dashboard → Broker Connections → Coinbase Advanced.
Paste the key JSON (or its name and private key) and save. KAOS checks the permissions with Coinbase,
encrypts the key and shows only its last 4 characters.

## 3. What you should see (please report back)
- Balances, buying power, positions with value and P&L, open orders, recent fills and fee tier, refreshing every 15 s.
- The same data in the Chrome extension (Coinbase Account page) and the Android app (◎ Coinbase).
- "Preview order" should fail with a permission error on a View-only key. That is expected: preview needs a Trade key.
- Submit is disabled. Disconnect deletes the stored key.

Until this has been done with a real account, the account view stays labelled **UNVERIFIED**.
