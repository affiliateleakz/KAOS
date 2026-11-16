"""OAuth exchange fixtures; no real Google accounts or tokens."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi import HTTPException
import routes_extension as routes


def test_public_google_configuration_exposes_only_public_client_and_store_id(monkeypatch):
    monkeypatch.setenv('KAOS_GOOGLE_EXTENSION_CLIENT_ID','fixture-public-client')
    monkeypatch.setenv('SOME_PRIVATE_SECRET','must-never-be-returned')
    assert asyncio.run(routes.extension_google_config())=={
        'configured':True,'client_id':'fixture-public-client','store_item_id':'gbobopmnjgeeegniphckfpalhnebapjm'}
    monkeypatch.delenv('KAOS_GOOGLE_EXTENSION_CLIENT_ID')
    assert asyncio.run(routes.extension_google_config())['configured'] is False


@pytest.mark.parametrize('matching',[True,False])
def test_google_exchange_verifies_client_and_identity_before_issuing_kaos_tokens(monkeypatch,matching):
    monkeypatch.setenv('JWT_SECRET','fixture-google-exchange-test-only-signing-key')
    monkeypatch.setenv('KAOS_GOOGLE_EXTENSION_CLIENT_ID','fixture-client')
    urls=[]
    async def get(self,url,**kwargs):
        urls.append(url)
        body={'aud':'fixture-client' if matching else 'wrong-client'} if url.endswith('tokeninfo') else {
            'sub':'fixture-google-sub','email':'fixture@example.com','email_verified':True}
        return httpx.Response(200,json=body,request=httpx.Request('GET',url))
    monkeypatch.setattr(httpx.AsyncClient,'get',get)
    identity=AsyncMock(return_value={'id':'fixture-user','email':'fixture@example.com'})
    monkeypatch.setattr(routes,'_google_signin_identity',identity)
    request=SimpleNamespace(json=AsyncMock(return_value={'access_token':'fixture-google-token'}))
    if not matching:
        with pytest.raises(HTTPException) as exc:asyncio.run(routes.extension_google_access_token(request))
        assert exc.value.status_code==401 and len(urls)==1
        identity.assert_not_awaited()
    else:
        response=asyncio.run(routes.extension_google_access_token(request))
        assert response['accessToken']!='fixture-google-token' and response['refreshToken']
        assert 'token_version' not in response['user'] and len(urls)==2
        assert identity.call_args.args[0]['email_verified'] is True
