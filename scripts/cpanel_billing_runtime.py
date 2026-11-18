"""Repair the deployed Passenger billing flags without copying website/API source or secrets."""

import argparse
import json
from pathlib import Path
from cpanel_activate import WRAPPER, write_file

POLICY = ".kaos-billing-runtime.json"


def repair(site: Path, enabled: bool):
    """Explicit owner action. The local policy survives stale inherited Passenger flags."""
    backend = site / "backend"
    targets = [
        backend,
        backend / POLICY,
        backend / "passenger_wsgi.py",
        backend / "tmp",
        backend / "tmp/restart.txt",
    ]
    if site.is_symlink() or any(path.is_symlink() for path in targets):
        raise ValueError("Refusing symlink application/configuration paths")
    for relative in (
        "apps/api/server.py",
        "apps/api/routes_billing.py",
        "packages/kaos-core",
        "passenger_wsgi.py",
    ):
        if not (backend / relative).exists():
            raise ValueError(
                "Deployed repository-shaped backend is missing: " + relative
            )
    compile(WRAPPER, str(backend / "passenger_wsgi.py"), "exec")
    policy = (
        json.dumps({"version": 1, "stripeCheckoutEnabled": enabled}, indent=2).encode()
        + b"\n"
    )
    updates = [
        (backend / "passenger_wsgi.py", WRAPPER.encode()),
        (backend / POLICY, policy),
    ]
    previous = [
        (
            path,
            path.read_bytes() if path.exists() else None,
            path.stat().st_mode & 0o777 if path.exists() else 0o600,
        )
        for path, _ in updates
    ]
    try:
        for path, data in updates:
            write_file(path, data, 0o600)
        restart = backend / "tmp/restart.txt"
        restart.parent.mkdir(mode=0o700, exist_ok=True)
        restart.touch(mode=0o600)
    except Exception:
        for path, data, mode in reversed(previous):
            if data is None:
                path.unlink(missing_ok=True)
            else:
                write_file(path, data, mode)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--enable-stripe", action="store_true")
    action.add_argument("--disable-stripe", action="store_true")
    args = parser.parse_args()
    repair(Path.home() / "tradingwithkaos.com", args.enable_stripe)
    print(
        "Installed current Passenger wrapper and saved explicit billing runtime policy."
    )
    print(
        "Stripe checkout requested: "
        + ("enabled" if args.enable_stripe else "disabled")
    )
    print(
        "Passenger restart requested. If the host ignores restart.txt, restart the Python app in cPanel."
    )
    print(
        "No API/website source, credentials, database records or trading settings were changed."
    )
    print(
        "Check https://api.tradingwithkaos.com/api/billing/availability after restart."
    )


if __name__ == "__main__":
    main()
