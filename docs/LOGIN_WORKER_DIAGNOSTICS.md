# Login/Passenger investigation

Observed: the website document loads, while extension login reports 500 and
even public `/api` and an empty login POST have timed out. Support first reported
resource limits, then reported no current server fault explaining the requests.
This does not establish that the password or the current account quota is the cause.

The WSGI wrapper acquired its adapter lock before checking the process PID.
Python at-fork callbacks normally reset this, but a native host fork need not run
those callbacks. A regression fixture reproduces an inherited-lock deadlock with
callbacks disabled and proves that checking/resetting process state before
locking avoids it. API module loading is also deferred to adapter construction in
the serving worker, reducing preloaded database/client state. This is local
evidence of a failure mode, not proof of Asura's spawning behavior.

Before changing live files, run from the updated checkout:

```bash
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/diagnose_cpanel_wsgi.py
```

The probe imports the currently installed entrypoint, not the repository's new
one. It prints loading/request timings and status codes only. Each stage is bounded
at 20 seconds. Expected results are local GET `/api` = 200 and empty POST login =
422. No credentials are sent, ASGI lifespan is not started, and these two existing
FastAPI routes do not require database writes. Legacy-native runtime detection
stops before the login probe. Do not supply passwords to the script.

If local probes pass while public requests time out, give support both timings
and ask them to trace request dispatch, application selection, worker spawning,
worker recycling and WSGI iteration for the Python app. Do not add unsupported
Passenger directives to `.htaccess` blindly. If a local stage fails, investigate
that stage before attributing the problem to hosting capacity.

Separately, extension 1.7.21 reduces repeated cloud work: its 12-second broker
session refresh checks the server's device/license/entitlements through one GET,
without re-registering the device or refetching optional configuration/releases.
Initial startup retains registration and full validation. Revoked devices remain
blocked; server failures are not mislabeled as expired sessions. The health badge
polls at 60 seconds instead of 6, skips hidden windows and prevents overlap. Local
chart/data messages are not hosting requests. These changes reduce known traffic;
they do not establish or guarantee a cure for the production timeout.

## Companion-only extension 1.7.22

The owner subsequently requested removing extension chart displays. The popup now
defaults to a compact broker companion with strategy/stake/expiry controls,
Demo/Real status, Start/Stop, risk settings and trade history. Advanced website
tools open separately. Broker market-data collection, candle validation and
strategy/order calculations remain unchanged; no automatic Start was added.
The retired renderer source/DOM is retained for compatibility and can be restored
from Git, but its views and recurring render/snapshot paths are disabled in the
companion build. A small `GET_COMPANION_STATUS` message supplies account/asset
status every five seconds without serializing chart history. The worker's
attachment readiness probe uses the same minimal receiver. Website chart access
and the server's membership limits remain unchanged.

The website now distinguishes server, network and timeout errors and gives
login/bootstrap requests a 20-second client timeout without retrying passwords.
No authentication bypass, role change, payment activation or live file overwrite
was performed by this investigation. Companion-only extension UI work remains a
separate requested change; preserving broker data/strategy logic is required.
