"""Local-only manual short-interest review. No redistribution or live signals.

Input CSV must be user-authorized published short *positions* with matching
publication dates, float and daily-volume estimates. NOT FINRA daily short
SALE volume, which is distinct from short interest. No API ingests this data.
"""
import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

REQUIRED = ('symbol','as_of','published_at','short_shares','float_shares','avg_daily_volume','source_url')


def row_metrics(row, *, today=None):
    today=today or date.today()
    if not isinstance(row,dict): raise ValueError('Invalid CSV row')
    symbol=str(row.get('symbol','')).strip().upper()
    if not (1<=len(symbol)<=12 and all(c.isupper() or c.isdigit() or c=='.' for c in symbol)):
        raise ValueError('Invalid symbol')
    as_of=date.fromisoformat(str(row['as_of']).strip())
    published=date.fromisoformat(str(row['published_at']).strip())
    if as_of>published or published>today: raise ValueError('Invalid dates')
    parsed=urlparse(str(row.get('source_url','')).strip())
    if parsed.scheme!='https' or not parsed.hostname: raise ValueError('Published source URL must be HTTPS')
    values={}
    for field in ('short_shares','float_shares','avg_daily_volume'):
        raw = str(row.get(field,'')).strip().replace(',','')
        n=float(raw)
        if not math.isfinite(n) or n<0 or (field!='short_shares' and n==0):
            raise ValueError('Invalid '+field)
        values[field]=n
    short_pct=values['short_shares']/values['float_shares']*100
    dtc=values['short_shares']/values['avg_daily_volume']
    # Reported short interest can exceed estimated tradable float; do not
    # discard such cases, but flag a possible data-definition mismatch.
    age=(today-published).days
    snapshot_age=(today-as_of).days
    # A WATCH label is a descriptive screen, not estimated squeeze probability.
    label=('stale_publication' if age>21 else
           'stale_snapshot' if snapshot_age>35 else
           'review_conditions' if short_pct>=15 and dtc>=3 else 'monitor')
    return {'symbol':symbol,'as_of':as_of.isoformat(),'published_at':published.isoformat(),
            'publication_age_days':age,'snapshot_age_days':snapshot_age,
            'short_exceeds_estimated_float':short_pct>100,'short_float_percent':round(short_pct,2),
            'days_to_cover':round(dtc,2),'screen_label':label,
            'source_url':str(row['source_url']).strip(),
            'interpretation':'Reported short positions divided by float and average daily volume. Not a squeeze prediction.',
            'redistribution':'local_review_only'}


def review_csv(path, *, today=None, max_rows=1000):
    path=Path(path)
    if path.stat().st_size>2_000_000: raise ValueError('CSV too large')
    with path.open(encoding='utf-8-sig',newline='') as file:
        reader=csv.DictReader(file)
        if not reader.fieldnames or not set(REQUIRED).issubset(reader.fieldnames):
            raise ValueError('CSV missing required short interest columns')
        result=[]
        for i,row in enumerate(reader):
            if i>=max_rows: raise ValueError('Maximum row count exceeded')
            result.append(row_metrics(row,today=today))
    return sorted(result,key=lambda x:(x['screen_label']!='review_conditions',-x['short_float_percent']))


def main():
    p=argparse.ArgumentParser(description='Local short-interest research, NOT daily short sale volume')
    p.add_argument('csv_file',help='Manually authorized short interest positions CSV')
    args=p.parse_args()
    print(json.dumps({'mode':'local_review_only','results':review_csv(args.csv_file)},indent=2))

if __name__=='__main__':main()
