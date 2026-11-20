"""Point-in-time evidence eligibility and auditable directional fusion.

Evidence is usable only if it was both published AND ingested by the decision
time. Provenance missing or delayed -> excluded. Never a probability model.
"""
from datetime import datetime, timezone
import math

ALLOWED_SOURCES=frozenset({"news","social","filing","insider","institutional",
                            "politician","options_flow","macro","short_interest",
                            "onchain","liquidity","dark_pool"})
MAX_AGE_HOURS=168


def epoch_ms(value):
    if isinstance(value,datetime):
        stamp=value
    elif isinstance(value,str):
        try:
            stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
        except ValueError:
            return None
    else:
        return None
    if stamp.tzinfo is None:return None
    return int(stamp.astimezone(timezone.utc).timestamp()*1000)


def available_evidence(observations, *, as_of_ms, symbol, asset_class,
                       max_age_hours=MAX_AGE_HOURS):
    """Return information that was truly observable at the historical cutoff.

    Historical snapshots without an original collection/observation timestamp
    cannot be reconstructed from publication timestamps alone.
    """
    if type(as_of_ms) is not int or as_of_ms<=0:
        raise ValueError("Invalid decision timestamp")
    if not 1<=max_age_hours<=168:
        raise ValueError("Invalid historical lookback")
    if not isinstance(observations,list) or len(observations)>5000:
        raise ValueError("Bounded research observations required")
    eligible=[]
    rejected={"future_or_missing_observation_time":0,
              "invalid_publication_time":0,"wrong_market":0,
              "stale_or_unsupported":0}
    # Deduplicate before scoring; select the most recent accepted observation
    # per source/event_id. Event IDs must be nonempty to avoid junk duplicates.
    seen=set()
    for o in observations:
        if not isinstance(o,dict):
            rejected["stale_or_unsupported"]+=1;continue
        if o.get("asset")!=symbol or o.get("asset_class")!=asset_class:
            rejected["wrong_market"]+=1;continue
        src=o.get("source")
        if src not in ALLOWED_SOURCES or o.get("direction") not in ("bullish","bearish","neutral"):
            rejected["stale_or_unsupported"]+=1;continue
        observed=epoch_ms(o.get("observed_at"))
        published=epoch_ms(o.get("published_at"))
        if observed is None or observed>as_of_ms or observed<=0:
            rejected["future_or_missing_observation_time"]+=1;continue
        if published is None or published>observed or published<=0:
            rejected["invalid_publication_time"]+=1;continue
        if as_of_ms-observed>max_age_hours*3600*1000:
            rejected["stale_or_unsupported"]+=1;continue
        event=o.get("event_id")
        if not isinstance(event,str) or not event.strip():
            rejected["stale_or_unsupported"]+=1;continue
        try:
            strength=float(o.get("strength",0))
        except (TypeError,ValueError,OverflowError):
            rejected["stale_or_unsupported"]+=1;continue
        if not math.isfinite(strength) or not 0<=strength<=1:
            rejected["stale_or_unsupported"]+=1;continue
        key=(src,event)
        if key in seen:continue
        seen.add(key)
        eligible.append({"source":src,"event_id":event,
                         "direction":o["direction"],"strength":strength,
                         "observed_ms":observed,"published_ms":published,
                         "age_hours":round((as_of_ms-observed)/3600000,3)})
    return eligible,rejected


def fixed_fusion(technical, eligible):
    """Predeclared research-only rule, not learned weights or calibrated AI.

    Require >=2 different independently observed *directional categories* to
    agree with a non-WAIT technical signal. One category cannot veto/approve
    regardless of article count. Mixed evidence -> WAIT.
    """
    tech=technical.get("buy_sell","WAIT")
    if tech not in ("RESEARCH_BULLISH","RESEARCH_BEARISH"):
        return "WAIT"
    agree="bullish" if tech=="RESEARCH_BULLISH" else "bearish"
    opposing="bearish" if agree=="bullish" else "bullish"
    supporters={o["source"] for o in eligible
                if o["direction"]==agree and o["strength"]>=.3}
    contradictors={o["source"] for o in eligible
                   if o["direction"]==opposing and o["strength"]>=.3}
    if len(supporters)>=2 and not contradictors:
        return tech
    return "WAIT"
