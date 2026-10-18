"""Incremental *safe* Ethereum block scanner with atomic, persistent checkpoint.

Backfills skipped safe block heights over repeated runs. On cold start scans
only the latest safe block (no invented historical coverage). No order API.
Runs through a configured private HTTPS RPC provider; respects provider limits.
"""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from ethereum_whales import _validated_rpc,observe_safe_block,parse_hex


def fetch_block(rpc_url, block_tag, opener=urlopen):
    _validated_rpc(rpc_url)
    if block_tag!='safe' and not (isinstance(block_tag,str) and block_tag.startswith('0x') and len(block_tag)<20):
        raise ValueError('Unsafe block tag')
    body={'jsonrpc':'2.0','id':1,'method':'eth_getBlockByNumber','params':[block_tag,True]}
    req=Request(rpc_url,data=json.dumps(body).encode(),method='POST',
                headers={'Content-Type':'application/json','User-Agent':'KAOS-Research-Only/3.0'})
    with opener(req,timeout=30) as resp:result=json.load(resp)
    if not isinstance(result,dict) or not isinstance(result.get('result'),dict) or result.get('error'):
        raise ValueError('Invalid Ethereum block result')
    return result['result']


def load_state(path):
    p=Path(path)
    if not p.exists():return None
    doc=json.loads(p.read_text(encoding='utf-8'))
    num=doc.get('last_safe_block')
    if not isinstance(num,int) or isinstance(num,bool) or not 0<=num<2**63:
        raise ValueError('Corrupted Ethereum block checkpoint')
    return num


def save_state(path,num):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(mode='w',dir=str(p.parent),encoding='utf-8',delete=False) as f:
        json.dump({'last_safe_block':num,'network':'ethereum-mainnet'},f)
        filename=f.name
    os.replace(filename,p)


def scan_safe_blocks(rpc_url,state_path,min_eth=500,max_blocks=32,opener=urlopen,*,commit=False):
    if not 1<=max_blocks<=64:raise ValueError('max_blocks must be 1..64')
    safe=fetch_block(rpc_url,'safe',opener)
    current=parse_hex(safe.get('number'))
    previous=load_state(state_path)
    if previous is not None and previous>current:
        raise ValueError('Ethereum safe height regressed; checkpoint must be reviewed')
    if previous==current:return [],{'last_safe_block':current,'processed_blocks':0,'caught_up':True}
    start=current if previous is None else previous+1
    end=min(current,start+max_blocks-1)
    observations=[]
    for num in range(start,end+1):
        block=safe if num==current else fetch_block(rpc_url,hex(num),opener)
        if parse_hex(block.get('number'))!=num:raise ValueError('Unexpected Ethereum block height')
        observations.extend(observe_safe_block(block,min_eth))
    # For KAOS cloud delivery, defer checkpoint until API acknowledges all events.
    # Replays use stable event ids, so retrying won't create duplicate records.
    if commit: save_state(state_path,end)
    return observations,{'last_safe_block':end,'processed_blocks':end-start+1,
                          'caught_up':end==current,'latest_safe_block':current,
                          'scope':'native_eth_value_only'}
