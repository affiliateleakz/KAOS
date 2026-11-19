"""Document the remaining session-binding release blocker, not a passing claim."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import auth
import routes_extension as ext


@pytest.mark.xfail(strict=True, reason='AUDIT-AUTH-1: refresh JWTs are not bound to a revocable installation/session')
def test_revoked_installation_cannot_refresh_its_previous_token(monkeypatch):
    monkeypatch.setenv('JWT_SECRET', 'x' * 40)
    user = {'id': 'u1', 'email': 'member@example.com', 'token_version': 7}
    monkeypatch.setattr(ext, 'db', SimpleNamespace(
        users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
        devices=SimpleNamespace(find_one=AsyncMock(return_value={'installId': 'old', 'revoked': True}))))
    token = auth.create_refresh_token('u1', 7)
    request = SimpleNamespace(json=AsyncMock(return_value={'refreshToken': token}), headers={'X-Device-Id': 'old'})
    with pytest.raises(HTTPException) as error:
        asyncio.run(ext.v1_refresh(request))
    assert error.value.status_code in (401, 403)
