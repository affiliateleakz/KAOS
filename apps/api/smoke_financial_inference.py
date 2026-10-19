"""Operator smoke test for locally staged Trading-Hero weights; no trading."""
import json
import sys
import time
from kaos_financial_inference import classify_headlines


def main():
    examples = [
        "Company reports stronger revenue and raises full-year guidance",
        "Company warns of weaker sales and cuts full-year guidance",
        "Company announces the date of its quarterly earnings call",
    ]
    started = time.monotonic()
    try:
        output = classify_headlines(examples)
    except Exception as exc:
        print(json.dumps({"status": "UNAVAILABLE", "error_type": type(exc).__name__,
                          "trading_enabled": False}))
        return 1
    if len(output) != len(examples) or any(row.get("execution_authority") is not False for row in output):
        print(json.dumps({"status": "INVALID_OUTPUT", "trading_enabled": False}))
        return 2
    print(json.dumps({"status": "INFERENCE_RESPONDED",
                      "note": "Manual semantic review and holdout validation still required",
                      "latency_seconds": round(time.monotonic() - started, 3),
                      "predictions": output, "trading_enabled": False}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
