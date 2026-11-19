"""Collector excludes incomplete/no-trade buckets and handles Binance microseconds."""
import importlib.util
import io
from pathlib import Path
import zipfile
import pytest

spec=importlib.util.spec_from_file_location('public_candles',Path(__file__).resolve().parents[1]/'collect_public_candles.py')
collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)


def payload(rows):
    handle=io.BytesIO()
    with zipfile.ZipFile(handle,'w') as archive:archive.writestr('candles.csv','\n'.join(','.join(map(str,r)) for r in rows))
    return handle.getvalue()


def seconds(count=5,unit=1,trade_count=1):
    start=1790812800000
    return [[(start+i*1000)*unit,100,102,99,101,2,(start+i*1000+999)*unit,0,trade_count,0,0,0] for i in range(count)]


@pytest.mark.parametrize('unit',[1,1000])
def test_exact_complete_bucket_and_timestamp_units(unit):
    bars,quality=collector.aggregate(payload(seconds(unit=unit)))
    assert len(bars)==1 and bars[0]['ts']==1790812800000
    assert bars[0]['closeTs']-bars[0]['ts']==5000
    assert bars[0]['volume']==10 and bars[0]['trades']==5
    assert quality['source_seconds']==5


def test_partial_and_no_trade_buckets_are_not_filled():
    bars,quality=collector.aggregate(payload(seconds(4)))
    assert bars==[] and quality['incomplete_five_second_buckets']==1
    bars,quality=collector.aggregate(payload(seconds(trade_count=0)))
    assert bars==[] and quality['no_trade_buckets_excluded']==1


def test_duplicate_source_second_is_an_error():
    rows=seconds()
    with pytest.raises(ValueError):collector.aggregate(payload(rows+[rows[0]]))
