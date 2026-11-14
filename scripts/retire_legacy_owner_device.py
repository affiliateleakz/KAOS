"""Explicit hosting-operator recovery for the known obsolete owner/1.1.6 device.

Run with the existing cPanel Python environment. Never prints secrets, deletes
records, upgrades a plan, or authorizes the new installation. Normal extension
registration and licensing still apply after the old device is retired.
"""
import argparse
from pathlib import Path


def retire(database, apply=False):
    owners = list(database.users.find({'username': 'owner'}, {'id': 1}).limit(2))
    if len(owners) != 1 or not owners[0].get('id'):
        raise ValueError('Expected one owner account; no changes made')
    uid = owners[0]['id']
    active = list(database.devices.find({'userId': uid, 'revoked': False}).limit(2))
    if len(active) != 1:
        raise ValueError('Expected exactly one active owner device; no changes made')
    device = active[0]
    if device.get('extensionVersion') != '1.1.6' or '_id' not in device:
        raise ValueError('Active owner device is not the expected legacy 1.1.6 device; no changes made')
    if not apply:
        return 'Confirmed: one obsolete owner device, version 1.1.6. Check only; no changes made.'
    result = database.devices.update_one(
        {'_id': device['_id'], 'userId': uid, 'extensionVersion': '1.1.6', 'revoked': False},
        {'$set': {'revoked': True}})
    if result.modified_count != 1:
        raise ValueError('Device changed during recovery; no successful retirement confirmed')
    return 'Retired the obsolete owner/1.1.6 device. Click RE-CHECK in extension 1.7.14. Other accounts and device limits were not changed.'


def main():
    from dotenv import dotenv_values
    from pymongo import MongoClient
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retire', action='store_true', help='Retire only the verified legacy owner device')
    args = parser.parse_args()
    config = dotenv_values(Path.home() / 'tradingwithkaos.com/backend/.env')
    if not config.get('MONGO_URL') or not config.get('DB_NAME'):
        raise SystemExit('Backend database settings are missing; no changes made')
    try:
        with MongoClient(config['MONGO_URL'], serverSelectionTimeoutMS=10000) as client:
            print(retire(client[config['DB_NAME']], args.retire))
    except ValueError as exc:
        raise SystemExit(str(exc))
    except Exception as exc:
        raise SystemExit(f'Recovery could not complete ({type(exc).__name__}). No success confirmed; database credentials were not printed.')


if __name__ == '__main__':
    main()
