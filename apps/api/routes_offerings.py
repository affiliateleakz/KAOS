"""IPO calendar and sourced ICO research; no offer purchase, endorsement or auto-trading."""
import csv
import io
import hashlib
from datetime import datetime,timezone
from typing import Literal
import httpx
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,HttpUrl
from pymongo.errors import DuplicateKeyError
from auth import require_role
from routes_opportunity import member
from db import db,now_iso,new_id
import radar_settings

router=APIRouter(tags=['offerings-research'])


def ipo_rows(text):
    rows=[]
    for item in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        try:
            date=datetime.strptime(item['ipoDate'],'%Y-%m-%d').date().isoformat()
            name=item['name'].strip()[:160];symbol=item['symbol'].strip()[:24]
            if not name or not symbol:continue
            def price(value):
                try:
                    x=float(value);return x if 0<x<1e9 else None
                except (TypeError,ValueError):return None
            rows.append({'name':name,'symbol':symbol,'date':date,'kind':'ipo','currency':item.get('currency','USD')[:8],'exchange':item.get('exchange','')[:80],'priceLow':price(item.get('priceRangeLow')),'priceHigh':price(item.get('priceRangeHigh')),'source':'Alpha Vantage IPO calendar','sourceUrl':'https://www.alphavantage.co/documentation/#ipo-calendar','dateType':'scheduled, subject to change'})
        except (KeyError,ValueError,TypeError):continue
        if len(rows)>=250:break
    return rows


async def ipo_calendar():
    cfg=await radar_settings.settings('alphavantage')
    if not cfg.get('enabled',True) or not cfg.get('api_key') or cfg.get('configuration_error'):
        return {'state':'setup_required','items':[],'message':'Uses the same Alpha Vantage key configured in Radar Sources. No extra member API key is needed.'}
    fingerprint=hashlib.sha256(cfg['api_key'].encode()).hexdigest();key=fingerprint+':ipo';now=datetime.now(timezone.utc);stamp=now.timestamp()
    old=await db.kaos_ipo_cache.find_one({'_id':key})
    if old and 0<=stamp-old.get('checked',0)<21600:return old['result']
    try:await db.kaos_alpha_locks.update_one({'_id':key,'until':{'$lt':stamp}},{'$set':{'until':stamp+30}},upsert=True)
    except DuplicateKeyError:return {'state':'collecting','items':old.get('result',{}).get('items',[]) if old else []}
    try:
        try:await db.kaos_alpha_usage.update_one({'_id':fingerprint+':'+now.strftime('%Y-%m-%d'),'count':{'$lt':20}},{'$inc':{'count':1}},upsert=True)
        except DuplicateKeyError:return {'state':'rate_limited','items':old.get('result',{}).get('items',[]) if old else [],'message':'Shared provider daily allowance is used. Retry after the daily reset.'}
        async with httpx.AsyncClient(timeout=12,follow_redirects=False) as client:
            response=await client.get('https://www.alphavantage.co/query',params={'function':'IPO_CALENDAR','apikey':cfg['api_key']});response.raise_for_status()
        if len(response.content)>2_000_000:raise ValueError('Calendar response too large')
        rows=ipo_rows(response.text)
        result={'state':'complete' if rows else 'unavailable','items':rows,'asOf':now.isoformat(),'message':'Scheduled IPO dates and ranges can change; this is research, not an offering invitation.' if rows else 'The provider did not return a usable IPO calendar.'}
        await db.kaos_ipo_cache.update_one({'_id':key},{'$set':{'checked':stamp,'result':result}},upsert=True)
        return result
    except (httpx.HTTPError,ValueError):return {'state':'unavailable','items':[],'message':'IPO calendar is unavailable. No dates or prices are invented.'}
    finally:await db.kaos_alpha_locks.update_one({'_id':key},{'$set':{'until':0}})


class Offering(BaseModel):
    kind:Literal['ipo','ico']
    name:str=Field(min_length=2,max_length=160)
    symbol:str=Field(min_length=1,max_length=24,pattern=r'^[A-Za-z0-9.\-]+$')
    date:str|None=Field(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$')
    sourceUrl:HttpUrl
    summary:str=Field(default='',max_length=1200)
    published:bool=False


@router.get('/api/v1/intelligence/offerings')
async def offerings(kind:Literal['ipo','ico']='ipo',user=Depends(member)):
    curated=await db.kaos_offerings.find({'kind':kind,'published':True},{'_id':0,'createdBy':0}).sort('date',1).limit(100).to_list(100)
    data=await ipo_calendar() if kind=='ipo' else {'state':'complete' if curated else 'no_confirmed_data','items':[],'message':'ICO entries require a dated primary source reviewed by KAOS. There is no unconfigured third-party feed or invented token calendar.'}
    return {**data,'items':data['items']+curated,'kind':kind,'researchOnly':True,'executionEnabled':False,'risks':['Offering dates, prices and availability may change.','An IPO or token listing is not a verified trading signal.','ICO links and issuer claims are not an endorsement; liquidity and eligibility may be limited.']}


@router.post('/api/admin/radar/offerings')
async def add_offering(req:Offering,user=Depends(require_role('super_admin'))):
    if req.sourceUrl.scheme!='https':raise HTTPException(422,'Use an HTTPS primary source URL')
    if req.date:
        try:datetime.strptime(req.date,'%Y-%m-%d')
        except ValueError:raise HTTPException(422,'Invalid offering date')
    row=req.model_dump(mode='json');row.update(id=new_id('offering'),source='KAOS source review',updatedAt=now_iso(),createdBy=user['id'],dateType='issuer-reported, subject to change')
    await db.kaos_offerings.insert_one(dict(row))
    return {k:v for k,v in row.items() if k!='createdBy'}
