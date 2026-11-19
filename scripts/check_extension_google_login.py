"""Read-only readiness checks; an actual Google sign-in is still required."""
import argparse
import json
from pathlib import Path
from urllib.request import Request,urlopen

STORE_ID='gbobopmnjgeeegniphckfpalhnebapjm'
ROOT=Path(__file__).resolve().parents[1]


def document(url):
    with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'KAOS-Store-Readiness/1.0'}),timeout=15) as response:
        body=response.read(65536).decode('utf-8',errors='replace')
        if 'bot verification' in body.lower() or 'lsrecaptcha' in body.lower():
            raise ValueError('Hosting returned a bot-verification page; API clients and reviewers must receive JSON.')
        value=json.loads(body)
        if response.status!=200 or not isinstance(value,dict):raise ValueError('API did not return a JSON object with HTTP 200')
        return value


def check(host):
    manifest=json.loads((ROOT/'apps/extension/manifest.json').read_text())
    if manifest.get('homepage_url')!='https://chromewebstore.google.com/detail/'+STORE_ID:raise ValueError('Wrong Chrome Web Store item')
    health=document(host.rstrip('/')+'/api')
    if health.get('status')!='ok':raise ValueError('KAOS API is not healthy')
    config=document(host.rstrip('/')+'/api/v1/extension/google/config')
    if not config.get('configured'):raise ValueError('Server KAOS_GOOGLE_EXTENSION_CLIENT_ID is missing')
    if config.get('client_id')!=manifest.get('oauth2',{}).get('client_id'):raise ValueError('Server and manifest Google client IDs differ')
    if config.get('store_item_id')!=STORE_ID:raise ValueError('Server reports a different store item')
    return {'state':'configuration_checks_passed','version':manifest['version'],'store_item_id':STORE_ID,
            'google_sign_in_verified':False,'next':'Test Google sign-in with the actual store-ID build and Google Cloud production consent configuration.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-host',default='https://api.tradingwithkaos.com')
    args=parser.parse_args()
    try:print(json.dumps(check(args.api_host),indent=2))
    except Exception as exc:
        print(json.dumps({'state':'blocked','reason':str(exc)}));return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
