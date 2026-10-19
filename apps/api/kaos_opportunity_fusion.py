"""Unified KAOS opportunity evaluation over verified, time-aligned evidence.

This is a deterministic decision boundary, not a substitute for real market
connectors, trained models, a risk engine or broker-side execution.
Only upstream verified direction observations may contribute trade votes.
News/social/LLM analysis is context unless its source is explicitly validated.
"""
from datetime import datetime, timezone

SOURCES = frozenset({"chart", "indicators", "strategy", "news", "social", "financial_llm", "orderflow"})
DIRECTIONS = frozenset({"BUY", "SELL"})
MAX_AGE_SECONDS = {"chart": 60, "indicators": 60, "strategy": 60,
                   "orderflow": 30, "news": 3600, "social": 900, "financial_llm": 3600}


def evaluate_opportunity(asset, broker, evidence, *, now=None):
    """Never emit an executable order. Separate research direction from readiness."""
    now = now or datetime.now(timezone.utc)
    accepted, excluded = [], []
    for item in evidence:
        source = item.get("source")
        timestamp = item.get("timestamp")
        if source not in SOURCES or not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
            excluded.append({"source": source, "reason": "unknown_source_or_timestamp"})
            continue
        age = (now - timestamp).total_seconds()
        if age < 0 or age > MAX_AGE_SECONDS[source]:
            excluded.append({"source": source, "reason": "stale_or_future"})
            continue
        if item.get("simulated") or not item.get("verified"):
            excluded.append({"source": source, "reason": "unverified_or_simulated"})
            continue
        if item.get("asset") != asset:
            excluded.append({"source": source, "reason": "asset_mismatch"})
            continue
        if item.get("direction") not in DIRECTIONS:
            excluded.append({"source": source, "reason": "no_direction"})
            continue
        accepted.append({"source": source, "direction": item["direction"],
                         "confidence": item.get("confidence"), "ageSeconds": round(age, 2)})
    # Trade candidates need fresh verified market evidence. AI prose cannot
    # invent a trade independently of the market and a specific strategy.
    market = [v for v in accepted if v["source"] in ("chart", "indicators", "strategy", "orderflow")]
    strategy = [v for v in accepted if v["source"] == "strategy"]
    candidate = None
    if strategy and market:
        directions = {v["direction"] for v in market}
        if len(directions) == 1:
            candidate = strategy[0]["direction"]
    context = [v for v in accepted if v["source"] in ("news", "social", "financial_llm")]
    conflicts = [v["source"] for v in context if candidate and v["direction"] != candidate]
    status = "CANDIDATE_RESEARCH_ONLY" if candidate else "NO_TRADE"
    return {"asset": asset, "broker": broker, "status": status,
            "candidate_direction": candidate, "executable": False,
            "reason": "Broker validation, portfolio risk, and live authorization are separate required steps."
                      if candidate else "No verified fresh unconflicted strategy and market alignment.",
            "context_conflicts": conflicts, "accepted_evidence": accepted,
            "excluded_evidence": excluded}
