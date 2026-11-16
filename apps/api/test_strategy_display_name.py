"""Old saved default names remain compatible without changing engine settings."""
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from services_trading import get_official_strategy


@pytest.mark.parametrize('name', ['KAOS Berserker', 'Berserker', 'Candidate 7B', 'candidate'])
def test_saved_default_strategy_name_is_presented_as_kaos(name):
    saved = {'name': name, 'engine': 'TWO_CANDLE_CONTINUATION', 'expiration': '45s'}
    with patch.dict(get_official_strategy.__globals__, {'get_setting': AsyncMock(return_value=saved)}):
        result = asyncio.run(get_official_strategy())
    assert result == {**saved, 'name': 'KAOS Strategy'}
    assert saved['name'] == name
