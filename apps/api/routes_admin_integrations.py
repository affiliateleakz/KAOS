"""Admin API-key management: one place to see what each integration is for,
where to get it, and to store the credential so member features work.

Secrets are write-only from the client's point of view: the API returns status
and a masked hint, never the stored value.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

import integration_config
from auth import require_role
from services import audit_log

router = APIRouter(prefix="/api/admin/integrations", tags=["admin-integrations"])
admin_dep = require_role("admin")


class ValuesIn(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


@router.get("")
async def list_integrations(admin: dict = Depends(admin_dep)):
    return await integration_config.catalog()


@router.put("/{provider}")
async def save_integration(provider: str, body: ValuesIn, admin: dict = Depends(admin_dep)):
    entry = await integration_config.save(provider, body.values, admin)
    await audit_log(admin, "integration_key_saved", "integration", provider)
    return entry


@router.delete("/{provider}")
async def delete_integration(provider: str, admin: dict = Depends(admin_dep)):
    result = await integration_config.remove(provider, admin)
    await audit_log(admin, "integration_key_removed", "integration", provider)
    return result


@router.post("/{provider}/test")
async def test_integration(provider: str, admin: dict = Depends(admin_dep)):
    if provider not in integration_config.BY_ID:
        raise HTTPException(404, "Unknown integration")
    return await integration_config.probe(provider)
