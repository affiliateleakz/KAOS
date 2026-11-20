"""Regression tests for multi-horizon training sample integrity."""
import unittest
from kaos_training_samples import sample_bucket_key


class SampleBucketTests(unittest.TestCase):
    def test_five_second_samples_do_not_collapse_into_thirty_second_bucket(self):
        a = {"asset": "BTC-USD", "t": 30000, "targetHorizonMs": 5000}
        b = {"asset": "BTC-USD", "t": 35000, "targetHorizonMs": 5000}
        self.assertNotEqual(sample_bucket_key(a, 5000), sample_bucket_key(b, 5000))

    def test_same_horizon_bucket_deduplicates(self):
        a = {"asset": "BTC-USD", "t": 30000, "targetHorizonMs": 5000}
        b = {"asset": "BTC-USD", "t": 31000, "targetHorizonMs": 5000}
        self.assertEqual(sample_bucket_key(a, 5000), sample_bucket_key(b, 5000))

    def test_mixed_horizons_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            sample_bucket_key({"asset": "BTC-USD", "t": 30000, "targetHorizonMs": 30000}, 5000)

    def test_missing_horizon_rejected_on_new_tasks(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            sample_bucket_key({"asset": "BTC-USD", "t": 30000}, 5000)

    def test_legacy_30_second_rows_still_supported(self):
        self.assertEqual(sample_bucket_key({"asset": "BTC-USD", "t": 30000}, 30000)[2], 30000)

    def test_missing_timestamp_rejected(self):
        with self.assertRaisesRegex(ValueError, "timestamp"):
            sample_bucket_key({"asset": "BTC-USD", "targetHorizonMs": 5000}, 5000)

    def test_venue_sources_do_not_deduplicate_each_other(self):
        a = {"asset": "BTC-USD", "t": 30000, "targetHorizonMs": 5000, "source": "coinbase"}
        b = {**a, "source": "another_venue"}
        self.assertNotEqual(sample_bucket_key(a, 5000), sample_bucket_key(b, 5000))


if __name__ == "__main__":
    unittest.main()
