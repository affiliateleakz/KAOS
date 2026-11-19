"""Secure SMTP for application mail. No plaintext authentication or credential logging."""
import asyncio,os,smtplib,ssl,logging
from email.message import EmailMessage
from email.utils import parseaddr

log=logging.getLogger(__name__)


def smtp_configuration():
    required=('SMTP_HOST','SMTP_USER','SMTP_PASSWORD','SMTP_FROM')
    if not all(os.getenv(k) for k in required):raise ValueError('SMTP settings incomplete')
    port=int(os.getenv('SMTP_PORT','465'));security=os.getenv('SMTP_SECURITY','ssl' if port==465 else 'starttls').lower()
    if security not in ('ssl','starttls') or not 1<=port<=65535:raise ValueError('Secure SMTP is required')
    sender=os.environ['SMTP_FROM']
    if any(c in sender for c in '\r\n') or '@' not in parseaddr(sender)[1]:raise ValueError('Invalid sender address')
    return {'host':os.environ['SMTP_HOST'],'port':port,'user':os.environ['SMTP_USER'],'password':os.environ['SMTP_PASSWORD'],'sender':sender,'security':security}


def smtp_ready():
    try:smtp_configuration();return True
    except (ValueError,KeyError):return False


def _send(config,to,subject,html):
    message=EmailMessage();message['From']=config['sender'];message['To']=to;message['Subject']=subject;message.set_content('A KAOS account action was requested. Open the HTML message to use its link.');message.add_alternative(html,subtype='html')
    context=ssl.create_default_context()
    if config['security']=='ssl':connection=smtplib.SMTP_SSL(config['host'],config['port'],timeout=10,context=context)
    else:connection=smtplib.SMTP(config['host'],config['port'],timeout=10)
    with connection as client:
        if config['security']=='starttls':client.ehlo();client.starttls(context=context);client.ehlo()
        client.login(config['user'],config['password']);client.send_message(message)


async def send_smtp(to,subject,html):
    try:await asyncio.to_thread(_send,smtp_configuration(),to,subject,html);return True
    except Exception as exc:
        log.error('SMTP delivery failed (%s)',type(exc).__name__)
        return False


def account_mail_ready():
    key=os.getenv('EMERGENT_EMAIL_KEY','')
    return os.getenv('FRONTEND_URL','').startswith('https://') and (smtp_ready() or bool(key and not key.startswith('{')))


async def send_account_email(to,subject,html):
    """Transactional account mail only; no password/credential data in logs."""
    if smtp_ready():return await send_smtp(to,subject,html)
    key=os.getenv('EMERGENT_EMAIL_KEY','')
    if not key or key.startswith('{'):return False
    import httpx
    base=os.getenv('INTEGRATION_PROXY_URL','').rstrip('/') or 'https://integrations.emergentagent.com'
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            result=await client.post(base+'/api/v1/email/send',headers={'X-Email-Key':key},
                json={'to':[to],'subject':subject,'html':html,'from_name':'KAOS Trading'})
            result.raise_for_status()
        return True
    except Exception as exc:
        log.error('Account email delivery failed (%s)',type(exc).__name__)
        return False
