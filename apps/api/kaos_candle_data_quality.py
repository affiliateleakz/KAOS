"""Closed-candle dataset audit and chronological split for offline KAOS AI research."""
from math import isfinite

def audit_candles(rows, seconds):
    if seconds not in (60,300,900):raise ValueError("Unsupported timeframe")
    clean=[]; seen=set(); invalid=0; duplicates=0
    for row in sorted(rows,key=lambda r:r.get("ts",0)):
        try:
            ts=int(row["ts"])
            values=[float(row[k]) for k in ("open","high","low","close","volume")]
            o,h,l,c,v=values
            valid=(ts>0 and ts%(seconds*1000)==0 and all(isfinite(x) for x in values)
              and min(o,h,l,c)>0 and v>=0 and l<=min(o,c)<=max(o,c)<=h)
            if not valid:invalid+=1;continue
            if ts in seen:duplicates+=1;continue
            seen.add(ts);clean.append(row)
        except (KeyError,TypeError,ValueError,OverflowError):
            invalid+=1
    gaps=[]
    for previous,current in zip(clean,clean[1:]):
        delta=int(current["ts"])-int(previous["ts"])
        if delta>seconds*1000:
            gaps.append({"after":int(previous["ts"]),"before":int(current["ts"]),
                         "missing_intervals":delta//(seconds*1000)-1})
    return {"total":len(rows),"usable":len(clean),"invalid":invalid,
            "duplicates":duplicates,"gaps":gaps,
            "missing_intervals":sum(g["missing_intervals"] for g in gaps),"candles":clean}

def chronological_split(rows,train_fraction=0.7,validation_fraction=0.15):
    if not (0<train_fraction<1 and 0<validation_fraction<1
            and train_fraction+validation_fraction<1):
        raise ValueError("Invalid split fractions")
    ordered=sorted(rows,key=lambda x:int(x["ts"]))
    n=len(ordered);a=int(n*train_fraction);b=int(n*(train_fraction+validation_fraction))
    return {"train":ordered[:a],"validation":ordered[a:b],"test":ordered[b:]}
