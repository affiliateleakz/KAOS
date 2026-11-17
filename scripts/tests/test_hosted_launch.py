import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('hosted_launch', Path(__file__).resolve().parents[1] / 'check_hosted_launch.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def catalog():
    return {'plans': [{'id': key, 'amount': amount, 'interval': interval, 'currency': 'usd',
                       'entitlements': {'chartLimit': charts, 'deviceLimit': devices}}
                      for key, (amount, interval, charts, devices) in check.EXPECTED.items()]}


def test_stale_saved_catalog_is_blocked():
    assert check.catalog_issues(catalog()) == []
    value = catalog()
    value['plans'][1]['amount'] = 2900
    value['plans'][2]['id'] = 'yearly'
    value['plans'][3]['entitlements'].pop('chartLimit')
    assert set(check.catalog_issues(value)) == {'pro:price_or_interval', 'pro_yearly:missing_or_duplicate',
                                             'ultimate:chart_or_device_limit', 'unexpected_plan_ids'}


def test_different_client_challenge_blocks_even_when_other_requests_pass(monkeypatch):
    manifest = json.loads((check.Path(check.__file__).resolve().parents[1] / 'apps/extension/manifest.json').read_text())
    def fetch(url, agent, website, timeout):
        if agent == check.PROFILES['store'] and url.endswith('/api'):
            return {'error': 'bot_verification'}, None
        data = ({'status': 'ok', 'service': 'KAOS Trading API'} if url.endswith('/api') else
                catalog() if url.endswith('/memberships') else
                {'configured': True, 'store_item_id': check.STORE_ID, 'client_id': manifest['oauth2']['client_id']})
        return {'status': 200, 'corsMatchesWebsite': True}, data
    monkeypatch.setattr(check, 'fetch', fetch)
    report = check.check('https://api.example.com', 'https://example.com')
    assert len(report['checks']) == 6
    assert sum(r['passed'] for r in report['checks']) == 5
    assert report['state'] == 'blocked'
    assert report['launchCertified'] is False and report['changesMade'] is False


@pytest.mark.parametrize('body,kind,error', [(b'<title>Bot Verification</title>', 'text/html', 'bot_verification'),
    (b'private backend traceback', 'text/html', 'non_json_response'),
    (b'not json', 'application/json', 'invalid_json'), (b'x' * 131073, 'application/json', 'response_too_large')])
def test_response_contents_are_never_reported(monkeypatch, body, kind, error):
    class Response:
        status = 200
        headers = {'Content-Type': kind}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return body[:limit]
    class Opener:
        def open(self, request, timeout):
            assert request.get_method() == 'GET'
            return Response()
    monkeypatch.setattr(check, 'build_opener', lambda *args: Opener())
    result, value = check.fetch('https://api.example.com/api', 'check', 'https://example.com', 10)
    assert result['error'] == error and value is None
    assert 'private' not in json.dumps(result)


@pytest.mark.parametrize('value', ['http://example.com', 'https://user:secret@example.com',
                                  'https://example.com/path', 'https://example.com?secret=x'])
def test_origin_rejects_secrets_and_paths(value):
    with pytest.raises(check.argparse.ArgumentTypeError): check.origin(value)


def test_passing_public_checks_still_do_not_certify_payments(monkeypatch):
    manifest = json.loads((check.Path(check.__file__).resolve().parents[1] / 'apps/extension/manifest.json').read_text())
    def fetch(url, *args):
        value = ({'service': 'KAOS Trading API', 'status': 'ok'} if url.endswith('/api') else
                 {**catalog(), 'checkoutEnabled': False, 'mode': 'live'} if url.endswith('/memberships') else
                 {'configured': True, 'store_item_id': check.STORE_ID, 'client_id': manifest['oauth2']['client_id']})
        return {'status': 200, 'corsMatchesWebsite': True}, value
    monkeypatch.setattr(check, 'fetch', fetch)
    report = check.check('https://api.example.com', 'https://example.com')
    assert report['state'] == 'public_checks_passed'
    assert report['launchCertified'] is False
    assert all(r['checkoutEnabled'] is False for r in report['checks'] if r['path'].endswith('/memberships'))


def test_json_without_website_cors_is_not_browser_ready(monkeypatch):
    monkeypatch.setattr(check, 'fetch', lambda *args: ({'status': 200, 'corsMatchesWebsite': False},
                                                    {'service': 'KAOS Trading API', 'status': 'ok'}))
    report = check.check('https://api.example.com', 'https://example.com')
    assert report['state'] == 'blocked'
    assert report['checks'][0]['payloadMatches'] is True
    assert report['checks'][0]['passed'] is False
