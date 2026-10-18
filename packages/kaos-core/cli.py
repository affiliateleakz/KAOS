import argparse,json
from kaos.core import ENGINES
from kaos.research import load_csv,replay
p=argparse.ArgumentParser()
p.add_argument('--engine',choices=sorted(ENGINES),required=True)
p.add_argument('--csv',required=True)
p.add_argument('--symbol',required=True)
p.add_argument('--fee-bps',type=float,default=10)
p.add_argument('--slippage-bps',type=float,default=2)
a=p.parse_args()
result=replay(a.engine,a.symbol,load_csv(a.csv),a.fee_bps,a.slippage_bps)
print(json.dumps({k:v for k,v in result.items() if k!='trades_log'},indent=2))
