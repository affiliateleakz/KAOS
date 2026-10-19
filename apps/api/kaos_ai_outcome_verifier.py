"""KAOS shadow outcome verification helpers; no trading authority."""
from decimal import Decimal
from datetime import datetime

def timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
