"""SEC Form 4 *reported* open-market stock P/S transactions.

Transaction date and SEC disclosure/acceptance timestamps are different.
This is neither a live insider trade stream nor evidence of future returns.
Only parses Form 4 primary XML documents, non-derivative code P/S; ignores
awards, options, amendments (for now) and other disposition types.
"""
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from collector_common import utc
from sec_edgar_filings import (get_submissions, validate_watchlist, accepted_time,
    DOCUMENT_RE, ACCESSION_RE, EDGAR_ARCHIVES)

MAX_XML_BYTES = 2_000_000

def get_xml(url, user_agent, *, opener=urlopen):
    if not url.startswith(EDGAR_ARCHIVES) or not url.lower().endswith('.xml'):
        raise ValueError('SEC archive XML document URL required')
    if not user_agent or not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
        raise ValueError('Identifying SEC_USER_AGENT required')
    req=Request(url,headers={'User-Agent':user_agent,'Accept':'application/xml, text/xml'})
    with opener(req,timeout=30) as resp:
        content=resp.read(MAX_XML_BYTES+1)
    if len(content)>MAX_XML_BYTES: raise ValueError('SEC XML response exceeds safety limit')
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        raise ValueError('Unsafe XML declaration')
    return content


def field(parent,path):
    # SEC ownership XML often has no namespace, but support namespace-qualified tags.
    parts=path.split('/')
    current=parent
    for part in parts:
        current=next((c for c in current if c.tag.rsplit('}',1)[-1]==part),None)
        if current is None: return None
    return (current.text or '').strip() or None


def children(parent,name):
    return [c for c in parent if c.tag.rsplit('}',1)[-1]==name]


def parse_form4_xml(xml, *, symbol,cik,accession,published,source_url,now=None):
    now=utc(now or datetime.now(timezone.utc));published=utc(published)
    if not isinstance(xml,(str,bytes)) or len(xml)>MAX_XML_BYTES:
        raise ValueError('Invalid ownership XML')
    root=ET.fromstring(xml)
    if root.tag.rsplit('}',1)[-1]!='ownershipDocument':
        raise ValueError('Not an SEC ownershipDocument XML')
    owner_list=children(root,'reportingOwner')
    owners=[field(o,'reportingOwnerId/rptOwnerName') for o in owner_list]
    owner=', '.join(o for o in owners if o)[:90] or 'reporting person unnamed'
    if not children(root,'nonDerivativeTable'):
        return []
    out=[]
    for table in children(root,'nonDerivativeTable'):
        for idx,tx in enumerate(children(table,'nonDerivativeTransaction')):
            code=field(tx,'transactionCoding/transactionCode')
            acquired=field(tx,'transactionAmounts/transactionAcquiredDisposedCode/value')
            if (code,acquired) not in {('P','A'),('S','D')}:continue
            txn_date=field(tx,'transactionDate/value')
            try:
                when=datetime.strptime(txn_date,'%Y-%m-%d').date()
            except (TypeError,ValueError):continue
            if when>published.date() or when>now.date():continue
            shares=field(tx,'transactionAmounts/transactionShares/value')
            price=field(tx,'transactionAmounts/transactionPricePerShare/value')
            if not shares:continue
            try:
                sh=float(shares)
                px=float(price) if price is not None else None
            except ValueError:continue
            if not 0<sh<1e12 or px is not None and not 0<=px<1e9:continue
            act='purchase' if code=='P' else 'sale'
            note=(f'SEC Form 4 reports {owner} {act} of {sh:,.4g} non-derivative shares '
                  f'of {symbol} on transaction date {when.isoformat()}.'
                  f' Price: ${px:,.4g}/share.' if px is not None else
                  f'SEC Form 4 reports {owner} {act} of {sh:,.4g} non-derivative shares '
                  f'of {symbol} on transaction date {when.isoformat()}; price unspecified.')
            note += (f' SEC filing accepted {published.isoformat()}; filing may be delayed or amended. '
                     'Reported transaction is not live order flow and is NOT a predictive trade signal.')
            out.append({'asset':symbol,'asset_class':'stock','source':'insider',
                  'direction':'neutral','strength':0.5,
                  'event_id':f'sec-form4-txn:{cik}:{accession}:{idx}:{when.isoformat()}:{code}',
                  'observed_at':now.isoformat(),'published_at':published.isoformat(),
                  'source_url':source_url,'summary':note[:1200]})
    return out


def extract_form4_links(cik, submissions, now, max_filings=12):
    r=((submissions.get('filings') or {}).get('recent') or {})
    forms=r.get('form') or []; acc=r.get('accessionNumber') or []; docs=r.get('primaryDocument') or []
    dates=r.get('filingDate') or []; accepted=r.get('acceptanceDateTime') or []
    if not (len(forms)==len(acc)==len(docs)==len(dates)) or len(accepted) not in (0,len(forms)):
        raise ValueError('Misaligned SEC submissions')
    out=[]
    for i,form in enumerate(forms):
        if form!='4':continue # no silent double count of amendments
        accession=acc[i];doc=docs[i]
        if not isinstance(accession,str) or not ACCESSION_RE.fullmatch(accession):continue
        if not isinstance(doc,str) or not DOCUMENT_RE.fullmatch(doc) or not doc.lower().endswith('.xml'):
            continue
        try:published,_=accepted_time(accepted[i] if accepted else None,dates[i])
        except (ValueError,TypeError):continue
        if published>now or now-published>timedelta(days=7):continue
        url=EDGAR_ARCHIVES+str(int(cik))+'/'+accession.replace('-','')+'/'+doc
        out.append((accession,published,url))
        if len(out)>=max_filings:break
    return out


def run(watchlist, *, user_agent=None, now=None, opener=urlopen, pause_seconds=1.0):
    watchlist=validate_watchlist(watchlist)
    if not watchlist:return [],[]
    user_agent=user_agent or os.getenv('SEC_USER_AGENT','')
    if not re.search(r'[^\s@]+@[^\s@]+\.[^\s@]+',user_agent):
        return [],[{'provider':'sec_form4','reason':'missing_valid_SEC_USER_AGENT'}]
    now=utc(now or datetime.now(timezone.utc))
    items=[];issues=[]
    for i,item in enumerate(watchlist):
        if i and pause_seconds:time.sleep(pause_seconds)
        try:
            submissions=get_submissions(item['cik'],user_agent,opener=opener)
            for accession,published,url in extract_form4_links(item['cik'],submissions,now):
                if pause_seconds:time.sleep(pause_seconds)
                try:
                    xml=get_xml(url,user_agent,opener=opener)
                    items.extend(parse_form4_xml(xml,symbol=item['symbol'],cik=item['cik'],
                        accession=accession,published=published,source_url=url,now=now))
                except Exception as exc:
                    issues.append({'provider':'sec_form4','symbol':item['symbol'],
                                   'reason':type(exc).__name__+': '+str(exc)[:180]})
        except Exception as exc:
            issues.append({'provider':'sec_form4','symbol':item['symbol'],
                           'reason':type(exc).__name__+': '+str(exc)[:180]})
    return items,issues
