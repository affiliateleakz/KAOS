#!/usr/bin/env python3
"""Reproducible cross-client check of the shared KAOS paper session against a running local stack.

Website client = cookie session (POST /api/auth/login). Extension and mobile clients = bearer tokens
(POST /api/v1/extension/login, the same token type the Expo app sends). All three must see ONE
server-side account. Optional --restart-cmd restarts the API mid-run to check recovery.
Paper only: never touches a broker. Writes a JSON report.

  python scripts/e2e_paper_session.py --api http://localhost:8001 --restart-cmd "docker compose restart api"
"""
import argparse, concurrent.futures, json, os, subprocess, sys, time, uuid
import httpx

p = argparse.ArgumentParser()
p.add_argument("--api", default="http://localhost:8001")
p.add_argument("--user", default="bob@demotrader.com")
p.add_argument("--other", default="carol@demotrader.com")
p.add_argument("--admin", default=os.environ.get("ADMIN_EMAIL", "owner@example.com"))
p.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", ""))
p.add_argument("--password", default=os.environ.get("KAOS_DEMO_PASSWORD", "dev-demo-password"))
p.add_argument("--restart-cmd", default="")
p.add_argument("--report", default="e2e_paper_report.json")
a = p.parse_args()
results = []


def check(step, name, ok, detail=""):
    results.append({"step": step, "check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {step} {name} {detail}")


def web_client(email, password=None):
    c = httpx.Client(base_url=a.api, timeout=20)
    r = c.post("/api/auth/login", json={"email": email, "password": password or a.password})
    r.raise_for_status()
    # Cookies are Secure; browsers send them to http://localhost, httpx does not, so forward them explicitly.
    c.cookies.clear()
    c.headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in r.cookies.items())
    return c


def bearer_client(email, install):
    r = httpx.post(a.api + "/api/v1/extension/login", json={"email": email, "password": a.password, "install_id": install}, timeout=20)
    r.raise_for_status()
    return httpx.Client(base_url=a.api, timeout=20, headers={"Authorization": "Bearer " + r.json()["accessToken"]})


def wait_healthy():
    for _ in range(60):
        try:
            if httpx.get(a.api + "/api/health", timeout=3).json().get("status") == "ok":
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


P = "/api/v1/paper"
web, ext, mob = web_client(a.user), bearer_client(a.user, "e2e-extension"), bearer_client(a.user, "e2e-mobile")
clients = {"website": web, "extension": ext, "mobile": mob}
ids = {k: c.get("/api/auth/me").json().get("id") for k, c in clients.items()}
check(1, "same user in website, extension and mobile", len(set(ids.values())) == 1 and None not in ids.values(), json.dumps(ids))

sym = "ETH-USD"
r = ext.put(P + "/session", json={"broker": "kaos_paper_coinbase", "symbol": sym, "granularity": 300, "notional": "10",
                                   "fee_rate": "0.006", "slippage_bps": 5})
check(2, "extension sets session", r.status_code == 200, r.text[:120])
seen = {k: c.get(P + "/session").json() for k, c in clients.items()}
check(2, "session visible identically in all clients", all(s.get("symbol") == sym and s.get("granularity") == 300 and s.get("slippage_bps") == 5 for s in seen.values()), json.dumps(seen)[:300])
check(2, "unavailable broker refused", web.put(P + "/session", json={"broker": "pocket_option"}).status_code == 422)

q = web.get(P + f"/quote/{sym}").json()
check(4, "quote has timestamp, age, provenance and 'polling' delivery", all(k in q for k in ("quote_time", "age_seconds", "source", "delivery")) and q["delivery"] == "polling", json.dumps(q))
sig = mob.post(P + f"/signals/{sym}?granularity=300", json={"notional": "10"}).json()
check(3, "signal from confirmed candles with reasons + preview risk decision", sig.get("reasons") and "risk" in sig and sig.get("candle_time"),
      f"{sig.get('action')} {sig.get('setup')} risk={sig.get('risk')}")
if sig.get("action") == "HOLD":
    r = web.post(P + f"/signals/{sig['signal_id']}/execute")
    check(3, "HOLD signal cannot be executed", r.status_code == 409, r.text[:120])
check(3, "signal journal shared", any(s["signal_id"] == sig["signal_id"] for s in ext.get(P + "/signals").json()["signals"]))

before = web.get(P + "/orders").json()
cid = f"e2e-{uuid.uuid4().hex[:12]}"
with concurrent.futures.ThreadPoolExecutor(3) as ex:  # duplicate clicks from three clients at once
    futs = [ex.submit(c.post, P + "/orders", json={"symbol": sym, "asset_class": "CRYPTO_SPOT", "side": "BUY", "quantity": "5", "client_order_id": cid}) for c in clients.values()]
    rs = [f.result() for f in futs]
orders_now = web.get(P + "/orders").json()
mine = [o for o in orders_now["orders"] if o["client_order_id"] == cid]
check(6, "concurrent duplicate submits from 3 clients -> exactly one fill", len(mine) == 1, str([x.status_code for x in rs]))
if mine:
    o = mine[0]
    qq = o["quote"]
    exp = float(qq["ask"]) * (1 + 5 / 10000)
    check(4, "fill at fresh ask + configured slippage, with quote provenance", abs(float(o["fill_price"]) - exp) < 1e-6 and o["execution_kind"] == "market_data_paper", f"ask={qq['ask']} fill={o['fill_price']} quote_time={qq['quote_time']}")
    check(4, "fee recorded at session rate", abs(float(o["fee"]) - 5 * 0.006) < 1e-9 and "not a Coinbase" in o["fee_model"], o["fee"])
books = {k: c.get(P + "/orders").json()["book"] for k, c in clients.items()}
check(4, "cash/positions/P&L/fees identical across clients", len({json.dumps(b, sort_keys=True) for b in books.values()}) == 1, json.dumps(books["website"])[:200])
check(4, "cash decreased by notional + fee", abs(float(before["book"]["cash"]) - float(books["website"]["cash"]) - 5.03) < 0.006)

other = web_client(a.other)
oo = other.get(P + "/orders").json()
check(7, "other user cannot see this account's orders/signals", all(x["client_order_id"] != cid for x in oo["orders"]) and all(s["signal_id"] != sig["signal_id"] for s in other.get(P + "/signals").json()["signals"]))
check(7, "other user cannot execute this user's signal", other.post(P + f"/signals/{sig['signal_id']}/execute").status_code == 404)

check(9, "unsupported asset (no authorized feed) rejected, no fill", web.post(P + "/orders", json={"symbol": "SPY", "asset_class": "EQUITY", "side": "BUY", "quantity": "5"}).status_code in (422, 503))
check(9, "unrealistic fee setting rejected", web.put(P + "/session", json={"symbol": sym, "fee_rate": "0.5"}).status_code == 422)

admin = web_client(a.admin, a.admin_password)
ks = admin.post(P + "/kill-switch", json={"active": True, "reason": "e2e check"})
try:
    r = mob.post(P + "/orders", json={"symbol": sym, "asset_class": "CRYPTO_SPOT", "side": "BUY", "quantity": "5"})
    check(8, "emergency stop blocks execution from mobile client", ks.status_code == 200 and r.status_code == 422, r.text[:120])
    check(8, "member cannot lift emergency stop", web.post(P + "/kill-switch", json={"active": False}).status_code == 403)
finally:
    admin.post(P + "/kill-switch", json={"active": False, "reason": "e2e check done"})

if a.restart_cmd:
    subprocess.run(a.restart_cmd, shell=True, check=True)
    up = wait_healthy()
    web2, ext2, mob2 = web_client(a.user), bearer_client(a.user, "e2e-extension"), bearer_client(a.user, "e2e-mobile")
    after = {k: c.get(P + "/orders").json() for k, c in {"website": web2, "extension": ext2, "mobile": mob2}.items()}
    check(5, "after API restart + fresh client logins: same book, order and session", up and all(
        json.dumps(x["book"], sort_keys=True) == json.dumps(books["website"], sort_keys=True) and any(o["client_order_id"] == cid for o in x["orders"]) for x in after.values())
        and ext2.get(P + "/session").json()["symbol"] == sym)
    r = web2.post(P + "/orders", json={"symbol": sym, "asset_class": "CRYPTO_SPOT", "side": "BUY", "quantity": "5", "client_order_id": cid})
    check(6, "retry of the same order after restart does not double-fill", r.status_code == 200 and sum(o["client_order_id"] == cid for o in web2.get(P + "/orders").json()["orders"]) == 1)

# Founder milestone: a BUY placed on the website is visible on extension + mobile, and closed once from mobile.
mb = web_client(a.user)
wcid = "e2e-web-buy-" + uuid.uuid4().hex[:8]
r = mb.post(P + "/orders", json={"symbol": sym, "asset_class": "CRYPTO_SPOT", "side": "BUY", "quantity": "5", "client_order_id": wcid})
seen_pos = {k: next((x for x in c.get(P + "/orders").json()["book"]["positions"] if x["symbol"] == sym), None)
            for k, c in {"extension": bearer_client(a.user, "e2e-extension"), "mobile": bearer_client(a.user, "e2e-mobile")}.items()}
check(10, "website BUY visible as the same position in extension and mobile", r.status_code == 200 and all(seen_pos.values())
      and len({json.dumps(v, sort_keys=True) for v in seen_pos.values()}) == 1, json.dumps(seen_pos)[:200])
mob3 = bearer_client(a.user, "e2e-mobile")
ccid = "e2e-mob-close-" + uuid.uuid4().hex[:8]
with concurrent.futures.ThreadPoolExecutor(3) as pool:
    cl = list(pool.map(lambda _: mob3.post(P + f"/positions/{sym}/close", json={"client_order_id": ccid}), range(3)))
final = {k: c.get(P + "/orders").json() for k, c in {"website": mb, "extension": bearer_client(a.user, "e2e-extension"), "mobile": mob3}.items()}
check(10, "mobile close (sent 3x) -> exactly one SELL at the bid, position flat in every client",
      all(x.status_code == 200 for x in cl) and all(sum(o["client_order_id"] == ccid for o in f["orders"]) == 1
      and not any(p_["symbol"] == sym for p_ in f["book"]["positions"]) for f in final.values())
      and len({json.dumps(f["book"], sort_keys=True) for f in final.values()}) == 1, str([x.status_code for x in cl]))
cfill = next(o for o in final["website"]["orders"] if o["client_order_id"] == ccid)
check(10, "close filled from a fresh quote at bid minus slippage", cfill.get("execution_kind") == "market_data_paper"
      and float(cfill["fill_price"]) <= float(cfill["quote"]["bid"]), f"bid={cfill['quote']['bid']} fill={cfill['fill_price']}")

# Approved signal from recorded genuine Coinbase candles -> execution re-checks risk on a fresh live quote -> exactly one fill.
rsym, rec = "BTC-USD", "coinbase_btc_usd_5m_breakout_long"
rw = web_client(a.user)
rs = rw.post(P + f"/signals/{rsym}", json={"notional": "5", "replay": rec})
rsig = rs.json() if rs.status_code == 200 else {}
check(3, "recorded genuine candles -> documented BUY approved by risk preview", rsig.get("action") == "BUY" and rsig.get("risk", {}).get("approved")
      and rsig.get("reasons") and str(rsig.get("candle_source", "")).startswith("recorded:"), rs.text[:200])
if rsig.get("status") == "PENDING":
    rclients = [bearer_client(a.user, "e2e-extension"), bearer_client(a.user, "e2e-mobile"), rw]
    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        ex = list(pool.map(lambda c: c.post(P + f"/signals/{rsig['signal_id']}/execute"), rclients))
    orders = rw.get(P + "/orders").json()["orders"]
    fills = [o for o in orders if o["client_order_id"] == f"exec-{rsig['signal_id']}"]
    check(6, "approved signal executed from 3 clients at once -> exactly one fill", len(fills) == 1, str([x.status_code for x in ex]))
    if fills:
        f0 = fills[0]
        check(4, "signal fill re-checked risk on a fresh quote (not the signal-time quote)", f0.get("execution_kind") == "market_data_paper"
              and f0["quote"]["quote_time"] >= rsig["quote"]["quote_time"] and float(f0["fill_price"]) >= float(f0["quote"]["ask"]),
              f"signal_quote={rsig['quote']['quote_time']} fill_quote={f0['quote']['quote_time']} ask={f0['quote']['ask']} fill={f0['fill_price']}")
    sig_now = next((x for x in rw.get(P + "/signals").json()["signals"] if x["signal_id"] == rsig["signal_id"]), {})
    check(6, "signal marked EXECUTED; replaying execute returns the same order", sig_now.get("status") == "EXECUTED"
          and rw.post(P + f"/signals/{rsig['signal_id']}/execute").json().get("client_order_id") == f"exec-{rsig['signal_id']}")
    rw.post(P + f"/positions/{rsym}/close", json={"client_order_id": "e2e-replay-close-" + uuid.uuid4().hex[:8]})

json.dump({"api": a.api, "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}, open(a.report, "w"), indent=2)
failed = [r for r in results if not r["pass"]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed. Report: {a.report}")
sys.exit(1 if failed else 0)
