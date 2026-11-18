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
    @app.post('/api/community/posts')
    @app.put('/api/community/posts/post_1/like')
    @app.patch('/api/community/posts/post_1')
    @app.delete('/api/community/posts/post_1')
    @app.post('/api/community/posts/post_1/comments')
    @app.post('/api/community/posts/post_1/report')
    @app.post('/api/users/bob/follow')
    @app.delete('/api/users/bob/follow')
    @app.post('/api/admin/reports/report_1/action')
    def community():
        return {'community':True,'execution_enabled':False}
    @app.post('/api/v1/ai/learning-samples')
    @app.post('/api/v1/trading/events')
    @app.post('/api/v1/ai/training/train')
    @app.post('/api/admin/ai/continuous/owner/train')
    @app.post('/api/admin/radar/offerings')
    @app.post('/api/v1/devices/register')
    def device():
        return {'ok': True}
    @app.post('/api/v1/intelligence/scan')
    def radar_scan():
        return {'research_only': True}
    @app.post('/api/v1/intelligence/research/asset')
    def asset_research():
        return {'execution_enabled':False}
    @app.post('/api/v1/intelligence/signals/opportunities')
    def opportunity_scan():
        return {'plays':[],'execution_enabled':False}
    @app.post('/api/v1/intelligence/news/feed')
    def news_feed():
        return {'articles':[]}
    @app.post('/api/v1/intelligence/social/mentions')
    def social_mentions():
        return {'execution_enabled':False}
    @app.post('/api/admin/radar/model/train')
    @app.post('/api/admin/radar/model/activate')
    def local_model():
        return {'execution_enabled':False}
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
    @app.put('/api/v1/broker-selection')
    @app.put('/api/v1/broker-connections/coinbase')
    @app.delete('/api/v1/broker-connections/coinbase')
    def broker_setup():
        return {'live_order_authorized': False}
    @app.delete('/api/v1/devices/device-1')
    def revoke_member_device():
        return {'revoked': True}
    @app.post('/api/admin/devices/device-1/revoke')
    def revoke_admin_device():
        return {'revoked': True}
    @app.post('/api/admin/users/user-1/revoke-all-devices')
    def revoke_all():
        pytest.fail('Mass account changes must remain blocked')
    from fastapi import Request, HTTPException
    @app.post('/api/admin/settings')
    async def membership_settings(request: Request):
        if request.headers.get('x-test-admin') != 'yes':
            raise HTTPException(status_code=403, detail='Admin required')
        payload = await request.json()
        assert payload['key'] == 'plans'
        return payload
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
    monkeypatch.delenv('KAOS_COINBASE_LIVE_ORDERS', raising=False)
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
    for path in ('/api/v1/broker-selection','/api/v1/broker-connections/coinbase'):
        assert client.put(path).json()=={'live_order_authorized': False}
    assert client.delete('/api/v1/broker-connections/coinbase').status_code==200
    assert client.put('/api/v1/broker-connections/unknown').status_code==503
    assert client.post('/api/v1/coinbase-live/orders').status_code==503
    assert client.delete('/api/v1/broker-selection').status_code==503
    assert client.post('/api/v1/auth/login').status_code == 200
    for path in ('/api/v1/ai/learning-samples','/api/v1/trading/events','/api/v1/ai/training/train','/api/admin/ai/continuous/owner/train','/api/admin/radar/offerings'):
        assert client.post(path).status_code == 200
    assert client.post('/api/v1/devices/register').status_code == 200
    assert client.post('/api/community/posts').status_code == 200
    assert client.put('/api/community/posts/post_1/like').status_code == 200
    assert client.patch('/api/community/posts/post_1').status_code == 200
    assert client.delete('/api/community/posts/post_1').status_code == 200
    assert client.post('/api/community/posts/post_1/comments').status_code == 200
    assert client.post('/api/community/posts/post_1/report').status_code == 200
    assert client.post('/api/users/bob/follow').status_code == 200
    assert client.delete('/api/users/bob/follow').status_code == 200
    assert client.post('/api/admin/reports/report_1/action').status_code == 200
    assert client.post('/api/v1/intelligence/scan').status_code == 200
    assert client.post('/api/v1/intelligence/research/asset').status_code == 200
    assert client.post('/api/v1/intelligence/signals/opportunities').status_code == 200
    assert client.put('/api/admin/radar/providers/options_data').status_code == 200
    assert client.post('/api/v1/intelligence/news/feed').status_code == 200
    assert client.put('/api/admin/radar/providers/alphavantage').status_code == 200
    assert client.post('/api/v1/intelligence/social/mentions').status_code == 200
    assert client.post('/api/admin/radar/model/train').status_code == 200
    assert client.post('/api/admin/radar/model/activate').status_code == 200
    assert client.put('/api/admin/radar/providers/openai').status_code == 503
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
    plan_payload = {'key': 'plans', 'value': {'value': [{'id': 'pro', 'amount': 4900}]}}
    assert client.post('/api/admin/settings', json=plan_payload).status_code == 403
    saved = client.post('/api/admin/settings', json=plan_payload, headers={'x-test-admin': 'yes'})
    assert saved.status_code == 200
    assert saved.json() == plan_payload  # Middleware must preserve the request body for the handler.
    assert client.post('/api/admin/settings', json={'key': 'ai_execution_validated', 'value': True}, headers={'x-test-admin': 'yes'}).status_code == 503
    assert client.post('/api/admin/settings', content='not JSON', headers={'content-type': 'application/json'}).status_code == 503
    assert client.post('/api/admin/settings', json=[]).status_code == 503
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


def test_full_install_records_verified_revision_only_after_files_install(tmp_path):
    import json
    site,web,backend=inputs(tmp_path)
    activation.install(site,web,backend,'a'*40)
    marker=site/'backend/apps/api/deployed_release.json'
    assert json.loads(marker.read_text())['revision']=='a'*40
    assert marker.stat().st_mode & 0o777==0o600
    with pytest.raises(ValueError):activation.install(site,web,backend,'invalid')
    assert json.loads(marker.read_text())['revision']=='a'*40


@pytest.mark.parametrize('enabled',[False,True])
def test_coinbase_live_enablement_is_explicit_and_does_not_enable_other_trading(tmp_path,monkeypatch,enabled):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import ModuleType
    import sys
    app=FastAPI()
    for path in ('/api/v1/coinbase-bot/start','/api/v1/coinbase-bot/stop','/api/v1/coinbase-live/orders','/api/v1/coinbase-live/reconcile'):
        app.add_api_route(path,lambda:{'fixture_only':True},methods=['POST'])
    server=ModuleType('server');server.app=app
    monkeypatch.setitem(sys.modules,'server',server)
    if enabled:monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
    else:monkeypatch.delenv('KAOS_COINBASE_LIVE_ORDERS',raising=False)
    scope={'__file__':str(tmp_path/'passenger_wsgi.py')}
    exec(compile(activation.WRAPPER,'passenger_wsgi.py','exec'),scope)
    scope['_get_app']()
    with TestClient(app) as client:
        assert client.post('/api/v1/coinbase-bot/stop').status_code==200
        for path in ('/api/v1/coinbase-bot/start','/api/v1/coinbase-live/orders','/api/v1/coinbase-live/reconcile'):
            assert client.post(path).status_code==(200 if enabled else 503)
        assert client.post('/api/trading/execute').status_code==503
        assert client.post('/api/billing/checkout').status_code==503
        assert client.post('/api/v1/coinbase-live/arbitrary').status_code==503


@pytest.mark.parametrize('enabled,validation',[(False,False),(True,False),(True,True)])
def test_explicit_stripe_checkout_flag_reaches_only_billing_handlers(tmp_path,monkeypatch,enabled,validation):
    from fastapi import FastAPI,Request,HTTPException
    from fastapi.testclient import TestClient
    from types import ModuleType
    import os,sys
    app=FastAPI()
    for path in ('/api/billing/guest-intent','/api/billing/guest-checkout','/api/billing/checkout','/api/billing/portal','/api/billing/cancel'):
        app.add_api_route(path,lambda:{'fixture_only':True},methods=['POST'])
    @app.get('/api/billing/status/{session_id}')
    def owned_status(session_id:str):return {'state':'pending'}
    @app.get('/api/billing/guest-status/{session_id}')
    @app.post('/api/billing/guest-cancel/{session_id}')
    @app.post('/api/billing/guest-resend/{session_id}')
    def private_receipt(session_id:str):raise HTTPException(403,'Receipt cookie required')
    @app.post('/api/stripe/webhook')
    def webhook(request:Request):
        if request.headers.get('Stripe-Signature')!='fixture-signed':raise HTTPException(400,'Signature required')
        return {'fixture_only':True}
    module=ModuleType('server');module.app=app;monkeypatch.setitem(sys.modules,'server',module)
    monkeypatch.setenv('KAOS_STRIPE_CHECKOUT_ENABLED','true' if enabled else 'false')
    monkeypatch.delenv('KAOS_LOGIN_VALIDATION_MODE',raising=False)
    if validation:monkeypatch.setenv('KAOS_LOGIN_VALIDATION_MODE','true')
    monkeypatch.setenv('STRIPE_SECRET_KEY','sk_test_fixture')
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET','whsec_fixture')
    scope={'__file__':str(tmp_path/'passenger_wsgi.py')}
    exec(compile(activation.WRAPPER,'passenger_wsgi.py','exec'),scope);scope['_get_app']()
    expected=200 if enabled and not validation else 503
    with TestClient(app) as client:
        for path in ('/api/billing/guest-intent','/api/billing/guest-checkout','/api/billing/checkout','/api/billing/portal','/api/billing/cancel'):
            assert client.post(path).status_code==expected
        assert client.get('/api/billing/status/cs_fixture').status_code==expected
        assert client.get('/api/billing/guest-status/cs_fixture').status_code==403
        assert client.post('/api/billing/guest-resend/cs_fixture').status_code==403
        assert client.post('/api/billing/guest-cancel/cs_fixture').status_code==403
        assert client.post('/api/stripe/webhook').status_code==(400 if expected==200 else 503)
        assert client.post('/api/stripe/webhook',headers={'Stripe-Signature':'fixture-signed'}).status_code==expected
        assert client.post('/api/trading/execute').status_code==503
        assert client.post('/api/affiliate/connect/transfer').status_code==503
        assert client.post('/api/billing/anything-else').status_code==503
    assert os.environ['STRIPE_SECRET_KEY']==('sk_test_fixture' if enabled else '')
