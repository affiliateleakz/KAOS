"""Regression tests: revoked extension devices cannot self-reactivate."""
import asyncio
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("MONGO_URL","mongodb://localhost:27017")
os.environ.setdefault("DB_NAME","kaos_test")
sys.path.insert(0,os.path.dirname(__file__))

from fastapi import HTTPException
import routes_extension
from models import DeviceReq

class FakeDevices:
    def __init__(self, doc):
        self.doc = dict(doc)
        self.last_update = None
        self.revoke_during_update = False

    async def find_one(self, query):
        for key,value in query.items():
            if isinstance(value,dict) and value.get("$ne") is True:
                if self.doc.get(key) is True:
                    return None
            elif self.doc.get(key)!=value:
                return None
        return dict(self.doc)

    async def update_one(self, query, update):
        self.last_update=(query,update)
        if self.revoke_during_update:
            self.doc["revoked"]=True
        match=await self.find_one(query)
        if match:
            self.doc.update(update["$set"])
        return SimpleNamespace(matched_count=1 if match else 0)

class RegistrationRevocationTests(unittest.TestCase):
    def run_registration(self,devices):
        user={"id":"owner1"}
        request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        fake_db=SimpleNamespace(devices=devices)
        with patch.object(routes_extension,"db",fake_db):
            return asyncio.run(routes_extension.register_device(
                DeviceReq(installId="installation1",extensionVersion="2.0"),
                request,user))

    def test_revoked_device_is_denied_with_no_writes(self):
        devices=FakeDevices({"id":"device1","installId":"installation1",
                             "userId":"owner1","revoked":True})
        with self.assertRaises(HTTPException) as e:
            self.run_registration(devices)
        self.assertEqual(e.exception.status_code,403)
        self.assertIsNone(devices.last_update)
        self.assertTrue(devices.doc["revoked"])

    def test_active_registration_never_resets_revocation(self):
        devices=FakeDevices({"id":"device1","installId":"installation1",
                             "userId":"owner1","revoked":False})
        result=self.run_registration(devices)
        self.assertEqual(result["extensionVersion"],"2.0")
        self.assertFalse(result["revoked"])
        self.assertNotIn("revoked",devices.last_update[1]["$set"])
        self.assertEqual(devices.last_update[0]["revoked"],{"$ne":True})

    def test_revocation_racing_registration_denies_reactivation(self):
        devices=FakeDevices({"id":"device1","installId":"installation1",
                             "userId":"owner1","revoked":False})
        devices.revoke_during_update=True
        with self.assertRaises(HTTPException) as e:
            self.run_registration(devices)
        self.assertEqual(e.exception.status_code,403)
        self.assertTrue(devices.doc["revoked"])

if __name__=="__main__":
    unittest.main()
