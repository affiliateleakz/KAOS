import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

spec = importlib.util.spec_from_file_location('activation', Path(__file__).resolve().parents[1] / 'cpanel_activate.py')
activation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activation)


def inputs(tmp_path):
    site = tmp_path / 'site'
    (site / 'backend').mkdir(parents=True)
    (site / '.htaccess').write_text('original routing')
    (site / 'backend/.env').write_text('private settings')
    (site / 'backend/wsgi_app.py').write_text('legacy application')
    (site / 'uploads').mkdir()
    (site / 'uploads/user-file').write_text('user data')
    web = {'index.html': b'new website', 'static/main.js': b'new script', '.htaccess': b'ignored'}
    backend = {'apps/api/server.py': b'new backend', 'packages/kaos-core/kaos/__init__.py': b'core', 'passenger_wsgi.py': b'ignored'}
    return site, web, backend


def test_installs_both_packages_preserving_settings_and_legacy(tmp_path):
    site, web, backend = inputs(tmp_path)
    activation.install(site, web, backend)
    assert (site / 'index.html').read_bytes() == b'new website'
    assert (site / '.htaccess').read_text() == 'original routing'
    assert (site / 'backend/.env').read_text() == 'private settings'
    assert (site / 'backend/wsgi_app.py').read_text() == 'legacy application'
    assert (site / 'uploads/user-file').read_text() == 'user data'
    assert (site / 'backend/apps/api/server.py').read_bytes() == b'new backend'
    assert (site / 'backend/passenger_wsgi.py').read_text() == activation.WRAPPER
    assert 'Require all denied' in (site / 'backend/.htaccess').read_text()
    assert (site / 'static').stat().st_mode & 0o777 == 0o755
    assert (site / 'static/main.js').stat().st_mode & 0o777 == 0o644


def test_rejects_symlink_before_any_writes(tmp_path):
    site, web, backend = inputs(tmp_path)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (site / 'static').symlink_to(elsewhere)
    with pytest.raises(ValueError):
        activation.install(site, web, backend)
    assert not (site / 'index.html').exists()
    assert not (site / 'backend/.htaccess').exists()
    assert not list(elsewhere.iterdir())


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'foo/../../outside', 'a\\b'])
def test_rejects_unsafe_archive_paths(tmp_path, name):
    with pytest.raises(ValueError):
        activation.safe_destination(tmp_path, name)


def test_validation_wrapper_blocks_orders_and_billing(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    @app.post('/api/v1/auth/login')
    def login():
        return {'ok': True}
    @app.post('/api/v1/devices/register')
    def device():
        return {'ok': True}
    @app.post('/api/v1/intelligence/scan')
    def radar_scan():
        return {'research_only': True}
    @app.put('/api/admin/radar/providers/{provider}')
    def radar_provider(provider: str):
        return {'provider': provider}
    @app.post('/api/admin/radar/vault/initialize')
    def radar_vault():
        return {'vaultReady': True}
    @app.post('/api/v1/intelligence/sync-news')
    def sync_news():
        return {'ok': True}
    @app.post('/api/affiliate/activate')
    def affiliate_enrollment():
        return {'ok': True}
    @app.post('/api/affiliate/connect/onboarding')
    def connect_onboarding():
        return {'ok': True}
    @app.put('/api/admin/commerce/providers/{provider}')
    def commerce_preferences(provider: str):
        return {'provider': provider}
    @app.post('/api/admin/commerce/providers/{provider}/test')
    def commerce_connection_check(provider: str):
        return {'provider': provider}
    @app.post('/api/admin/commerce/vault/initialize')
    def commerce_vault():
        return {'vaultReady': True}
    @app.delete('/api/v1/devices/device-1')
    def revoke_member_device():
        return {'revoked': True}
    @app.post('/api/admin/devices/device-1/revoke')
    def revoke_admin_device():
        return {'revoked': True}
    @app.post('/api/admin/users/user-1/revoke-all-devices')
    def revoke_all():
        pytest.fail('Mass account changes must remain blocked')
    @app.post('/api/trading/execute')
    def order():
        pytest.fail('Trading handler must never be called')
    @app.get('/api/billing/status')
    def billing():
        pytest.fail('Billing handler must never be called')
    @app.get('/api/billing/plans')
    def plans():
        return []
    @app.get('/api/billing/memberships')
    def memberships():
        return {'plans': []}
    @app.get('/api')
    def health():
        return {'ok': True}
    server = ModuleType('server')
    server.app = app
    monkeypatch.setitem(sys.modules, 'server', server)
    monkeypatch.setattr(sys, 'path', list(sys.path))
    monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS', 'enabled')
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'test-value')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'test-value')
    scope = {'__file__': str(tmp_path / 'passenger_wsgi.py')}
    exec(compile(activation.WRAPPER, 'passenger_wsgi.py', 'exec'), scope)
    scope['_get_app']()
    import os
    assert os.environ['KAOS_COINBASE_LIVE_ORDERS'] == 'disabled'
    assert os.environ['STRIPE_SECRET_KEY'] == ''
    client = TestClient(app)
    assert client.get('/api').status_code == 200
    assert client.post('/api/v1/auth/login').status_code == 200
    assert client.post('/api/v1/devices/register').status_code == 200
    assert client.post('/api/v1/intelligence/scan').status_code == 200
    assert client.put('/api/admin/radar/providers/reddit').status_code == 200
    assert client.put('/api/admin/radar/providers/unknown').status_code == 503
    assert client.post('/api/admin/radar/vault/initialize').status_code == 200
    assert client.post('/api/v1/intelligence/sync-news').status_code == 200
    assert client.post('/api/v1/intelligence/ingest').status_code == 503
    assert client.post('/api/affiliate/activate').status_code == 200
    assert client.post('/api/affiliate/connect/onboarding').status_code == 200
    assert client.post('/api/affiliate/connect/transfer').status_code == 503
    for provider in ('stripe', 'paypal', 'nowpayments'):
        assert client.put('/api/admin/commerce/providers/' + provider).status_code == 200
        assert client.post('/api/admin/commerce/providers/' + provider + '/test').status_code == 200
    assert client.post('/api/admin/commerce/vault/initialize').status_code == 200
    assert client.post('/api/admin/commerce/providers/paypal/transfer').status_code == 503
    assert client.put('/api/admin/commerce/providers/unknown').status_code == 503
    assert client.delete('/api/v1/devices/device-1').status_code == 200
    assert client.post('/api/admin/devices/device-1/revoke').status_code == 200
    assert client.post('/api/admin/users/user-1/revoke-all-devices').status_code == 503
    assert client.delete('/api/v1/devices/device-1/extra').status_code == 503
    assert client.post('/api/trading/execute').status_code == 503
    assert client.get('/api/billing/status').status_code == 503
    assert client.get('/api/billing/plans').status_code == 200
    assert client.get('/api/billing/memberships').status_code == 200
    assert client.post('/api/billing/memberships').status_code == 503
    assert client.post('/api/billing/plans').status_code == 503


def test_wsgi_adapter_survives_preloaded_parent_fork(tmp_path):
    """A worker must never wait on an event-loop thread inherited from its parent."""
    import subprocess
    script = tmp_path / 'fork_check.py'
    wrapper = tmp_path / 'wrapper.txt'
    wrapper.write_text(activation.WRAPPER)
    script.write_text('''import os, signal, sys
from pathlib import Path
from types import ModuleType
from wsgiref.util import setup_testing_defaults
from fastapi import FastAPI
server = ModuleType("server")
server.app = FastAPI()
@server.app.get("/api")
def health():
    return {"status": "ok"}
sys.modules["server"] = server
scope = {"__file__": str(Path(sys.argv[1]).parent / "passenger_wsgi.py")}
exec(Path(sys.argv[1]).read_text(), scope)
def request():
    env = {}
    setup_testing_defaults(env)
    env["PATH_INFO"] = "/api"
    status = []
    body = b"".join(scope["application"](env, lambda s, h, exc_info=None: status.append(s)))
    assert status == ["200 OK"], status
    assert b'"status":"ok"' in body, body
request()
pid = os.fork()
if pid == 0:
    signal.alarm(5)
    request()
    os._exit(0)
_, status = os.waitpid(pid, 0)
assert os.waitstatus_to_exitcode(status) == 0, status
''')
    result = subprocess.run([sys.executable, str(script), str(wrapper)], capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr.decode()
    # Simulate a native fork without Python callbacks while the parent owns the
    # adapter lock. The PID check must run before acquiring that inherited lock.
    callback_free = activation.WRAPPER.replace('if hasattr(os, "register_at_fork"):', 'if False:')
    wrapper.write_text(callback_free)
    script.write_text(script.read_text().replace('pid = os.fork()', 'scope["_adapter_lock"].acquire()\npid = os.fork()'))
    fixed = subprocess.run([sys.executable, str(script), str(wrapper)], capture_output=True, timeout=15)
    assert fixed.returncode == 0, fixed.stderr.decode()
    unsafe = callback_free.replace('    if _process_pid != pid:\n        _after_fork()\n', '')
    wrapper.write_text(unsafe)
    old = subprocess.run([sys.executable, str(script), str(wrapper)], capture_output=True, timeout=15)
    assert old.returncode != 0, 'Regression fixture must reproduce the inherited-lock hang'
