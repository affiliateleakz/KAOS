import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('google_readiness',Path(__file__).resolve().parents[1]/'check_extension_google_login.py')
readiness=importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


def test_matching_config_does_not_claim_a_real_google_signin(monkeypatch):
    import json
    manifest=json.loads((readiness.ROOT/'apps/extension/manifest.json').read_text())
    def document(url):
        return {'status':'ok'} if url.endswith('/api') else {'configured':True,'client_id':manifest['oauth2']['client_id'],'store_item_id':readiness.STORE_ID}
    monkeypatch.setattr(readiness,'document',document)
    report=readiness.check('https://api.example.com')
    assert report['state']=='configuration_checks_passed' and report['google_sign_in_verified'] is False


def test_missing_configuration_blocks_readiness(monkeypatch):
    monkeypatch.setattr(readiness,'document',lambda url:{'status':'ok'} if url.endswith('/api') else {'configured':False})
    with pytest.raises(ValueError,match='missing'):readiness.check('https://api.example.com')


def test_http_200_challenge_is_not_a_passing_health_check(monkeypatch):
    class Response:
        status=200
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return b'<title>Bot Verification</title><form id="lsrecaptcha-form">'
    monkeypatch.setattr(readiness,'urlopen',lambda *args,**kwargs:Response())
    with pytest.raises(ValueError,match='bot-verification'):readiness.document('https://api.example.com/api')
