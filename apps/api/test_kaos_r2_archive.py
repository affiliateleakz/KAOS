"""Offline regression checks for private Cloudflare R2 research reads."""
import json
import os
import sys
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
sys.path.insert(0,os.path.dirname(__file__))

import kaos_r2_archive as r2

BASE=int(datetime(2026,11,20,20,tzinfo=timezone.utc).timestamp()*1000)
def bars(symbol="BTC-USD",asset_class="crypto",source="coinbase_exchange_public",count=150):
    return [{"ts":BASE-(count-i)*60000,"symbol":symbol,"asset_class":asset_class,
             "seconds":60,"source":source,"open":100,"high":101,"low":99,
             "close":100.4,"volume":22} for i in range(count)]

class R2ReaderTests(unittest.IsolatedAsyncioTestCase):
    def test_never_allow_path_traversal(self):
        with self.assertRaises(ValueError):
            r2.validate_request("../AAPL","stock",60,300)
        with self.assertRaises(ValueError):
            r2.validate_request("BTC/../USD","crypto",60,300)
        with self.assertRaises(ValueError):
            r2.validate_request("BTC-USD","crypto",30,300)

    async def test_disabled_archive_avoids_network(self):
        with patch.dict(os.environ,{"KAOS_R2_ENABLED":"false"}):
            result=await r2.read_archive("BTC-USD","crypto",60)
        self.assertEqual(result,([],None))

    async def test_cryptocurrency_archive_keeps_single_source(self):
        with patch.dict(os.environ,{"KAOS_R2_ENABLED":"true"}):
            with patch.object(r2,"_fetch_days",return_value=bars()):
                rows,source=await r2.read_archive("BTC-USD","crypto",60,
                    limit=300,now_ms=BASE)
        self.assertEqual(len(rows),150)
        self.assertEqual(source,"coinbase_exchange_public")
        self.assertEqual(rows[0]["ts"],BASE-150*60000)

    async def test_reject_mixed_provider_rows(self):
        mixed=bars()
        mixed[20]["source"]="alpaca_iex"
        with patch.dict(os.environ,{"KAOS_R2_ENABLED":"true"}):
            with patch.object(r2,"_fetch_days",return_value=mixed):
                with self.assertRaises(r2.ArchiveUnavailable):
                    await r2.read_archive("BTC-USD","crypto",60,
                        limit=300,now_ms=BASE)

    async def test_owner_larger_than_300_preserves_history(self):
        with patch.dict(os.environ,{"KAOS_R2_ENABLED":"true"}):
            with patch.object(r2,"_fetch_days",return_value=bars(count=1200)):
                rows,_=await r2.read_archive("BTC-USD","crypto",60,
                    limit=5000,now_ms=BASE)
        self.assertEqual(len(rows),1200)
        self.assertEqual(rows[0]["ts"],BASE-1200*60000)

    async def test_skips_still_open_candle(self):
        data=bars(count=100)
        data.append({**bars(count=1)[0],"ts":BASE})
        with patch.dict(os.environ,{"KAOS_R2_ENABLED":"true"}):
            with patch.object(r2,"_fetch_days",return_value=data):
                rows,_=await r2.read_archive("BTC-USD","crypto",60,
                    limit=300,now_ms=BASE)
        self.assertEqual(len(rows),100)
        self.assertTrue(all(row["ts"]<BASE for row in rows))

    def test_credential_validation_precedes_any_external_request(self):
        with patch.dict(os.environ,{"KAOS_R2_ACCOUNT_ID":"bad","KAOS_R2_ACCESS_KEY_ID":"x",
                                  "KAOS_R2_SECRET_ACCESS_KEY":"y"}):
            with self.assertRaises(r2.ArchiveUnavailable):
                r2._client()

if __name__=="__main__":
    unittest.main()
