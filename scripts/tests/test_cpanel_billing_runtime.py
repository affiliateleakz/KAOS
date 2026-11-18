"""Only explicit repair overrides stale Passenger flags; never secrets or order gates."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cpanel_activate", ROOT / "cpanel_activate.py"
)
activation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activation)


def fixture_site(tmp_path):
    site = tmp_path / "site"
    backend = site / "backend"
    for name in (
        "apps/api/server.py",
        "apps/api/routes_billing.py",
        "passenger_wsgi.py",
    ):
        path = backend / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# original\n")
    (backend / "packages/kaos-core").mkdir(parents=True)
    (backend / ".env").write_text(
        "JWT_SECRET=private-fixture\nKAOS_LOGIN_VALIDATION_MODE=true\n"
    )
    return site, backend


def load_repair(monkeypatch):
    monkeypatch.setitem(sys.modules, "cpanel_activate", activation)
    spec = importlib.util.spec_from_file_location(
        "repair", ROOT / "cpanel_billing_runtime.py"
    )
    repair = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(repair)
    return repair


@pytest.mark.parametrize("enabled", [True, False])
def test_repair_preserves_credentials_and_requests_worker_restart(
    tmp_path, monkeypatch, enabled
):
    site, backend = fixture_site(tmp_path)
    repair = load_repair(monkeypatch)
    before = (backend / ".env").read_bytes()
    repair.repair(site, enabled)
    assert (backend / ".env").read_bytes() == before
    assert (backend / "apps/api/server.py").read_text() == "# original\n"
    assert (backend / "passenger_wsgi.py").read_text() == activation.WRAPPER
    assert (
        json.loads((backend / repair.POLICY).read_text())["stripeCheckoutEnabled"]
        is enabled
    )
    assert (backend / repair.POLICY).stat().st_mode & 0o777 == 0o600
    assert (backend / "tmp/restart.txt").exists()


@pytest.mark.parametrize("enabled", [True, False])
def test_wrapper_owner_policy_wins_over_stale_environment(
    tmp_path, monkeypatch, enabled
):
    import os
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    site, backend = fixture_site(tmp_path)
    repair = load_repair(monkeypatch)
    repair.repair(site, enabled)
    monkeypatch.setenv("KAOS_STRIPE_CHECKOUT_ENABLED", "false" if enabled else "true")
    monkeypatch.setenv("KAOS_LOGIN_VALIDATION_MODE", "true" if enabled else "false")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "fixture-existing")
    monkeypatch.setenv("KAOS_COINBASE_LIVE_ORDERS", "disabled")
    app = FastAPI()

    @app.post("/api/billing/checkout")
    def checkout():
        return {"fixture": True}

    module = ModuleType("server")
    module.app = app
    monkeypatch.setitem(sys.modules, "server", module)
    monkeypatch.setattr(sys, "path", list(sys.path))
    scope = {"__file__": str(backend / "passenger_wsgi.py")}
    exec(compile(activation.WRAPPER, "passenger_wsgi.py", "exec"), scope)
    scope["_get_app"]()
    assert os.environ["KAOS_STRIPE_CHECKOUT_ENABLED"] == (
        "true" if enabled else "false"
    )
    assert os.environ["KAOS_LOGIN_VALIDATION_MODE"] == ("false" if enabled else "true")
    assert os.environ["KAOS_COINBASE_LIVE_ORDERS"] == "disabled"
    with TestClient(app) as client:
        assert client.post("/api/billing/checkout").status_code == (
            200 if enabled else 503
        )
        assert client.post("/api/trading/execute").status_code == 503
        assert client.post("/api/affiliate/connect/transfer").status_code == 503


def test_symlink_policy_is_rejected(tmp_path, monkeypatch):
    site, backend = fixture_site(tmp_path)
    repair = load_repair(monkeypatch)
    target = tmp_path / "untouched"
    target.write_text("untouched")
    (backend / repair.POLICY).symlink_to(target)
    with pytest.raises(ValueError):
        repair.repair(site, True)
    assert target.read_text() == "untouched"
