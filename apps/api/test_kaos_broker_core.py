import unittest
from dataclasses import replace
from kaos_broker_core import *
class BrokerCoreTests(unittest.TestCase):
    def setUp(self):
        self.i=OrderIntent('u','coinbase','a','client-1','BTC-USD',AssetClass.CRYPTO_SPOT,'BUY',OrderKind.MARKET,'10','QUOTE','sig-1')
    def test_spot_buy(self): validate_intent(self.i,BROKER_CATALOG['coinbase'])
    def test_negative(self):
        with self.assertRaises(ValueError): validate_intent(replace(self.i,quantity='-2'),BROKER_CATALOG['coinbase'])
    def test_nan(self):
        with self.assertRaises(ValueError): validate_intent(replace(self.i,quantity='NaN'),BROKER_CATALOG['coinbase'])
    def test_spot_expiry_rejected(self):
        with self.assertRaises(ValueError): validate_intent(replace(self.i,expiration_seconds=45),BROKER_CATALOG['coinbase'])
    def test_spot_uncovered_sell_rejected(self):
        with self.assertRaises(ValueError): validate_intent(replace(self.i,side='SELL'),BROKER_CATALOG['coinbase'])
    def test_spot_position_sell(self): validate_intent(replace(self.i,side='SELL',metadata={'source_position_id':'p'}),BROKER_CATALOG['coinbase'])
    def test_binary_expiry(self):
        i=replace(self.i,broker='pocket_option',asset_class=AssetClass.BINARY,order_kind=OrderKind.BINARY_DIRECTION,quantity_unit='STAKE',expiration_seconds=15)
        validate_intent(i,BROKER_CATALOG['pocket_option'])
    def test_binary_no_expiry(self):
        i=replace(self.i,broker='pocket_option',asset_class=AssetClass.BINARY,order_kind=OrderKind.BINARY_DIRECTION,quantity_unit='STAKE')
        with self.assertRaises(ValueError): validate_intent(i,BROKER_CATALOG['pocket_option'])
    def test_all_catalog_disabled(self): self.assertTrue(all(not c.live_supported for c in BROKER_CATALOG.values()))
if __name__=='__main__': unittest.main()
