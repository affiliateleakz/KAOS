"""Stripe-authenticated subscription identity and paid-through dates; never guess duration."""
import math
from datetime import datetime,timezone
from fastapi import HTTPException


def identity(value):return value.get('id') if isinstance(value,dict) else value


def subscription_id(invoice):
    return identity(invoice.get('subscription')) or identity((invoice.get('parent') or {}).get('subscription_details',{}).get('subscription'))


def period_end(subscription):
    value=subscription.get('current_period_end')
    if value is None:
        items=(subscription.get('items') or {}).get('data',[])
        if len(items)!=1:raise HTTPException(503,'A single verified membership billing item is required')
        value=items[0].get('current_period_end')
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0:raise HTTPException(503,'Stripe billing period is unavailable; retry after reconciliation')
    return int(value)


def iso(stamp):return datetime.fromtimestamp(stamp,timezone.utc).isoformat()


def invoice_period_end(invoice,sub_id):
    lines=(invoice.get('lines') or {}).get('data',[])
    if (invoice.get('lines') or {}).get('has_more'):return None
    ends=[]
    for line in lines:
        parent=(line.get('parent') or {}).get('subscription_item_details',{})
        linked=identity(line.get('subscription')) or identity(parent.get('subscription'))
        recurring=line.get('type')=='subscription' or bool(parent)
        if linked and linked!=sub_id:continue
        if not recurring or line.get('proration') or parent.get('proration'):continue
        end=(line.get('period') or {}).get('end')
        if type(end) in (int,float) and math.isfinite(end) and end>0:ends.append(int(end))
    return ends[0] if len(ends)==1 else None
