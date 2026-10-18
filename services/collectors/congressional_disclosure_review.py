"""Local-only congressional financial disclosure review, not a paid feed.

Public House disclosure documents are subject to use restrictions, including
commercial-use limitations; this module NEVER uploads or republishes filings.
Rows must be manually checked against original reports; no inferred trades.
"""
import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

OFFICIAL_HOSTS={'disclosures-clerk.house.gov','clerk.house.gov','efd.senate.gov','senate.gov'}
COLUMNS={'report_id','chamber','member','ticker','asset_description','transaction_type',
         'transaction_date','filing_date','amount_range','source_url'}
TRANSACTION_TYPES={'purchase','sale','exchange','unknown'}
TICKER=re.compile(r'^[A-Z][A-Z0-9.\-]{0,11}$')

def inspect_row(row, *, today=None):
    today=today or date.today()
    errors=[]
    missing=COLUMNS-set(row)
    if missing:raise ValueError('CSV missing columns: '+', '.join(sorted(missing)))
    result={key:str(row.get(key) or '').strip() for key in COLUMNS}
    chamber=result['chamber'].lower()
    if chamber not in ('house','senate'):errors.append('chamber_not_valid')
    ttype=result['transaction_type'].lower()
    if ttype not in TRANSACTION_TYPES:errors.append('transaction_type_not_valid')
    if not result['member'] or len(result['member'])>160:errors.append('member_missing_or_long')
    if not result['report_id'] or len(result['report_id'])>100:errors.append('report_id_missing_or_long')
    if not result['asset_description'] or len(result['asset_description'])>180:errors.append('asset_description_missing_or_long')
    if result['ticker'] and not TICKER.fullmatch(result['ticker']):errors.append('ticker_not_valid')
    try:
        trans_date=date.fromisoformat(result['transaction_date'])
        if trans_date>today:errors.append('transaction_date_in_future')
    except ValueError:errors.append('transaction_date_not_valid');trans_date=None
    try:
        filing_date=date.fromisoformat(result['filing_date'])
        if filing_date>today:errors.append('filing_date_in_future')
        if trans_date and filing_date<trans_date:errors.append('filing_predates_transaction')
    except ValueError:errors.append('filing_date_not_valid');filing_date=None
    url=urlsplit(result['source_url'])
    if url.scheme!='https' or url.hostname not in OFFICIAL_HOSTS or url.username or url.password:
        errors.append('not_an_official_source_url')
    result['chamber']=chamber
    result['transaction_type']=ttype
    result['disclosure_lag_days']=(filing_date-trans_date).days if filing_date and trans_date else None
    # No source inference and no representation of exact traded dollars.
    return {'valid':not errors,'errors':errors,'review':result,
            'permitted_for_paid_member_distribution':False,'verified_against_original':False}


def inspect_file(path, *, today=None, max_rows=5000):
    path=Path(path)
    if path.stat().st_size>2_000_000:raise ValueError('CSV file exceeds 2MB')
    with path.open('r',encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames is None or COLUMNS-set(reader.fieldnames):
            raise ValueError('CSV missing required column headers')
        results=[]
        for i,row in enumerate(reader,1):
            if i>max_rows:raise ValueError('Row limit exceeded')
            results.append({'line':i+1,**inspect_row(row,today=today)})
    return {'mode':'local_review_only','rows':len(results),
            'valid_rows':sum(r['valid'] for r in results),
            'commercial_republication':False,'records':results}


def main():
    p=argparse.ArgumentParser(description='KAOS local congressional disclosure review only')
    p.add_argument('csv_file',help='Curated CSV of manually reviewed official documents')
    p.add_argument('--output',help='Save local JSON review report')
    args=p.parse_args()
    review=inspect_file(args.csv_file)
    serialized=json.dumps(review,indent=2,ensure_ascii=False)
    if args.output:Path(args.output).write_text(serialized+'\n',encoding='utf-8')
    else:print(serialized)

if __name__=='__main__':main()
