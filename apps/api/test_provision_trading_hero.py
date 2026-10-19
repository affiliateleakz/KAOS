"""Pinned model revision is mandatory before staging model weights."""
import pytest
from provision_trading_hero import validate_revision


def test_rejects_moving_ref_or_short_hash():
    for value in ("main", "latest", "a" * 39, "z" * 40):
        with pytest.raises(ValueError):
            validate_revision(value)


def test_accepts_complete_sha():
    value = "a" * 40
    assert validate_revision(value) == value
