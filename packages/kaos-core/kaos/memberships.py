"""Non-monetary preview ledger. Production payouts require compliance, tax, fraud and refund checks."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
RATES={'free':(10,0,0),'pro':(30,15,0),'ultimate':(50,25,5)}
PRICES={'free':Decimal('0'),'pro':Decimal('29.95'),'ultimate':Decimal('99.95')}
PERMISSIONS={'free':{'strategy'},'pro':{'strategy','scanners','ai_insights'},'ultimate':{'strategy','scanners','ai_insights','ai_execution'}}
@dataclass(frozen=True)
class Affiliate:
    id: str
    tier: str
    referrer: str|None = None

def calculate_referral_payouts(sale_amount, buyer_id, members):
    """Walk buyer -> direct sponsor -> sponsor sponsor; rate comes from each recipient's tier and generation."""
    base=Decimal(str(sale_amount))
    if base<0:raise ValueError('negative sale')
    if buyer_id not in members:raise KeyError(buyer_id)
    out=[]; current=members[buyer_id].referrer; seen={buyer_id}
    for generation in range(1,4):
        if not current: break
        if current in seen: raise ValueError('referral cycle')
        seen.add(current)
        aff=members[current]
        rate=RATES[aff.tier][generation-1]
        if rate:
            payout=(base*Decimal(rate)/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
            out.append({'affiliate_id':current,'level':generation,'rate_pct':rate,'amount':str(payout)})
        current=aff.referrer
    return out
