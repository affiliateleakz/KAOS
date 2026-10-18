"""KAOS AI — pure-Python inference over the native tree bundle produced by kaos_ai_trainer.

The trainer emits a portable bundle: {type, base, task:'logit_sum', features, trees:[node...],
assetModels:{asset:bundle}, ...} where each node is {'f','t','l','r'} or {'leaf'}. This walks the
trees with zero heavy dependencies so server-side inference stays fast and dependency-free.

AI is LEARNING/REPORTING ONLY — it never has execution authority over the deterministic strategy.
"""
from __future__ import annotations
import math

FEATURES = 104
# Must mirror the trainer's model_matrix masking so inference sees the same feature space.
MODEL_DISABLED_FEATURES = tuple(list(range(32, 48)) + [54, 55])


def _sigmoid(z):
    if z < -60:
        return 0.0
    if z > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def _mask(x):
    v = [float(x[i]) if i < len(x) else 0.0 for i in range(FEATURES)]
    for i in MODEL_DISABLED_FEATURES:
        v[i] = 0.0
    return v


def _walk(node, x):
    while "leaf" not in node:
        node = node["l"] if x[node["f"]] < node["t"] else node["r"]
    return node["leaf"]


def _score_bundle(bundle, x):
    margin = float(bundle.get("base", 0.0))
    for tree in bundle.get("trees", []):
        margin += _walk(tree, x)
    return _sigmoid(margin)


def normalize_features(x):
    """Accept 88-feature legacy rows (padded to 104) or full 104 vectors."""
    if isinstance(x, list) and len(x) == 88:
        x = x + [0.0] * 16
    return x


def predict(bundle, features, asset=None):
    """Return {prob_up, direction, confidence, modelKind} for a single feature vector.

    Prefers a per-asset model when one exists for the asset (market-aware), else the global model.
    """
    x = _mask(normalize_features(features))
    kind = "global"
    active = bundle
    asset_models = bundle.get("assetModels") or {}
    if asset and asset in asset_models and asset_models[asset]:
        active = asset_models[asset]
        kind = "asset"
    prob_up = _score_bundle(active, x)
    direction = "BUY" if prob_up >= 0.5 else "SELL"
    confidence = round(max(prob_up, 1.0 - prob_up), 4)
    return {"prob_up": round(prob_up, 4), "direction": direction,
            "confidence": confidence, "modelKind": kind}
