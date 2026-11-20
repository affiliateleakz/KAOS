import unittest
from kaos_chart_detection import normalize_detections

class ChartDetectorAdapterTests(unittest.TestCase):
    def test_valid_box_normalized(self):
        result=normalize_detections([{"label":"breakout_up","score":.8,
                                     "xyxy":[20,10,100,50]}],
                                    width=200,height=100,threshold=.5)
        self.assertEqual(result[0]["box"]["x"],.1)
        self.assertEqual(result[0]["box"]["width"],.4)
        self.assertEqual(result[0]["score_meaning"],
                         "detector_object_confidence_not_market_probability")

    def test_low_score_filtered_without_fabrication(self):
        self.assertEqual(normalize_detections(
            [{"label":"uptrend","score":.2,"xyxy":[0,0,100,100]}],
            width=100,height=100),[])

    def test_invalid_image_extent_fails(self):
        with self.assertRaisesRegex(ValueError,"outside image"):
            normalize_detections([{"label":"range","score":.9,
                "xyxy":[0,0,300,100]}],width=200,height=100)

    def test_invalid_labels_blocked(self):
        with self.assertRaisesRegex(ValueError,"label"):
            normalize_detections([{"label":"guaranteed_buy","score":.99,
                "xyxy":[0,0,50,50]}],width=200,height=100)

    def test_nonfinite_scores_blocked(self):
        with self.assertRaisesRegex(ValueError,"score"):
            normalize_detections([{"label":"uptrend","score":float("nan"),
                "xyxy":[0,0,50,50]}],width=200,height=100)

    def test_sorted_and_bounded(self):
        inp=[{"label":"range","score":.51+.001*i,
              "xyxy":[0,0,50,50]} for i in range(25)]
        res=normalize_detections(inp,width=100,height=100)
        self.assertEqual(len(res),20)
        self.assertGreaterEqual(res[0]["detection_score"],res[-1]["detection_score"])

if __name__=="__main__":unittest.main()
