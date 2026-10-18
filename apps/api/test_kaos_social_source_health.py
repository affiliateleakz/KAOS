import unittest
from kaos_source_health import provider
class SocialProviderTests(unittest.TestCase):
    def test_bsky_search(self):
        self.assertEqual(provider('bsky-search:GME:2026101605'),'bsky-search')
if __name__=='__main__':unittest.main()
