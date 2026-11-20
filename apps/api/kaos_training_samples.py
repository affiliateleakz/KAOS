"""Pure input checks for the legacy KAOS classifier training wire format.

Legacy untagged examples belong only to the original 30-second task. New
horizons must carry an explicit target horizon to prevent silent label mixing.
"""


def sample_bucket_key(sample, target_horizon_ms, row_index=0):
    """Return a source/asset/horizon/time bucket or reject an unsafe sample."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a dict")
    target = int(target_horizon_ms)
    if not 5000 <= target <= 3600000:
        raise ValueError("unsupported target horizon")
    declared = sample.get("targetHorizonMs", sample.get("horizonMs"))
    if declared is None:
        if target != 30000:
            raise ValueError("missing sample horizon for nonlegacy task")
        declared = 30000
    if int(declared) != target:
        raise ValueError("sample horizon mismatch")
    timestamp = int(sample.get("t", sample.get("ts", 0)) or 0)
    if timestamp <= 0:
        raise ValueError("sample timestamp required")
    asset = str(sample.get("asset") or "").strip()
    if not asset:
        raise ValueError("sample asset required")
    source = str(sample.get("source") or "legacy_unspecified").strip()
    return (source, asset, target, (timestamp // target) * target)
