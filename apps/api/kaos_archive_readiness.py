"""KAOS bounded archival research readiness audit.

Metadata-only classification; no training, provider requests or invented
market history. Use for planning owner-only model evaluation.
"""
from collections import Counter
from datetime import datetime,timezone
from math import isfinite
from kaos_point_in_time import epoch_ms,ALLOWED_SOURCES

def inspect_market(candles,observations,*,symbol,asset_class,seconds,now_ms=None):
    if now_ms is None:now_ms=int(datetime.now(timezone.utc).timestamp()*1000)
    if not isinstance(candles,list) or len(candles)>10000:
        raise ValueError("Bounded candles required")
    if not isinstance(observations,list) or len(observations)>5000:
        raise ValueError("Bounded observations required")
    if type(seconds) is not int or seconds<=0 or type(now_ms) is not int or now_ms<=0:
        raise ValueError("Invalid interval or timestamp")
    feed_counts=Counter()
    invalid=0;open_bars=0;timestamps=[];valid=[]
    for c in candles:
        if not isinstance(c,dict) or c.get("symbol")!=symbol or c.get("asset_class")!=asset_class or c.get("seconds")!=seconds:
            invalid+=1;continue
        source=c.get("source")
        stamp=c.get("ts")
        if not isinstance(source,str) or not source or type(stamp) is not int or stamp<=0:
            invalid+=1;continue
        try:
            o,h,l,cl=(float(c[k]) for k in ("open","high","low","close"))
        except (KeyError,ValueError,TypeError,OverflowError):
            invalid+=1;continue
        if not all(isfinite(v) and v>0 for v in (o,h,l,cl)) or l>min(o,cl) or h<max(o,cl):
            invalid+=1;continue
        if stamp+seconds*1000>now_ms:
            open_bars+=1;continue
        feed_counts[source]+=1
        valid.append(c);timestamps.append(stamp)
    duplicate=len(timestamps)-len(set(timestamps))
    mixed_sources=len(feed_counts)!=1
    recent=sorted(valid,key=lambda r:r["ts"])
    gaps=sum(b["ts"]-a["ts"]!=seconds*1000 for a,b in zip(recent,recent[1:]))
    # Gap-free runs, rather than total bar count, determine if interval-based
    # lookbacks and forward outcomes are usable at all.
    runs=[]
    current=0;last=None
    for row in recent:
        if last is None or row["ts"]-last==seconds*1000:
            current+=1
        else:
            runs.append(current);current=1
        last=row["ts"]
    if current:runs.append(current)
    eligible=Counter();late=0;bad_evidence=0
    earliest=recent[0]["ts"] if recent else now_ms
    latest=recent[-1]["ts"]+seconds*1000 if recent else now_ms
    for item in observations:
        if not isinstance(item,dict) or item.get("asset")!=symbol or item.get("asset_class")!=asset_class:
            continue
        source=item.get("source")
        published=epoch_ms(item.get("published_at"))
        observed=epoch_ms(item.get("observed_at"))
        if source not in ALLOWED_SOURCES or observed is None or published is None or published>observed:
            bad_evidence+=1;continue
        if observed>latest:
            late+=1;continue
        if observed>=earliest and observed<=latest:
            eligible[source]+=1
    longest=max(runs,default=0)
    # 80-bar context plus minimum 100 nonoverlapping horizon-5 decisions
    # would require far more contiguous bars; this audit intentionally
    # reports only technical preconditions, not a trained-model guarantee.
    enough=longest>=700 and invalid==0 and duplicate==0 and not mixed_sources
    return {"symbol":symbol,"asset_class":asset_class,"seconds":seconds,
        "total_archive_rows":len(candles),"valid_closed_rows":len(valid),
        "invalid_rows":invalid,"unfinished_rows":open_bars,
        "duplicate_timestamps":duplicate,"sources":dict(feed_counts),
        "mixed_sources":mixed_sources,"gaps":gaps,
        "longest_contiguous_run":longest,
        "first_bar_ms":recent[0]["ts"] if recent else None,
        "last_closed_bar_ms":latest if recent else None,
        "point_in_time_evidence_by_source":dict(eligible),
        "future_observed_records":late,"invalid_observation_time_records":bad_evidence,
        "technical_research_ready":enough,
        "multifactor_evidence_present":bool(eligible),
        "status":"technical_research_candidate" if enough else "archive_not_ready",
        "recommendation":"Owner-only offline testing permitted; check market sessions and license first" if enough else "Collect more clean, source-consistent archived candles and timestamped evidence",
        "research_only":True,"model_accuracy_known":False,
        "notes":"Audit only. Intraday stock overnight gaps require session-aware evaluation. Source rights and freshness not verified."}
