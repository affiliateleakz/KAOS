"""Source FastAPI parity; not evidence about unavailable legacy WSGI source."""
import asyncio
from http.cookies import SimpleCookie
from types import SimpleNamespace
from unittest.mock import AsyncMock
import jwt
from fastapi import Response
import auth
import routes_auth
import routes_extension
from models import LoginReq


def test_web_and_extension_share_account_hash_and_token_version(monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'isolated-parity-test-secret-at-least-32-bytes')
    user = {'id': 'u1', 'email': 'member@example.com', 'token_version': 7,
            'password_hash': auth.hash_password('test-password')}
    database = SimpleNamespace(
        users=SimpleNamespace(find_one=AsyncMock(side_effect=lambda *a, **kw: dict(user))),
        login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None), delete_many=AsyncMock()))
    for module in (auth, routes_auth, routes_extension):
        monkeypatch.setattr(module, 'db', database)
    request = SimpleNamespace(client=SimpleNamespace(host='127.0.0.1'))
    req = LoginReq(email='MEMBER@example.com', password='test-password')
    response = Response()
    asyncio.run(routes_auth.login(req, request, response))
    extension = asyncio.run(routes_extension.v1_login(req, request))
    cookies = SimpleCookie()
    for value in response.headers.getlist('set-cookie'):
        cookies.load(value)
    def payload(token):
        result = jwt.decode(token, 'isolated-parity-test-secret-at-least-32-bytes', algorithms=['HS256'])
        assert result.pop('exp') > 0
        return result
    assert payload(cookies['access_token'].value) == payload(extension['accessToken'])
    assert payload(cookies['refresh_token'].value) == payload(extension['refreshToken'])
    assert asyncio.run(auth._user_from_token(extension['accessToken']))['id'] == 'u1'
    refresh_request = SimpleNamespace(json=AsyncMock(return_value={'refreshToken': extension['refreshToken']}))
    refreshed = asyncio.run(routes_extension.v1_refresh(refresh_request))
    assert payload(refreshed['accessToken'])['ver'] == 7
    assert 'password_hash' not in extension['user']
