"""Owner-only paper research artifacts; never production model publication or orders."""
import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter,Depends,Response
from auth import require_role

router=APIRouter(prefix='/api/v1/ai/research',tags=['owner-paper-research'])
owner=require_role('super_admin')


@lru_cache(maxsize=1)
def micro_model():
    model=json.loads((Path(__file__).parent/'research_models/micro_reversion_v1.json').read_text())
    if model.get('researchOnly') is not True or model.get('executionEnabled') is not False or model.get('schema')!='kaos-crypto-12-v1':
        raise RuntimeError('Invalid isolated research artifact')
    return model


@router.get('/micro-reversion')
async def micro_reversion(response:Response,user=Depends(owner)):
    response.headers['Cache-Control']='private, no-store'
    return {'name':'KAOS Micro Reversion Research v1','model':micro_model(),
            'scope':'Binance BTCUSDT/ETHUSDT/SOLUSDT only; not Pocket Option OTC',
            'researchOnly':True,'executionEnabled':False,'publishedMemberModel':False,
            'state':'failed_adverse_fill_gate',
            'notice':'Experimental paper testing only. No broker orders. Two-day historical result is sensitive to entry prices.',
            'historical':{'idealWinRate':769/1133,'delayedWinRate':629/1037,'adverseOneBpWinRate':377/1295,'days':2,'assumedPayout':.8}}
