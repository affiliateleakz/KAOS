"""Read-only hosting readiness report. No keys, account documents or funds printed."""
from pathlib import Path
import sys

REQUIRED_INDEXES = {
    'webhook_events': 'event_id',
    'affiliate_ledger_payments': 'event_id',
    'affiliate_ledger_entries': 'entry_id',
    'affiliate_ledger_reversals': 'reversal_id',
    'affiliate_accounts': 'code',
}


def configuration_checks(config):
    return {
        'Stripe live membership key configured': (config.get('STRIPE_SECRET_KEY') or '').startswith('sk_live_'),
        'Stripe webhook signing secret configured': (config.get('STRIPE_WEBHOOK_SECRET') or '').startswith('whsec_'),
        'Stripe Connect live key configured': (config.get('STRIPE_CONNECT_SECRET_KEY') or '').startswith('sk_live_'),
        'Stripe Connect onboarding enabled': config.get('KAOS_STRIPE_CONNECT_ENABLED') == 'true',
        'Affiliate transaction mode required': config.get('KAOS_AFFILIATE_TXN_MODE') == 'required',
    }


def main():
    from dotenv import dotenv_values
    from pymongo import MongoClient
    root = Path.home() / 'tradingwithkaos.com/backend'
    config = dotenv_values(root / '.env')
    checks = configuration_checks(config)
    try:
        with MongoClient(config.get('MONGO_URL', ''), serverSelectionTimeoutMS=10000) as client:
            hello = client.admin.command('hello')
            checks['MongoDB supports transaction topology'] = bool(hello.get('setName') or hello.get('msg') == 'isdbgrid')
            database = client[config['DB_NAME']]
            for collection, field in REQUIRED_INDEXES.items():
                indexes = database[collection].index_information().values()
                checks[f'Unique {collection}.{field} index exists'] = any(
                    i.get('unique') is True and i.get('key') == [(field, 1)] for i in indexes)
    except Exception as exc:
        checks['Database readiness verified'] = False
        print('Database check unavailable (' + type(exc).__name__ + ')')
    entry = root / 'passenger_wsgi.py'
    checks['Hosting wrapper permits billing'] = entry.exists() and 'Login validation mode' not in entry.read_text()
    for name, ok in checks.items():
        print(('PASS: ' if ok else 'BLOCKED: ') + name)
    print('Read-only checks complete. Stripe platform approval, live webhook delivery, '
          'refund/reconciliation tests and payout release are separate launch requirements. '
          'This script does not activate payments or send transfers.')
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
