"""Owner-only configuration evidence. Read-only; never activates services or funds."""
import os,time,json
from pathlib import Path
from fastapi import APIRouter,Depends,Response
from auth import require_role
from db import db,now_iso
from routes_billing import get_plans
from stripe_runtime import availability
import commerce_providers
from mail_delivery import smtp_ready

router=APIRouter(prefix='/api/admin/launch',tags=['launch-readiness'])
owner=require_role('super_admin')


def check(key,title,state,detail,action,href):return {'id':key,'title':title,'state':state,'detail':detail,'action':action,'href':href}


def installed_release():
    path=Path(__file__).parent/'deployed_release.json'
    try:
        if path.stat().st_size>1000:return None
        data=json.loads(path.read_text())
        if not isinstance(data,dict):return None
        revision=data.get('revision','')
        if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):return None
        return {'revision':revision,'installedAt':str(data.get('installedAt',''))}
    except (OSError,ValueError,TypeError):return None


async def report():
    plans=await get_plans();stripe=await availability();provider=await commerce_providers.document('stripe')
    worker=await db.ai_worker_state.find_one({'_id':'continuous'},{'_id':0,'heartbeat':1}) or {}
    published=await db.ai_training_models.count_documents({'audience':'shared','state':'published','createdAtMs':{'$gt':(time.time()-30*86400)*1000}})
    events=await db.webhook_events.find({'state':'completed'},{'_id':0,'type':1,'livemode':1,'createdAt':1}).sort('createdAt',-1).limit(8).to_list(8)
    expected={'pro':2995,'pro_yearly':29995,'ultimate':9995,'ultimate_yearly':99595}
    prices={p['id']:p.get('amount') for p in plans if p.get('enabled',True)}
    pricing=all(prices.get(k)==v for k,v in expected.items())
    last=provider.get('lastCheck') or {};mode='live' if stripe['mode']=='live' else 'sandbox'
    connection=bool(stripe.get('configurationReady')) and last.get('ok') is True and last.get('mode')==mode
    smtp=smtp_ready()
    legacy_key=os.getenv('EMERGENT_EMAIL_KEY','');legacy_email=bool(legacy_key and not legacy_key.startswith('{'))
    google=bool(os.getenv('KAOS_GOOGLE_WEB_CLIENT_ID'))
    extension_google=bool(os.getenv('KAOS_GOOGLE_EXTENSION_CLIENT_ID'))
    checks=[
        check('plans','Membership catalog','configured' if pricing else 'needs_review','Current target: Free $0; Pro $29.95/month or $299.95/year; Ultimate $99.95/month or $995.95/year.','Review and save actual configured plans.','/admin/settings'),
        check('stripe_config','Stripe credentials','configured' if stripe.get('configurationReady') else 'blocked',stripe.get('note','Not configured'),'Save matching payments key and signing secret.','/admin/commerce'),
        check('stripe_connection','Stripe account connection','checked' if connection else 'unverified','A saved API check is not proof of a charge, webhook, renewal or refund.','Run the saved-environment connection check.','/admin/commerce'),
        check('checkout','Membership checkout','activated' if stripe['checkoutEnabled'] else 'blocked',stripe.get('note','Checkout disabled'),'Finish isolated sandbox testing before a billing-capable live deployment.','/admin/commerce'),
        check('email','Password recovery email','configured_unverified' if smtp or legacy_email else 'blocked','Configured does not mean delivery has been tested.','Configure secure SMTP in hosting settings, then test recovery with an owner-controlled account.','https://github.com/affiliateleakz/KAOS/blob/chatgpt/deepscan-critical-repairs-20261018/docs/BUSINESS_LAUNCH.md'),
        check('google','Google sign-in','configured_unverified' if google and extension_google else 'needs_review','Installed extension ID must remain gbobopmnjgeeegniphckfpalhnebapjm.','Verify website and official-extension sign-in after deployment.','/admin/extension'),
        check('worker','AI training worker','heartbeat_seen' if 0<=time.time()-worker.get('heartbeat',0)<900 else 'not_running','Website requests never start training. Worker hosting is still a separate owner decision.','Choose dedicated worker hosting before promising continuously running training.','/admin/kaos-ai'),
        check('models','Published pretrained models','available_unverified' if published else 'not_available','Experimental research artifacts are not production pretrained member models.','Validate models and their actual execution scope before publication.','/admin/kaos-ai'),
        check('payouts','Affiliate payout release','disabled','Commission accounting and provider setup do not mean real payouts are connected or enabled.','Verify hold/refund accounting, provider approval and payout reconciliation before release.','/admin/affiliates'),
    ]
    return {'checkedAt':now_iso(),'installedRelease':installed_release(),'checks':checks,'stripeMode':stripe['mode'],'recentProcessedWebhookEvidence':events,
            'publishedModels':published,'activationPerformed':False,'launchCertified':False,
            'notice':'Read-only configuration evidence, not an end-to-end launch certification. No payments, payouts, emails, trading or workers are started by this page.',
            'externalChecks':['Isolated Stripe sandbox checkout, duplicate delivery, renewal, failure, cancellation, refund and dispute reconciliation.','Owner-controlled password-reset delivery and session restore.','Installed Chrome extension Google sign-in and broker chart feed; store submission/review.','Provider account approvals and verified live configuration.','Deploy this exact tested release, restart Passenger and verify the hosted flows.']}


@router.get('/readiness')
async def readiness(response:Response,user=Depends(owner)):
    response.headers['Cache-Control']='private, no-store'
    return await report()
