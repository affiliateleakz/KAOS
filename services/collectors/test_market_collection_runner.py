import json
import tempfile
import unittest
from pathlib import Path
from market_collection_runner import load_config

class RunnerTests(unittest.TestCase):
    def write_and_load(self, doc):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'cfg.json'
            path.write_text(json.dumps(doc))
            return load_config(path)
    def test_normalized_config(self):
        c=self.write_and_load({'stocks':['aapl','SPY','AAPL'], 'etfs':['spy'],
                               'crypto_spot':['btcusdt'], 'options_underlyings':['AAPL'],
                               'dex_queries':['SOL']})
        self.assertEqual(c['stocks'], ['AAPL','SPY'])
        self.assertEqual(c['crypto_spot'], ['BTCUSDT'])
        self.assertTrue(c['tradier_sandbox'])
        self.assertEqual(c['social_search_cashtags'], [])
    def test_mismatched_etf_rejected(self):
        with self.assertRaises(ValueError):
            self.write_and_load({'stocks':['AAPL'], 'etfs':['SPY']})
    def test_rate_limit_controls(self):
        with self.assertRaises(ValueError):
            self.write_and_load({'options_underlyings':['AAPL']*101})
    def test_search_config_validated(self):
        c=self.write_and_load({'social_search_cashtags':['GME','AMC']})
        self.assertEqual(c['social_search_cashtags'], ['GME','AMC'])
        with self.assertRaises(ValueError):
            self.write_and_load({'social_search_cashtags':['A'+str(i) for i in range(21)]})
    def test_public_search_wired_into_runner(self):
        from unittest.mock import patch
        from market_collection_runner import collect_once
        c=self.write_and_load({'social_search_cashtags':['GME']})
        with patch('market_collection_runner.run_social_search',return_value=([],[])) as run:
            items,issues=collect_once(c,0,include_news=False,include_sec=False,include_13f=False)
        run.assert_called_once()
        self.assertEqual(items,[])
        self.assertEqual(issues,[])
    def test_invalid_provider_selection(self):
        with self.assertRaises(ValueError):
            self.write_and_load({'alpaca_feed':'unverified'})

if __name__=='__main__': unittest.main()
