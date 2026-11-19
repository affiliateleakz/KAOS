"""Run the Coinbase execution worker independently of AI training and Passenger.

--check validates local configuration only; it never contacts a broker or database.
Secrets must be supplied privately by the process supervisor, not command arguments.
"""
import argparse
import asyncio
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def configuration_errors(env):
    errors = []
    for name in ('MONGO_URL', 'DB_NAME', 'KAOS_BROKER_VAULT_KEY'):
        if not env.get(name, '').strip():
            errors.append(name + ' is required')
    for name in ('KAOS_COINBASE_AUTO_WORKER', 'KAOS_COINBASE_LIVE_ORDERS'):
        if env.get(name) != 'enabled':
            errors.append(name + ' must be enabled')
    mongo = env.get('MONGO_URL', '')
    if mongo and not mongo.startswith(('mongodb://', 'mongodb+srv://')):
        errors.append('MONGO_URL must use a MongoDB connection scheme')
    origin = urlsplit(env.get('KAOS_COINBASE_CONTROL_ORIGIN', 'https://api.tradingwithkaos.com'))
    if (origin.scheme != 'https' or not origin.hostname or origin.username or origin.password
            or origin.path not in ('', '/') or origin.query or origin.fragment):
        errors.append('KAOS_COINBASE_CONTROL_ORIGIN must be an HTTPS origin')
    if env.get('KAOS_BROKER_VAULT_KEY'):
        from cryptography.fernet import Fernet
        keys = [env['KAOS_BROKER_VAULT_KEY']] + [k.strip() for k in env.get('KAOS_BROKER_VAULT_PREVIOUS_KEYS', '').split(',') if k.strip()]
        try:
            for key in keys:
                Fernet(key.encode())
        except (ValueError, TypeError):
            errors.append('Broker vault key format is invalid')
    if env.get('KAOS_COINBASE_MAX_ORDER_USD'):
        from decimal import Decimal, InvalidOperation
        try:
            amount = Decimal(env['KAOS_COINBASE_MAX_ORDER_USD'])
            if not amount.is_finite() or amount <= 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            errors.append('KAOS_COINBASE_MAX_ORDER_USD must be finite and positive')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    errors = configuration_errors(os.environ)
    if errors:
        raise SystemExit('Coinbase execution configuration incomplete:\n' + '\n'.join(errors))
    if args.check:
        print('Local Coinbase execution configuration valid. Broker, database, API and worker readiness are not verified. No orders placed.')
        return
    for path in (ROOT / 'apps/api', ROOT / 'packages/kaos-core'):
        sys.path.insert(0, str(path))
    from coinbase_auto_worker import main as run_worker
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
