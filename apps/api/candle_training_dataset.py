"""Research dataset preparation with chronological splits and horizon labels.

Never trains or trades. Prices stay grouped by asset class, symbol, timeframe,
and source; gaps are excluded rather than silently joined.
"""
from math import isfinite

def prepare(candles, horizon_bars=1, train_fraction=.7, validation_fraction=.15):
    if not isinstance(horizon_bars,int) or horizon_bars<1 or horizon_bars>30:
        raise ValueError("Invalid horizon")
    if not (0.5<=train_fraction<=0.8 and 0.1<=validation_fraction<=0.25 and train_fraction+validation_fraction<=.9):
        raise ValueError("Invalid split")
    groups={}
    for c in candles:
        key=(c["asset_class"],c["symbol"],c["seconds"],c["source"])
        groups.setdefault(key,[]).append(c)
    result=[]
    for key,records in sorted(groups.items()):
        rows=sorted(records,key=lambda x:x["ts"])
        unique={x["ts"]:x for x in rows}
        rows=[unique[t] for t in sorted(unique)]
        n=len(rows)
        train_end=int(n*train_fraction);val_end=int(n*(train_fraction+validation_fraction))
        for i in range(n-horizon_bars):
            j=i+horizon_bars
            # Exclude temporal gaps and ensure targets never cross split boundaries.
            if any(rows[k+1]["ts"]-rows[k]["ts"]!=rows[k]["seconds"]*1000 for k in range(i,j)):
                continue
            split="train" if j<train_end else "validation" if i>=train_end and j<val_end else "test" if i>=val_end else None
            if split is None:continue
            start,end=rows[i],rows[j]
            a,b=float(start["close"]),float(end["close"])
            if not all(isfinite(x) and x>0 for x in (a,b)):continue
            result.append({"asset_class":key[0],"symbol":key[1],"seconds":key[2],
              "source":key[3],"at":start["ts"],"target_at":end["ts"],"split":split,
              "close":a,"return":round(b/a-1,10),"label":"UP" if b>a else "DOWN" if b<a else "FLAT"})
    return result
