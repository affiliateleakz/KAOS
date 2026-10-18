"""SQLite paper-order reservation journal. No live broker routing.

Reservations are durable and unique across processes. A crash after reservation
stays UNKNOWN until operator reconciliation; NEVER blindly resubmit.
"""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from enum import Enum


class JournalConflict(ValueError):
    pass


class PaperOrderJournal:
    def __init__(self, path):
        self.path = str(path)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS paper_orders (
              user_id TEXT NOT NULL, broker TEXT NOT NULL, account_id TEXT NOT NULL,
              client_order_id TEXT NOT NULL, intent_json TEXT NOT NULL,
              state TEXT NOT NULL, report_json TEXT,
              PRIMARY KEY (user_id, broker, account_id, client_order_id))''')

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        try:
            db.execute('PRAGMA busy_timeout=15000')
            yield db
            if db.in_transaction:
                db.commit()
        except BaseException:
            if db.in_transaction:
                db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _json(obj):
        return json.dumps(asdict(obj), sort_keys=True, separators=(',', ':'), default=lambda x: x.value if isinstance(x, Enum) else str(x))

    def reserve(self, intent):
        key = (intent.user_id, intent.broker, intent.account_id, intent.client_order_id)
        payload = self._json(intent)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT intent_json,state,report_json FROM paper_orders WHERE user_id=? AND broker=? AND account_id=? AND client_order_id=?', key).fetchone()
            if existing:
                if existing[0] != payload:
                    raise JournalConflict('Client order ID reused with different order details')
                return existing[1], existing[2]
            db.execute('INSERT INTO paper_orders VALUES (?,?,?,?,?,?,?)', (*key, payload, 'UNKNOWN', None))
            return 'NEW', None

    def finish(self, intent, report):
        key = (intent.user_id, intent.broker, intent.account_id, intent.client_order_id)
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            result = db.execute('UPDATE paper_orders SET state=?,report_json=? WHERE user_id=? AND broker=? AND account_id=? AND client_order_id=? AND state=?', (report.state.value, self._json(report), *key, 'UNKNOWN'))
            if result.rowcount != 1:
                raise JournalConflict('Reservation missing or already finalized')

    def get(self, intent):
        key = (intent.user_id, intent.broker, intent.account_id, intent.client_order_id)
        with self._db() as db:
            return db.execute('SELECT state,report_json FROM paper_orders WHERE user_id=? AND broker=? AND account_id=? AND client_order_id=?', key).fetchone()
