"""Member Pine source library with owner editing and admin moderation. Never executes Pine."""
import asyncio
import base64
import binascii
from io import BytesIO
import json
import re
import warnings
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from PIL import Image, ImageOps
from db import db, now_iso
from auth import get_current_user, require_role

router = APIRouter(tags=['TradingView Pine Scripts'])
admin_user = require_role('admin')
MAX_SOURCE = 128 * 1024
STATES = ('draft','pending','published','rejected','archived')


def administrator(user):return user.get('role') in ('admin','super_admin')


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1,max_length=100)
    description: str = Field(min_length=1,max_length=5000)
    source: str = Field(min_length=1,max_length=MAX_SOURCE)
    kind: str = 'indicator'
    market: str = Field(default='Any',max_length=60)
    timeframe: str = Field(default='Any',max_length=60)
    thumbnail: str = Field(default='',max_length=3_000_000)
    revision: str = Field(default='',max_length=64)
    status: str = 'pending'
    official: bool = False
    featured: bool = False
    moderation_note: str = Field(default='',max_length=1000)
    rights_confirmed: bool = False

    @field_validator('title','description','market','timeframe')
    @classmethod
    def text(cls,value):
        value=value.strip()
        if not value:raise ValueError('Text cannot be blank')
        return value

    @field_validator('source')
    @classmethod
    def pine(cls,value):
        if '\x00' in value or len(value.encode('utf-8'))>MAX_SOURCE:
            raise ValueError('Pine source must be plain text, at most 128 KiB')
        if not re.search(r'^\s*//\s*@version=[3-6]\s*$',value,re.M):
            raise ValueError('Include a Pine //@version=3, 4, 5 or 6 declaration')
        return value.replace('\r\n','\n')

    @field_validator('kind')
    @classmethod
    def script_kind(cls,value):
        if value not in ('indicator','strategy','library'):raise ValueError('Invalid script type')
        return value

    @field_validator('status')
    @classmethod
    def state(cls,value):
        if value not in STATES:raise ValueError('Invalid publication state')
        return value


def thumbnail(value):
    match=re.fullmatch(r'data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=\r\n]+)',value)
    if not match:raise HTTPException(422,'Upload a PNG, JPEG or WebP thumbnail')
    try:
        raw=base64.b64decode(match[2],validate=True)
        if len(raw)>2*1024*1024:raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if image.format not in ('PNG','JPEG','WEBP') or image.width*image.height>16_000_000 or getattr(image,'n_frames',1)!=1:
                    raise ValueError()
                image=ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((640,360))
                result=BytesIO();image.save(result,format='JPEG',quality=80)
        if len(result.getvalue())>200_000:raise ValueError()
        return 'data:image/jpeg;base64,'+base64.b64encode(result.getvalue()).decode()
    except (ValueError,binascii.Error,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise HTTPException(422,'Thumbnail must be a valid still image up to 2 MiB and 16 megapixels') from None


async def payload(request):
    body=bytearray()
    async for part in request.stream():
        body.extend(part)
        if len(body)>3_300_000:raise HTTPException(413,'Script upload is too large')
    try:return Submission.model_validate(json.loads(body))
    except (ValueError,UnicodeError,ValidationError):
        raise HTTPException(422,'Check required title/description, script type, publication status and Pine version. Source limit is 128 KiB.') from None


def visible(row,user):
    return row.get('status')=='published' or row.get('author_id')==user['id'] or administrator(user)


def public(row,user,source=False):
    fields=('id','title','description','kind','market','timeframe','thumbnail','author_id','author_name',
            'status','official','featured','created_at','updated_at','revision')
    result={k:row.get(k) for k in fields}
    result['can_edit']=row['author_id']==user['id'] or administrator(user)
    if result['can_edit']:result['moderation_note']=row.get('moderation_note','')
    if source:result['source']=row['source']
    return result


async def list_rows(user,search,kind,scope,status,page,admin=False):
    query={}
    if scope=='mine':query['author_id']=user['id']
    elif not admin:query['status']='published'
    if status:
        if status not in STATES:raise HTTPException(422,'Invalid status filter')
        if admin or scope=='mine':query['status']=status
    if kind:
        if kind not in ('indicator','strategy','library'):raise HTTPException(422,'Invalid script type')
        query['kind']=kind
    if search.strip():
        pattern={'$regex':re.escape(search.strip()),'$options':'i'}
        query['$or']=[{'title':pattern},{'description':pattern},{'author_name':pattern}]
    count=await db.pine_scripts.count_documents(query)
    rows=await db.pine_scripts.find(query,{'source':0,'trail':0}).sort([('featured',-1),('updated_at',-1),('_id',1)]).skip((page-1)*12).limit(12).to_list(12)
    return {'items':[public(row,user) for row in rows],'total':count,'page':page,'pageSize':12}


@router.get('/api/pine-scripts')
async def listing(response:Response,search:str=Query('',max_length=100),kind:str='',scope:str='library',status:str='',page:int=Query(1,ge=1,le=10000),user:dict=Depends(get_current_user)):
    response.headers['Cache-Control']='private, no-store'
    if scope not in ('library','mine'):raise HTTPException(422,'Invalid library scope')
    return await list_rows(user,search,kind,scope,status,page)


@router.get('/api/admin/pine-scripts')
async def admin_listing(response:Response,search:str=Query('',max_length=100),kind:str='',status:str='',page:int=Query(1,ge=1,le=10000),user:dict=Depends(admin_user)):
    response.headers['Cache-Control']='private, no-store'
    return await list_rows(user,search,kind,'all',status,page,admin=True)


@router.get('/api/pine-scripts/{sid}')
async def detail(sid:str,response:Response,user:dict=Depends(get_current_user)):
    response.headers['Cache-Control']='private, no-store'
    row=await db.pine_scripts.find_one({'_id':sid})
    if not row or not visible(row,user):raise HTTPException(404,'Script not found')
    return public(row,user,source=True)


@router.get('/api/pine-scripts/{sid}/download')
async def download(sid:str,user:dict=Depends(get_current_user)):
    row=await db.pine_scripts.find_one({'_id':sid})
    if not row or not visible(row,user):raise HTTPException(404,'Script not found')
    filename=re.sub(r'[^A-Za-z0-9_-]','_',row['title'])[:80] or 'kaos-script'
    return Response(row['source'],media_type='text/plain',headers={'Content-Disposition':f'attachment; filename="{filename}.pine"',
        'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})


async def save(request,user,sid=None,admin=False):
    if user.get('account_status','active')!='active':raise HTTPException(403,'Account disabled')
    data=await payload(request)
    if not data.rights_confirmed:raise HTTPException(422,'Confirm you have permission to share this source and thumbnail')
    old=await db.pine_scripts.find_one({'_id':sid}) if sid else None
    if sid and (not old or (old['author_id']!=user['id'] and not admin)):
        raise HTTPException(404,'Script not found')
    if not admin and (data.official or data.featured or data.moderation_note or data.status not in ('draft','pending','archived')):
        raise HTTPException(403,'Only administrators may publish, feature or moderate scripts')
    if not old and not admin and await db.pine_scripts.count_documents({'author_id':user['id']})>=100:
        raise HTTPException(409,'Member upload limit reached; contact KAOS support')
    if old and old['revision']!=data.revision:raise HTTPException(409,'Script changed; reload it before saving')
    image=old.get('thumbnail') if old else None
    if data.thumbnail and data.thumbnail!=image:
        image=await asyncio.to_thread(thumbnail,data.thumbnail)
    if not image:raise HTTPException(422,'A thumbnail is required')
    identity=sid or uuid4().hex
    values={'id':identity,'title':data.title,'description':data.description,'kind':data.kind,
        'market':data.market,'timeframe':data.timeframe,'source':data.source,'thumbnail':image,
        'status':data.status,'official':data.official if admin else False,'featured':data.featured if admin else False,
        'moderation_note':data.moderation_note if admin else '', 'updated_at':now_iso(),'revision':uuid4().hex,
        'rights_confirmed_at':now_iso()}
    event={'actor_id':user['id'],'at':values['updated_at'],'status':values['status'],'action':'update' if old else 'create'}
    if old:
        changed=await db.pine_scripts.update_one({'_id':sid,'revision':data.revision},
            {'$set':values,'$push':{'trail':{'$each':[event],'$slice':-30}}})
        if changed.matched_count!=1:raise HTTPException(409,'Script changed; reload before saving')
        row={**old,**values}
    else:
        row={'_id':identity,**values,'author_id':user['id'],'author_name':str(user.get('username') or 'KAOS member')[:80],
             'created_at':now_iso(),'trail':[event]}
        await db.pine_scripts.insert_one(row)
    return public(row,user,source=True)


@router.post('/api/pine-scripts')
async def create(request:Request,user:dict=Depends(get_current_user)):
    return await save(request,user)


@router.put('/api/pine-scripts/{sid}')
async def update(sid:str,request:Request,user:dict=Depends(get_current_user)):
    return await save(request,user,sid)


@router.post('/api/admin/pine-scripts')
async def admin_create(request:Request,user:dict=Depends(admin_user)):
    return await save(request,user,admin=True)


@router.put('/api/admin/pine-scripts/{sid}')
async def admin_update(sid:str,request:Request,user:dict=Depends(admin_user)):
    return await save(request,user,sid,admin=True)


@router.delete('/api/admin/pine-scripts/{sid}')
async def admin_delete(sid:str,revision:str=Query(...,min_length=1,max_length=64),user:dict=Depends(admin_user)):
    result=await db.pine_scripts.delete_one({'_id':sid,'revision':revision})
    if result.deleted_count!=1:raise HTTPException(409,'Script changed or already deleted; refresh the list')
    return {'deleted':True}
