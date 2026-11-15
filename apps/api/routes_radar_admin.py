from typing import Annotated
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,SecretStr,ConfigDict
from auth import require_role
from db import db,now_iso
from services import audit_log
import radar_settings as settings

router=APIRouter(prefix='/api/admin/radar',tags=['radar-settings'])
owner=require_role('super_admin')
class ProviderInput(BaseModel):
 model_config=ConfigDict(extra='forbid')
 enabled:bool=True
 credentials:dict[str,SecretStr]=Field(default_factory=dict,max_length=6)
 model:Annotated[str,Field(pattern=r'^[A-Za-z0-9._:-]{1,80}$')]='gpt-4.1-mini'

@router.get('/providers')
async def providers(admin=Depends(owner)):
 return {'vaultReady':settings.vault_ready(),'providers':[await settings.public_settings(p) for p in settings.CATALOG]}

@router.post('/vault/initialize')
async def initialize(admin=Depends(owner)):
 settings.initialize_vault();await audit_log(admin,'radar_vault_initialized','radar')
 return {'vaultReady':True}

@router.put('/providers/{provider}')
async def save(provider:str,request:ProviderInput,admin=Depends(owner)):
 info=settings.CATALOG.get(provider)
 if not info:raise HTTPException(404,'Unknown research provider')
 if set(request.credentials)-set(info['fields']):raise HTTPException(400,'Unknown credential field')
 update={'enabled':request.enabled,'updatedAt':now_iso(),'updatedBy':admin['id']}
 if provider=='openai':update['model']=request.model
 changed=[]
 for name,secret in request.credentials.items():
  value=secret.get_secret_value().strip()
  if not value:continue
  if len(value)>8192:raise HTTPException(400,'Credential too long')
  update['encrypted.'+name]=settings.cipher().encrypt(value.encode()).decode();changed.append(name)
 await db.radar_provider_settings.update_one({'_id':provider},{'$set':update},upsert=True)
 await audit_log(admin,'radar_provider_saved','radar_provider',provider,{'credentialFieldsChanged':changed,'enabled':request.enabled})
 return await settings.public_settings(provider)
