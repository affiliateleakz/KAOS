#!/usr/bin/env python3
"""KAOS Coinbase local bridge. Read-only Coinbase Advanced Trade REST adapter.
Dependencies: pip install PyJWT cryptography requests
Start: python kaos_coinbase_bridge.py
Keys held in process memory only. No live orders supported in this stage.
"""
import json, os, time, uuid, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import jwt, requests

HOST='127.0.0.1'; PORT=8766
BASE='https://api.coinbase.com'
state={'key_name':None,'private_key':None,'connected':False}
lock=threading.Lock()

def sign(method,path):
    with lock: name=state['key_name']; key=state['private_key']
    if not name or not key: raise ValueError('Coinbase credentials not configured')
    now=int(time.time())
    claims={'sub':name,'iss':'cdp','nbf':now,'exp':now+120,'uri':f'{method} api.coinbase.com{path}'}
    return jwt.encode(claims,key,algorithm='ES256',headers={'kid':name,'nonce':uuid.uuid4().hex})

def coinbase(method,path):
    token=sign(method,path)
    r=requests.request(method,BASE+path,headers={'Authorization':'Bearer '+token,'Accept':'application/json'},timeout=12)
    try: body=r.json()
    except ValueError: body={'error':'Invalid JSON from Coinbase'}
    if not r.ok: raise RuntimeError('Coinbase API '+str(r.status_code)+': '+str(body)[:300])
    return body

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def _origin_ok(self):
        origin=self.headers.get('Origin','')
        return origin.startswith('chrome-extension://') and '/' not in origin[len('chrome-extension://'):]
    def _reply(self,status,data):
        body=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin','null') if self._origin_ok() else 'null')
        self.send_header('Vary','Origin')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def do_OPTIONS(self):
        if not self._origin_ok():return self._reply(403,{'error':'Extension origin required'})
        self._reply(200,{'ok':True})
    def do_POST(self):
        if not self._origin_ok():return self._reply(403,{'error':'Extension origin required'})
        if self.path=='/coinbase/disconnect':
            with lock:state.update(key_name=None,private_key=None,connected=False)
            return self._reply(200,{'connected':False})
        if self.path!='/coinbase/connect':return self._reply(404,{'error':'Not found'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<2 or n>20000:raise ValueError('Invalid payload length')
            data=json.loads(self.rfile.read(n)); name=data.get('key_name','').strip();key=data.get('private_key','').replace('\\n','\n').strip()
            if not name.startswith('organizations/') or '/apiKeys/' not in name or 'BEGIN EC PRIVATE KEY' not in key and 'BEGIN PRIVATE KEY' not in key:
                raise ValueError('Expected Coinbase CDP API key name and PEM private key')
            with lock:state.update(key_name=name,private_key=key,connected=False)
            accounts=coinbase('GET','/api/v3/brokerage/accounts')
            with lock:state['connected']=True
            return self._reply(200,{'connected':True,'account_count':len(accounts.get('accounts',[]))})
        except Exception as e:
            with lock:state.update(key_name=None,private_key=None,connected=False)
            return self._reply(400,{'connected':False,'error':str(e)[:350]})
    def do_GET(self):
        if not self._origin_ok():return self._reply(403,{'error':'Extension origin required'})
        if self.path=='/coinbase/status':return self._reply(200,{'connected':state['connected'],'mode':'read_only'})
        if not state['connected']:return self._reply(409,{'error':'Connect Coinbase first'})
        path={'/coinbase/accounts':'/api/v3/brokerage/accounts','/coinbase/products':'/api/v3/brokerage/products?limit=50'}.get(self.path)
        if not path:return self._reply(404,{'error':'Not found'})
        try:return self._reply(200,coinbase('GET',path))
        except Exception as e:return self._reply(502,{'error':str(e)[:350]})

if __name__=='__main__':
    print('KAOS Coinbase read-only bridge listening on http://127.0.0.1:8766')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
