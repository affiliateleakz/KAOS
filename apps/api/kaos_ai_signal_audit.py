"""KAOS AI shadow forecast evaluator: chronological, provenance-aware and read-only.

Only forecasts issued before outcome timestamp are eligible; duplicates, simulated
forecasts and unverified results never count toward reported accuracy.
"""
from collections import defaultdict
from datetime import datetime,timezone
from math import sqrt

def parse_time(v):
    if isinstance(v,str):v=datetime.fromisoformat(v.replace("Z","+00:00"))
    if not isinstance(v,datetime) or v.tzinfo is None:raise ValueError("timezone-aware timestamp required")
    return v.astimezone(timezone.utc)

def wilson(w,n,z=1.96):
    if not n:return None
    p=w/n; d=1+z*z/n
    return round(100*(p+z*z/(2*n)-z*sqrt((p*(1-p)+z*z/(4*n))/n))/d,2)

def assess(rows):
    results=defaultdict(lambda:{"wins":0,"losses":0,"ties":0})
    seen=set();skipped=defaultdict(int)
    for row in sorted(rows,key=lambda r:str(r.get("issued_at",""))):
        try:
            ident=str(row["prediction_id"])
            if not ident or ident in seen:
                skipped["duplicate"]+=1;continue
            seen.add(ident)
            if row.get("simulated") or not row.get("production_trained"):
                skipped["not_trained"]+=1;continue
            issued=parse_time(row["issued_at"]);settled=parse_time(row["outcome_at"])
            if issued>=settled:
                skipped["timestamp_invalid"]+=1;continue
            if row.get("outcome_verified") is not True:
                skipped["not_verified"]+=1;continue
            direction=str(row["direction"]).upper()
            outcome=str(row["outcome"]).upper()
            if direction not in ("BUY","SELL") or outcome not in ("WIN","LOSS","TIE"):
                skipped["invalid_label"]+=1;continue
            market=str(row.get("asset","UNKNOWN")).upper()[:60]
            model=str(row.get("model_version","unknown"))[:80]
            bucket=results[(model,market)]
            bucket[{"WIN":"wins","LOSS":"losses","TIE":"ties"}[outcome]]+=1
        except (KeyError,TypeError,ValueError,OverflowError):
            skipped["invalid_record"]+=1
    groups=[]
    for (version,asset),counts in sorted(results.items()):
        n=counts["wins"]+counts["losses"]
        groups.append({"model_version":version,"asset":asset,**counts,"decisive_samples":n,
          "win_rate_ex_ties":round(100*counts["wins"]/n,2) if n else None,
          "win_rate_lower_95":wilson(counts["wins"],n),
          "performance_validated":n>=100,
          "warning":"Historical forecast accuracy, not trade profitability or guaranteed results"})
    return {"groups":groups,"excluded":dict(skipped),"execution_enabled":False,"research_only":True}
