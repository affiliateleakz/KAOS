"""Owner-managed, encrypted research-provider settings; never exposes secret values."""
import os
from cryptography.fernet import InvalidToken
from fastapi import HTTPException
from db import db
from commerce_providers import cipher, vault_ready, initialize_vault

CATALOG = {
 'reddit': {'name':'Reddit','description':'Read-only Reddit post search. Requires approved OAuth API access. Priority social source.', 'fields':{'client_id':('Client ID','REDDIT_CLIENT_ID'),'client_secret':('Client secret','REDDIT_CLIENT_SECRET'),'user_agent':('Identifying User-Agent','REDDIT_USER_AGENT')}},
 'x': {'name':'X','description':'Official recent-post search; your X API plan must permit this endpoint. Priority social source.', 'fields':{'bearer_token':('API bearer token','X_BEARER_TOKEN')}},
 'bluesky': {'name':'Bluesky','description':'Bounded cashtag samples. Public access is tried without credentials; a Bluesky app password enables authenticated search.', 'fields':{'identifier':('Account handle','BLUESKY_IDENTIFIER'),'app_password':('App password (not your main password)','BLUESKY_APP_PASSWORD')}},
 'facebook': {'name':'Facebook Pages','description':'Posts from your authorized Page only. This is not all-Facebook public search.', 'fields':{'page_id':('Authorized Page ID','FACEBOOK_PAGE_ID'),'access_token':('Page access token','FACEBOOK_PAGE_ACCESS_TOKEN'),'graph_version':('Graph API version, e.g. v23.0','FACEBOOK_GRAPH_VERSION')}},
 'sec': {'name':'SEC insider transactions','description':'Recent Form 4 purchase/sale disclosures for stock tickers. Requires an identifying SEC User-Agent with a contact email.', 'fields':{'user_agent':('Organization and contact email','SEC_USER_AGENT')}},
 'ethereum': {'name':'Ethereum large transfers','description':'One safe block of native ETH transfers of at least 500 ETH. Not BTC/ERC-20 coverage or wallet-owner identification.', 'fields':{'rpc_url':('HTTPS Ethereum JSON-RPC URL','ETH_RPC_URL')}},
 'government': {'name':'Congressional disclosures','description':'Quiver historical Congress trades for selected stock tickers. Requires an API plan permitted for your use; transaction and report dates are retained.', 'fields':{'api_key':('Quiver API key','QUIVER_API_KEY')}},
}

async def settings(provider):
 if provider not in CATALOG: raise HTTPException(404,'Unknown research provider')
 doc=await db.radar_provider_settings.find_one({'_id':provider}) or {}
 values={};problem=False
 for name,(_,env) in CATALOG[provider]['fields'].items():
  encrypted=doc.get('encrypted',{}).get(name)
  if encrypted:
   try: values[name]=cipher().decrypt(encrypted.encode()).decode()
   except (HTTPException,InvalidToken,ValueError):problem=True;values[name]=''
  else:values[name]=os.getenv(env,'').strip()
 values.update(enabled=doc.get('enabled',True),configuration_error=problem)
 return values

async def public_settings(provider):
 info=CATALOG[provider];doc=await db.radar_provider_settings.find_one({'_id':provider}) or {}
 configured={name:bool(doc.get('encrypted',{}).get(name) or os.getenv(env,'').strip()) for name,(_,env) in info['fields'].items()}
 ready=all(configured.values()) if provider!='bluesky' else True
 return {'id':provider,'name':info['name'],'description':info['description'],'enabled':doc.get('enabled',True),
         'configured':ready,'access':'Public search / optional login' if provider=='bluesky' else ('Ready to try' if ready else 'Setup required'),
         'fields':[{'name':name,'label':label,'configured':configured[name],'secret':name in ('client_secret','bearer_token','app_password','access_token','api_key','rpc_url')} for name,(label,_) in info['fields'].items()]}
