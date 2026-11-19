import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

spec = importlib.util.spec_from_file_location('owner_recovery', Path(__file__).resolve().parents[1] / 'retire_legacy_owner_device.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def database(records, owners=None, modified=1):
    owner_find = Mock(return_value=SimpleNamespace(limit=lambda n: owners if owners is not None else [{'id': 'owner-id'}]))
    devices = SimpleNamespace(find=Mock(return_value=SimpleNamespace(limit=lambda n: records)),
                              update_one=Mock(return_value=SimpleNamespace(modified_count=modified)))
    return SimpleNamespace(users=SimpleNamespace(find=owner_find), devices=devices)


def test_targets_only_legacy_device_of_owner():
    db = database([{'_id': 'mongo-id', 'extensionVersion': '1.1.6'}])
    assert 'Retired' in recovery.retire(db, apply=True)
    db.devices.find.assert_called_once_with({'userId': 'owner-id', 'revoked': False})
    db.devices.update_one.assert_called_once_with(
        {'_id': 'mongo-id', 'userId': 'owner-id', 'extensionVersion': '1.1.6', 'revoked': False},
        {'$set': {'revoked': True}})


def test_default_is_read_only():
    db = database([{'_id': 'mongo-id', 'extensionVersion': '1.1.6'}])
    assert 'Check only' in recovery.retire(db)
    db.devices.update_one.assert_not_called()


@pytest.mark.parametrize('records', [[], [{'_id': 'new', 'extensionVersion': '1.7.14'}],
    [{'_id': 'old', 'extensionVersion': '1.1.6'}, {'_id': 'another', 'extensionVersion': '1.1.6'}]])
def test_refuses_ambiguous_or_different_device(records):
    db = database(records)
    with pytest.raises(ValueError):
        recovery.retire(db, apply=True)
    db.devices.update_one.assert_not_called()


@pytest.mark.parametrize('owners', [[], [{'id': 'one'}, {'id': 'two'}]])
def test_refuses_ambiguous_owner(owners):
    db = database([], owners=owners)
    with pytest.raises(ValueError):
        recovery.retire(db, apply=True)
    db.devices.update_one.assert_not_called()


def test_race_is_not_reported_as_success():
    db = database([{'_id': 'mongo-id', 'extensionVersion': '1.1.6'}], modified=0)
    with pytest.raises(ValueError, match='changed during recovery'):
        recovery.retire(db, apply=True)
