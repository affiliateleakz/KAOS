import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_offerings as offerings


def test_ipo_csv_retains_actual_dates_ranges_and_source():
    csv='symbol,name,ipoDate,priceRangeLow,priceRangeHigh,currency,exchange\nTEST,Example Issuer,2026-12-02,12,15,USD,NASDAQ\nBAD,Invalid,not-a-date,1,2,USD,X\n'
    result=offerings.ipo_rows(csv)
    assert len(result)==1 and result[0]['date']=='2026-12-02'
    assert result[0]['priceLow']==12 and result[0]['source']=='Alpha Vantage IPO calendar'
    assert 'subject to change' in result[0]['dateType']


def test_unconfigured_ipo_feed_does_not_invent_offerings(monkeypatch):
    monkeypatch.setattr(offerings.radar_settings,'settings',AsyncMock(return_value={'enabled':True,'api_key':''}))
    assert asyncio.run(offerings.ipo_calendar())['state']=='setup_required'
    assert asyncio.run(offerings.ipo_calendar())['items']==[]


def test_curated_entry_requires_real_https_primary_source(monkeypatch):
    monkeypatch.setattr(offerings,'db',SimpleNamespace(kaos_offerings=SimpleNamespace(insert_one=AsyncMock())))
    with pytest.raises(HTTPException):asyncio.run(offerings.add_offering(offerings.Offering(kind='ico',name='Example',symbol='EX',sourceUrl='http://example.com'),{'id':'owner'}))
    with pytest.raises(HTTPException):asyncio.run(offerings.add_offering(offerings.Offering(kind='ico',name='Example',symbol='EX',date='2026-99-99',sourceUrl='https://example.com'),{'id':'owner'}))
    result=asyncio.run(offerings.add_offering(offerings.Offering(kind='ico',name='Example',symbol='EX',date='2026-12-01',sourceUrl='https://example.com'),{'id':'owner'}))
    assert result['published'] is False and 'createdBy' not in result
