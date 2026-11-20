"""Verified visual detection output adapter for a future KAOS-owned detector.

Normalizes boxes returned by an independently licensed detector. Not a
prediction service; no image scanning, trained detector or fake detections.
"""
import math

LABELS = frozenset(("uptrend", "downtrend", "range",
                    "breakout_up", "breakout_down", "unknown"))


def normalize_detections(raw, *, width, height, threshold=0.5, max_items=20):
    """Accept bounded pixel xyxy boxes, return normalized fractional coordinates.

    Detection scores indicate object-localization confidence only, never a
    calibrated next-price prediction. Bad provider output is rejected.
    """
    if not (type(width) is int and 16 <= width <= 10000 and
            type(height) is int and 16 <= height <= 10000):
        raise ValueError("invalid dimensions")
    if (type(threshold) not in (int, float) or not math.isfinite(threshold) or
            not 0 <= threshold <= 1):
        raise ValueError("invalid detection threshold")
    if not isinstance(raw, list) or len(raw) > 100:
        raise ValueError("invalid detector output")
    results = []
    for detection in raw:
        if not isinstance(detection, dict):
            raise ValueError("invalid detection record")
        label = detection.get("label")
        score = detection.get("score")
        coords = detection.get("xyxy")
        if label not in LABELS or not isinstance(coords, (list, tuple)) or len(coords) != 4:
            raise ValueError("invalid detection label or box")
        if type(score) not in (float, int) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid detection score")
        if any(type(p) not in (float, int) or not math.isfinite(p) for p in coords):
            raise ValueError("invalid detection coordinates")
        x1,y1,x2,y2 = coords
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError("box outside image")
        if score < threshold:
            continue
        results.append({
            "label": label,
            "detection_score": round(float(score), 4),
            "box": {
                "x": round(x1/width, 6), "y": round(y1/height, 6),
                "width": round((x2-x1)/width, 6),
                "height": round((y2-y1)/height, 6),
            },
            "score_meaning": "detector_object_confidence_not_market_probability",
        })
    results.sort(key=lambda x:x["detection_score"],reverse=True)
    return results[:max_items]
