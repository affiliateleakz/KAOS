"""Extension license checks must reject revoked or unknown installation IDs."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_extension as ext

@pytest.mark.parametrize("device,expected", [
    (None,"not registered"),
    ({"id":"dev1","userId":"u1","revoked":True},"revoked"),
])
def test_license_refuses_untrusted_device(monkeypatch,device,expected):
    devices=SimpleNamespace(find_one=AsyncMock(return_value=device),update_one=AsyncMock())
    monkeypatch.setattr(ext,"db",SimpleNamespace(devices=devices))
    request=SimpleNamespace(headers={"X-Device-Id":"install1"},
                            client=SimpleNamespace(host="127.0.0.1"))
    with pytest.raises(HTTPException,match=expected) as err:
        asyncio.run(ext.v1_license(request,user={"id":"u1"}))
    assert err.value.status_code==403
    devices.update_one.assert_not_awaited()
