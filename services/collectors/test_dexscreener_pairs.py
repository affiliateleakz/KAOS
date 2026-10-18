import unittest
from datetime import datetime, timezone
from dexscreener_pairs import observe,number,fetch

class DexTests(unittest.TestCase):
    def test_liquidity_and_neutrality(self):
        pairs=[{'chainId':'solana','pairAddress':'123','baseToken':{'symbol':'TEST'},'liquidity':{'usd':100000},'volume':{'h24':250000},'url':'https://dexscreener.com/solana/123'}]
        result=observe(pairs,'https://api.dexscreener.com/latest/dex/search',datetime(2026,10,16,tzinfo=timezone.utc))
        self.assertEqual(result[0]['asset_class'],'dex')
        self.assertEqual(result[0]['direction'],'neutral')
        self.assertEqual(result[0]['source'],'liquidity')
        self.assertEqual(len(observe(pairs+pairs,'https://api.dexscreener.com')),1)
    def test_filters(self):
        self.assertEqual(observe([{'chainId':'solana','pairAddress':'a','liquidity':{'usd':10}}],'https://api.dexscreener.com'),[])
        self.assertEqual(number('NaN'),0)
        self.assertEqual(number(-20),0)
    def test_invalid_query(self):
        with self.assertRaises(ValueError): fetch('')
if __name__=='__main__': unittest.main()
