"""Pure offline safety and regression tests for private R2 AI learning."""
import os
import sys
import unittest

sys.path.insert(0,os.path.dirname(__file__))
from kaos_r2_ai_lab import make_samples, train_from_candles, _split, _evaluate

def candles(n=600,gap=False):
    start=1700000040000
    out=[]
    for i in range(n):
        j=i+(3 if gap and i>=300 else 0)
        p=100+0.08*i+2.4*((i%13)/13)
        out.append({"ts":start+j*60000,"open":p-0.12,"high":p+1.0,
                    "low":p-1,"close":p,"volume":float(10+(i%17))})
    return out

class TestR2AILab(unittest.TestCase):
    def test_chronological_split_purges_label_boundary(self):
        s=make_samples(candles(),60,4)
        train,val,test=_split(s,4)
        self.assertGreater(len(train),80)
        self.assertLess(train[-1]["settlement_ts"],val[0]["ts"])
        self.assertLess(val[-1]["settlement_ts"],test[0]["ts"])
        self.assertLess(train[-1]["ts"],val[0]["ts"])
        self.assertLess(val[-1]["ts"],test[0]["ts"])

    def test_no_examples_span_provider_gap(self):
        s=make_samples(candles(gap=True),60,4)
        boundary=candles(gap=True)[299]["ts"]
        self.assertTrue(s)
        self.assertTrue(all(r["settlement_ts"]<=boundary or r["ts"]>boundary for r in s))

    def test_cannot_promote_from_short_archive(self):
        r=train_from_candles(candles(130),60,4)
        self.assertEqual(r["status"],"insufficient_training_history")
        self.assertFalse(r["execution_enabled"])

    def test_training_deterministic_and_never_execution_authorized(self):
        r=train_from_candles(candles(540),60,4)
        self.assertIn(r["status"],("candidate_not_validated","validated_research_candidate"))
        self.assertFalse(r["execution_enabled"])
        self.assertTrue(r["research_only"])
        self.assertEqual(r["model"]["features"][0],"ret1")
        self.assertLess(r["train_range"][1],r["validation_range"][0])
        self.assertLess(r["validation_range"][1],r["test_range"][0])
        self.assertEqual(r["dataset_fingerprint"],train_from_candles(candles(540),60,4)["dataset_fingerprint"])
        self.assertEqual(r["test"]["samples"],len(make_samples(candles(540),60,4))-
                         int(len(make_samples(candles(540),60,4))*0.80))

    def test_zero_selected_predictions_do_not_fabricate_accuracy(self):
        sample={"ts":100,"settlement_ts":200,"x":[0]*8,"y":1}
        model={"weights":[0]*8,"mean":[0]*8,"std":[1]*8,"bias":0}
        r=_evaluate([sample],model,seconds=60)
        self.assertEqual(r["signals"],0)
        self.assertIsNone(r["accuracy"])

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            make_samples(candles(50),60,0)

if __name__=="__main__":
    unittest.main()
