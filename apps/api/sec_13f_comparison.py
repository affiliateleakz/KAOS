"""Compare two publicly reported SEC 13F holdings snapshots.

A difference is a net reported holding change, not a known executed transaction.
"""
from decimal import Decimal,InvalidOperation

def compare_holdings(previous, current):
    def index(rows):
        out={}
        for row in rows:
            cusip=str(row["cusip"]).upper()
            if cusip in out: raise ValueError("Duplicate CUSIP in a filing")
            try:
                shares=Decimal(str(row["reported_shares_or_principal"]))
            except (InvalidOperation,TypeError) as exc:
                raise ValueError("Reported share count unavailable") from exc
            if not shares.is_finite() or shares<0:raise ValueError("Invalid holding quantity")
            out[cusip]=(shares,row["issuer"])
        return out
    before=index(previous);after=index(current)
    result=[]
    for cusip in sorted(before.keys()|after.keys()):
        old=before.get(cusip,(Decimal(0),""))[0]
        new=after.get(cusip,(Decimal(0),""))[0]
        if old==new:continue
        result.append({"cusip":cusip,"issuer":after.get(cusip,before.get(cusip))[1],
            "previous_reported_shares":str(old),"latest_reported_shares":str(new),
            "net_reported_change":str(new-old),
            "change":"increase" if new>old else "decrease",
            "interpretation":"quarterly_holdings_difference_not_confirmed_trade"})
    return result
