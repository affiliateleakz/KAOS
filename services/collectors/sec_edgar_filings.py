"""SEC EDGAR *filing discovery*, NOT parsed insider trades or hedge-fund holdings.

A Form 4 filing is NOT a purchase; 13F is NOT live institutional flows.
Run at a modest frequency with a responsible identifying User-Agent.
"""
import argparse
import json
import os
import re
import time
from datetime import date, datetime, timezone, timedelta
from urllib.request import urlopen
from zoneinfo import ZoneInfo
from collector_common import read_json, submit, utc

SEC_BASE = 'https://data.sec.gov/submissions/'
EDGAR_ARCHIVES = 'https://www.sec.gov/Archives/edgar/data/'
SYMBOL_RE = re.compile(r'^[A-Z][A-Z0-9.]{0,11}$')
FORM_TYPES={'4':'insider','4/A':'insider', '8-K':'filing','8-K/A':'filing',
            '10-Q':'filing','10-K':'filing'}
ACCESSION_RE=re.compile(r'^\d{10}-\d{2}-\d{6}$')
DOCUMENT_RE=re.compile(r'^[A-Za-z0-9_.-]{1,160}$')


def validate_watchlist(raw):
    if not isinstance(raw,list) or len(raw)>40: raise ValueError('sec_watchlist must have <=40 entries')
    seen, result=set(),[]
    for item in raw:
        if not isinstance(item,dict) or set(item)!={'symbol','cik'}:
            raise ValueError('SEC watch entries must have symbol and cik only')
        symbol,cik=item['symbol'],item['cik']
        if not isinstance(symbol,str) or not SYMBOL_RE.fullmatch(symbol):
            raise ValueError('Invalid SEC watch ticker')
        if isinstance(cik,int): cik=str(cik)
        if not isinstance(cik,str) or not cik.isascii() or not cik.isdigit() or not 1<=len(cik)<=10:
            raise ValueError('CIK must be a 1-10 digit SEC identifier')
        cik=cik.zfill(10)
        if (symbol,cik) in seen: raise ValueError('Duplicate SEC watch entry')
        seen.add((symbol,cik))
        result.append({'symbol':symbol,'cik':cik})
    return result


def get_submissions(cik, user_agent, *, opener=urlopen):
    if not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik): raise ValueError('Invalid padded CIK')
    if not user_agent or not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
        raise ValueError('SEC_USER_AGENT must identify your organization and contact email')
    return read_json(SEC_BASE+'CIK'+cik+'.json',headers={'User-Agent':user_agent,
                    'Accept':'application/json','Accept-Encoding':'identity'},opener=opener,timeout=30)


def accepted_time(value, filing_date):
    """SEC acceptance timestamps in company-submission JSON are Eastern local time."""
    if isinstance(value,str):
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo('America/New_York'))
            return dt.astimezone(timezone.utc), 'SEC acceptance time'
        except ValueError: pass
    day=date.fromisoformat(str(filing_date))
    # Date-only fallback is an approximation. Mark in summary.
    return datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc),'filing date only (UTC day marker, NOT timestamp)'


def observe_filings(symbol,cik,payload,now=None, *, max_items=30):
    now=utc(now or datetime.now(timezone.utc))
    if not isinstance(payload,dict): raise ValueError('Invalid SEC payload')
    expected=int(cik)
    if int(payload.get('cik',-1))!=expected:
        raise ValueError('SEC response CIK does not match requested company')
    r=(payload.get('filings') or {}).get('recent') or {}
    forms=r.get('form') or []
    accessions=r.get('accessionNumber') or []
    dates=r.get('filingDate') or []
    accepted=r.get('acceptanceDateTime') or []
    docs=r.get('primaryDocument') or []
    if any(not isinstance(x,list) for x in [forms,accessions,dates,accepted,docs]):
        raise ValueError('Invalid SEC recent filings arrays')
    if not (len(forms)==len(accessions)==len(dates)==len(docs)):
        raise ValueError('SEC recent filing columns are out of alignment')
    # acceptanceDateTime may be absent in older API variants; use date-only.
    if len(accepted) not in (0,len(forms)):
        raise ValueError('SEC acceptance timestamps are misaligned')
    out=[]
    for i,form in enumerate(forms):
        if form not in FORM_TYPES: continue
        accession,document=accessions[i],docs[i]
        if not isinstance(accession,str) or not ACCESSION_RE.fullmatch(accession):continue
        if not isinstance(document,str) or not DOCUMENT_RE.fullmatch(document):continue
        try: published,time_precision=accepted_time(accepted[i] if accepted else None,dates[i])
        except (ValueError,TypeError):continue
        if published>now or now-published>timedelta(days=7):continue
        url=(EDGAR_ARCHIVES+str(int(cik))+'/'+accession.replace('-','')+'/'+document)
        classification=FORM_TYPES[form]
        caution=('Filing discovered; does NOT establish insider BUY/SELL or transaction date.'
                 if classification=='insider' else
                 'Corporate disclosure filing, NOT directional market or flow prediction.')
        summary=(f'SEC EDGAR {form} for {symbol} (CIK {cik}) dated {dates[i]}; '
                 f'{time_precision}. {caution} Review the actual filing before assigning sentiment.')
        out.append({'asset':symbol,'asset_class':'stock','source':classification,
                    'direction':'neutral','strength':0.25,
                    'event_id':f'sec:{cik}:{accession}',
                    'observed_at':now.isoformat(),'published_at':published.isoformat(),
                    'source_url':url,'summary':summary[:1200]})
        if len(out)>=max_items: break
    return out


def run(watchlist, *, user_agent=None, now=None, opener=urlopen, pause_seconds=1.0):
    watchlist=validate_watchlist(watchlist)
    if not watchlist: return [],[]
    user_agent=user_agent or os.getenv('SEC_USER_AGENT','')
    if not user_agent or not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
        return [],[{'provider':'sec','reason':'missing_valid_SEC_USER_AGENT'}]
    now=utc(now or datetime.now(timezone.utc))
    observations,issues=[],[]
    for i,item in enumerate(watchlist):
        if i and pause_seconds: time.sleep(pause_seconds)
        try:
            doc=get_submissions(item['cik'],user_agent,opener=opener)
            observations.extend(observe_filings(item['symbol'],item['cik'],doc,now))
        except Exception as exc:
            issues.append({'provider':'sec','symbol':item['symbol'],'reason':str(exc)})
    return observations,issues


def main():
    p=argparse.ArgumentParser(description='KAOS SEC corporate filings / Form 4 discovery')
    p.add_argument('--config',default='market_universe.example.json')
    p.add_argument('--dry-run',action='store_true')
    p.add_argument('--api',default=os.getenv('KAOS_API_BASE',''))
    args=p.parse_args()
    with open(args.config,encoding='utf-8') as f: doc=json.load(f)
    observations,issues=run(doc.get('sec_watchlist',[]))
    result={'provider':'sec_edgar','observations_count':len(observations),'issues':issues,'mode':'research_only'}
    if args.dry_run:result['observations']=observations
    else:result['delivery']=submit(observations,args.api)
    print(json.dumps(result,indent=2))
if __name__=='__main__': main()
