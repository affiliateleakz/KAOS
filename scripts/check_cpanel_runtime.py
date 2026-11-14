"""Read-only hosting check before upgrading Python dependencies. No secret output."""
from pathlib import Path
import sys


def compatible_database(version):
    try:
        return tuple(int(part) for part in version.split('.')[:2]) >= (4, 4)
    except (ValueError, AttributeError):
        return False


def main():
    if sys.version_info < (3, 11):
        raise SystemExit('Python 3.11 or later is required')
    from dotenv import dotenv_values
    from pymongo import MongoClient
    config = dotenv_values(Path.home() / 'tradingwithkaos.com/backend/.env')
    if not config.get('MONGO_URL'):
        raise SystemExit('Backend MONGO_URL is missing; nothing changed')
    try:
        with MongoClient(config['MONGO_URL'], serverSelectionTimeoutMS=10000) as client:
            version = client.server_info().get('version', '')
            if not compatible_database(version):
                raise SystemExit('MongoDB 4.4 or later is required for the new driver; stop before upgrading')
            print('Python and MongoDB compatibility checks passed. No database records were changed.')
    except Exception as exc:
        raise SystemExit(f'Cannot verify database compatibility ({type(exc).__name__}); stop before upgrading')


if __name__ == '__main__':
    main()
