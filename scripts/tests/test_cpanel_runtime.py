import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('runtime_check', Path(__file__).resolve().parents[1] / 'check_cpanel_runtime.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


@pytest.mark.parametrize('version,accepted', [('3.6.0', False), ('4.0.0', False), ('4.2.0', False), ('4.4.0', True), ('7.0.16', True), ('8.0.0', True), ('invalid', False), ('', False)])
def test_driver_compatibility_threshold(version, accepted):
    assert check.compatible_database(version) is accepted
