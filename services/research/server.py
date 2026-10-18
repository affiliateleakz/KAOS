"""Local-only, research-only adapter for TauricResearch TradingAgents.
No trading API, broker credentials, order routing, or live signal endpoint.
"""
import json,os,re,datetime,traceback,statistics
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit


def analyze_otc(data):
    """Causal, research-only technical specialist opinions on closed candles.
    Never predicts probabilities or authorizes broker orders.
    """
    market=str(data.get('market','UNKNOWN')).strip()[:40]
    raw=data.get('candles',[])
    if not isinstance(raw,list) or len(raw)<60 or len(raw)>12000:raise ValueError('Supply 60 to 12000 closed candles')
    candles=[]
    for c in raw:
        if not isinstance(c,dict):raise ValueError('Each candle must be an object')
        candles.append({k:float(c[k]) for k in ('open','high','low','close')})
    if any(not (c['low']<=min(c['open'],c['close'])<=max(c['open'],c['close'])<=c['high']) for c in candles):raise ValueError('Invalid OHLC candle')
    closes=[c['close'] for c in candles]
    if min(closes)<=0:raise ValueError('Prices must be positive')
    # Last observation must be a completed candle. No future candle used.
    ema=lambda vals,n: _ema(vals,n)
    fast=ema(closes,9);slow=ema(closes,21)
    last=candles[-1]; prior=candles[-2]
    highs=[c['high'] for c in candles[-22:-2]];lows=[c['low'] for c in candles[-22:-2]]
    widths=[c['high']-c['low'] for c in candles[-31:-1]]
    typical=statistics.median(widths) or 1e-12
    opinions=[]
    trend='BUY' if fast[-1]>slow[-1] and fast[-1]>fast[-2] else 'SELL' if fast[-1]<slow[-1] and fast[-1]<fast[-2] else 'HOLD'
    opinions.append({'agent':'trend','vote':trend,'reason':'EMA 9/21 alignment and EMA9 slope'})
    mom=closes[-1]-closes[-4]
    momentum='BUY' if mom>typical*.6 else 'SELL' if mom< -typical*.6 else 'HOLD'
    opinions.append({'agent':'momentum','vote':momentum,'reason':'Three-candle close displacement relative to typical range'})
    rejection='BUY' if last['low']<min(lows) and last['close']>min(lows) and last['close']>last['open'] else 'SELL' if last['high']>max(highs) and last['close']<max(highs) and last['close']<last['open'] else 'HOLD'
    opinions.append({'agent':'liquidity_rejection','vote':rejection,'reason':'Sweep of previous 20-candle extreme and close back inside'})
    votes={side:sum(x['vote']==side for x in opinions) for side in ('BUY','SELL')}
    decision='BUY' if votes['BUY']>=2 and votes['SELL']==0 else 'SELL' if votes['SELL']>=2 and votes['BUY']==0 else 'HOLD'
    return {'market':market,'closed_candles':len(candles),'decision':decision,'agents':opinions,'votes':votes,'typical_range':typical,'mode':'offline deterministic research','trade_authorized':False,'model_win_rate':None,'warning':'Not TradingAgents LLM inference, not validated as profitable; never use as live trade authorization.'}

def _ema(vals,n):
    alpha=2/(n+1);result=[vals[0]]
    for v in vals[1:]:result.append(alpha*v+(1-alpha)*result[-1])
    return result

HOST='127.0.0.1';PORT=8765
class Handler(BaseHTTPRequestHandler):
    def reply(self,status,data):
        b=json.dumps(data,default=str).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)))
        self.send_header('Access-Control-Allow-Origin','*') # local-only binding; no broker secrets exposed
        self.send_header('Access-Control-Allow-Methods','POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self):self.reply(200,{'ok':True})
    def do_GET(self):
        if self.path=='/kaos-ai/archive':
            from kaos_ai_lab import list_archive
            return self.reply(200,{'datasets':list_archive(),'trade_authorized':False})
        if self.path.startswith('/kaos-ai/notebook/'): 
            from kaos_ai_lab import read_notebook
            try:return self.reply(200,{'entries':read_notebook(self.path.split('/')[-1]),'trade_authorized':False})
            except ValueError as e:return self.reply(400,{'error':str(e)})
        if self.path!='/health':return self.reply(404,{'error':'not found'})
        try:
            from tradingagents.graph.trading_graph import TradingAgentsGraph
            installed=True
        except ImportError:installed=False
        self.reply(200,{'status':'ok','mode':'research-only','otc_research_supported':True,'tradingagents_installed':installed,'trading_enabled':False})
    def do_POST(self):
        if self.path in ('/kaos-ai/ingest','/kaos-ai/notebook'):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>8000000:return self.reply(413,{'error':'request too large'})
                obj=json.loads(self.rfile.read(n))
                from kaos_ai_lab import ingest,notebook
                return self.reply(200,ingest(obj) if self.path.endswith('ingest') else notebook(obj))
            except (ValueError,TypeError,KeyError,OverflowError) as e:return self.reply(400,{'error':str(e)})
        if self.path=='/backtest':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>32000000:return self.reply(413,{'error':'Backtest request exceeds 32MB'})
                from backtest import backtest
                return self.reply(200,backtest(json.loads(self.rfile.read(n))))
            except (ValueError,TypeError,KeyError) as e:return self.reply(400,{'error':str(e)})
            except Exception as e:return self.reply(500,{'error':str(e)})
        if self.path=='/otc/analyze':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n<1 or n>2000000:return self.reply(413,{'error':'payload must be 1-2,000,000 bytes'})
                data=json.loads(self.rfile.read(n))
                return self.reply(200,analyze_otc(data))
            except (ValueError,TypeError,KeyError) as e:return self.reply(400,{'error':str(e)})
        if self.path!='/research':return self.reply(404,{'error':'not found'})
        try:
            if int(self.headers.get('Content-Length','0'))>8192: return self.reply(413,{'error':'request too large'})
            obj=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            ticker=obj.get('ticker','').upper().strip();date=obj.get('date','')
            if not re.fullmatch(r'[A-Z0-9.\-]{1,20}',ticker):return self.reply(400,{'error':'invalid ticker'})
            try:datetime.date.fromisoformat(date)
            except ValueError:return self.reply(400,{'error':'invalid date'})
            if '_OTC' in ticker or ticker.endswith('OTC'):return self.reply(400,{'error':'Pocket Option OTC symbols require a custom data-provider adapter. TradingAgents cannot analyze them natively.'})
            try:
                from tradingagents.graph.trading_graph import TradingAgentsGraph
                from tradingagents.default_config import DEFAULT_CONFIG
            except ImportError:return self.reply(503,{'error':'TradingAgents not installed. See README.md for installation.'})
            config=DEFAULT_CONFIG.copy()
            # API keys are read from environment by TradingAgents, not supplied by extension.
            graph=TradingAgentsGraph(debug=False,config=config)
            state,decision=graph.propagate(ticker,date)
            # Deliberately return research recommendation only, not a trade signal.
            self.reply(200,{'mode':'research-only','ticker':ticker,'date':date,'research_recommendation':str(decision),'decision_state':str(state)[:20000],'trade_authorized':False})
        except Exception as e:self.reply(500,{'error':str(e),'trade_authorized':False})
if __name__=='__main__':
    print(f'KAOS TradingAgents research-only service on http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
