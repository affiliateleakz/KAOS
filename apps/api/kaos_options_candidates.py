"""KAOS research-only listed-options liquidity and scenario candidate screening.

Uses actual option-chain records. No model forecast, EV estimate, or trade
recommendation is inferred from a direction-only technical alignment index.
"""
import math
from datetime import date,datetime,timezone

def screen(underlying,expiration,records,*,bias="unknown",asof=None,sandbox=True,limit=8):
    if not isinstance(records,list) or len(records)>10000:
        raise ValueError("Invalid option-chain size")
    if not isinstance(underlying,str) or not underlying:
        raise ValueError("Missing underlying")
    try: expiry=date.fromisoformat(expiration)
    except (ValueError,TypeError) as exc: raise ValueError("Invalid option expiration") from exc
    asof=asof or datetime.now(timezone.utc)
    if asof.tzinfo is None:raise ValueError("Timestamp must be timezone-aware")
    if expiry<asof.date():raise ValueError("Expired contract")
    if bias not in ("bullish","bearish","mixed","unknown"):raise ValueError("Invalid market bias")
    if type(limit) is not int or not 1<=limit<=20:raise ValueError("Invalid limit")
    chosen=[]
    for item in records:
        if not isinstance(item,dict):continue
        right=str(item.get("option_type","")).lower()
        contract=str(item.get("symbol","")).upper()
        if right not in ("call","put") or not contract or len(contract)>45:
            continue
        try:
            bid,ask,strike=(float(item[k]) for k in ("bid","ask","strike"))
            volume=int(item.get("volume") or 0)
            oi=int(item.get("open_interest") or 0)
        except (KeyError,TypeError,ValueError,OverflowError):continue
        if (not all(math.isfinite(n) for n in (bid,ask,strike)) or
                bid<=0 or ask<bid or strike<=0 or volume<0 or oi<0):continue
        mid=(ask+bid)/2
        spread=(ask-bid)/mid
        if spread>.25 or volume<10 or oi<25:continue
        # A transparent liquidity-only ranking. No directional forecast weight
        # and no fabricated Greeks, IV, delta or probability of profit.
        liquidity=round(min(100.,30*min(1,volume/200)+
                              30*min(1,oi/1000)+40*(1-min(spread/.25,1))),2)
        chosen.append({"contract":contract,"right":right.upper(),
                       "strike":strike,"expiration":expiry.isoformat(),
                       "bid":bid,"ask":ask,"spread_pct":round(spread*100,2),
                       "volume":volume,"open_interest":oi,
                       "liquidity_score":liquidity,
                       "score_type":"liquidity_quality_only_not_buy_probability",
                       "matches_technical_bias":(right=="call" if bias=="bullish"
                                                  else right=="put" if bias=="bearish" else None)})
    chosen.sort(key=lambda r:(-r["liquidity_score"],r["spread_pct"],r["contract"]))
    return {"underlying":underlying,"expiration":expiry.isoformat(),
            "as_of":asof.isoformat(),"environment":"sandbox_delayed" if sandbox else "production_entitlement_dependent",
            "candidates":chosen[:limit],"eligible_contract_count":len(chosen),
            "status":"liquidity_screen_only" if chosen else "no_eligible_contracts",
            "call_put_recommendation":"NONE","recommended_expiration":None,
            "validated_forecast":False,"research_only":True,"orders_enabled":False,
            "note":"Actual listed contract quotes; liquidity ranking only. No validated direction, profit probability, or contract recommendation."}
