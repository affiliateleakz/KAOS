"""Research-only *native ETH* large transfer scanner, via a user-configured Ethereum RPC.

A transfer is not a verified investor accumulation event, an exchange inflow,
ERC-20 movement, or an automated trade signal. Uses the 'safe' block tag.
No private keys, token transfers, internal transactions, or wallet labeling.
"""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from collector_common import submit

WEI_PER_ETH = 10**18
DEFAULT_MIN_ETH = 500


def _validated_rpc(url):
    if not isinstance(url, str):
        raise ValueError('ETH_RPC_URL required')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('ETH_RPC_URL must be an HTTPS JSON-RPC URL without userinfo or fragment')
    # Credentials embedded in the path/query are permitted by some RPC providers;
    # never put URL itself into observations or exception messages.
    return url


def rpc_call(url, method, params, opener=urlopen):
    _validated_rpc(url)
    if method != 'eth_getBlockByNumber' or params != ['safe', True]:
        raise ValueError('Only read-only safe-block lookup is supported')
    request = Request(url, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                   'method': method, 'params': params}).encode('utf-8'),
                   method='POST', headers={'Content-Type': 'application/json',
                   'User-Agent': 'KAOS-Research-Only/3.0'})
    with opener(request, timeout=30) as response:
        doc = json.load(response)
    if not isinstance(doc, dict) or doc.get('error') or not isinstance(doc.get('result'), dict):
        raise ValueError('Ethereum RPC safe-block response invalid or unavailable')
    return doc['result']


def parse_hex(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]+', value):
        raise ValueError('Invalid hex integer from Ethereum JSON-RPC')
    return int(value, 16)


def observe_safe_block(block, min_eth=DEFAULT_MIN_ETH, now=None):
    now = now or datetime.now(timezone.utc)
    if not 1 <= min_eth <= 1_000_000:
        raise ValueError('Invalid ETH minimum threshold')
    if not isinstance(block, dict) or not isinstance(block.get('transactions'), list):
        raise ValueError('Invalid full Ethereum block response')
    num = parse_hex(block.get('number'))
    block_time = datetime.fromtimestamp(parse_hex(block.get('timestamp')), timezone.utc)
    if block_time > now or (now - block_time).total_seconds() > 7200:
        return []  # stale/invalid block; not evidence of activity now
    result=[]
    for tx in block['transactions']:
        if not isinstance(tx,dict): continue
        txid=tx.get('hash')
        if not isinstance(txid,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',txid): continue
        try:
            wei=parse_hex(tx.get('value'))
        except ValueError:
            continue
        if wei < int(min_eth*WEI_PER_ETH): continue
        # Transfer of *native ETH*, includes contract payable calls, not necessarily wallet-to-wallet.
        eth=wei/WEI_PER_ETH
        result.append({'asset':'ETH','asset_class':'crypto','source':'onchain',
            'direction':'neutral','strength':0.5,
            'event_id':f'eth-mainnet:{txid.lower()}',
            'observed_at':block_time.isoformat(), 'published_at':block_time.isoformat(),
            'source_url':f'https://etherscan.io/tx/{txid}',
            'summary':(f'Ethereum safe block #{num}: {eth:,.2f} native ETH value '
                f'in on-chain transaction (minimum {min_eth:g} ETH). '
                'This does NOT identify a whale owner, trade direction, exchange activity, '
                'ERC-20 transfer, or intention to buy/sell. Research only.')[:1200]})
    return result


def fetch_observations(url, minimum=DEFAULT_MIN_ETH, opener=urlopen):
    return observe_safe_block(rpc_call(url,'eth_getBlockByNumber',['safe',True],opener), minimum)


def main():
    p=argparse.ArgumentParser(description='KAOS native ETH large-value scanner (safe block only)')
    p.add_argument('--min-eth',type=float,default=DEFAULT_MIN_ETH)
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    args=p.parse_args()
    url=os.getenv('ETH_RPC_URL','')
    if not url: p.error('ETH_RPC_URL required')
    items=fetch_observations(url,args.min_eth)
    result={'provider':'ethereum','minimum_eth':args.min_eth,'observations':len(items),
            'scope':'one_safe_block_native_ETH_only','mode':'research_only'}
    if args.dry_run: result['sample']=items[:5]
    elif items: result['delivery']=submit(items,args.api)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
