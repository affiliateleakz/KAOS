"""KAOS broker-neutral contract. No broker credentials or live execution here.
Adapters implement this interface. Spot, margin, binary and CFDs are distinct.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Protocol, Optional, Mapping, Any

class AssetClass(str, Enum):
    CRYPTO_SPOT = 'CRYPTO_SPOT'
    FOREX = 'FOREX'
    EQUITY = 'EQUITY'
    CFD = 'CFD'
    BINARY = 'BINARY'

class OrderKind(str, Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    BINARY_DIRECTION = 'BINARY_DIRECTION'

class OrderState(str, Enum):
    RESERVED = 'RESERVED'
    SUBMITTED = 'SUBMITTED'
    PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    FILLED = 'FILLED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'
    UNKNOWN = 'UNKNOWN'

@dataclass(frozen=True)
class Capabilities:
    asset_classes: frozenset[AssetClass]
    order_kinds: frozenset[OrderKind]
    supports_short: bool = False
    supports_native_stops: bool = False
    supports_fills: bool = False
    supports_expiry: bool = False
    live_supported: bool = False

@dataclass(frozen=True)
class OrderIntent:
    user_id: str
    broker: str
    account_id: str
    client_order_id: str
    symbol: str
    asset_class: AssetClass
    side: str
    order_kind: OrderKind
    quantity: str
    quantity_unit: str  # BASE, QUOTE, CONTRACTS, STAKE
    strategy_signal_id: str
    expiration_seconds: Optional[int] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecutionReport:
    broker: str
    account_id: str
    client_order_id: str
    broker_order_id: Optional[str]
    state: OrderState
    filled_quantity: str = '0'
    average_price: Optional[str] = None
    fee_amount: str = '0'
    fee_currency: Optional[str] = None

class BrokerAdapter(Protocol):
    broker_id: str
    capabilities: Capabilities
    async def market_rules(self, symbol: str) -> Mapping[str, Any]: ...
    async def submit(self, intent: OrderIntent) -> ExecutionReport: ...
    async def lookup(self, client_order_id: str) -> ExecutionReport: ...
    async def fills(self, broker_order_id: str) -> list[Mapping[str, Any]]: ...
    async def balances(self) -> Mapping[str, str]: ...
    async def cancel(self, broker_order_id: str) -> ExecutionReport: ...

def decimal_positive(value: str) -> Decimal:
    try:
        result = Decimal(value)
        if not result.is_finite() or result <= 0:
            raise ValueError('Quantity must be finite and positive')
        return result
    except (InvalidOperation, TypeError) as exc:
        raise ValueError('Invalid quantity') from exc

def validate_intent(intent: OrderIntent, caps: Capabilities) -> None:
    for field_name in ('user_id','broker','account_id','client_order_id','symbol','strategy_signal_id'):
        if not getattr(intent,field_name):
            raise ValueError('Missing '+field_name)
    decimal_positive(intent.quantity)
    if intent.asset_class not in caps.asset_classes or intent.order_kind not in caps.order_kinds:
        raise ValueError('Unsupported asset class or order type')
    if intent.side not in ('BUY','SELL'):
        raise ValueError('Invalid side')
    if intent.quantity_unit not in ('BASE','QUOTE','CONTRACTS','STAKE'):
        raise ValueError('Invalid quantity unit')
    if intent.asset_class == AssetClass.BINARY:
        if intent.order_kind != OrderKind.BINARY_DIRECTION or not caps.supports_expiry:
            raise ValueError('Binary orders require expiry support')
        if intent.expiration_seconds is None or intent.expiration_seconds <= 0:
            raise ValueError('Binary expiry required')
        if intent.quantity_unit != 'STAKE':
            raise ValueError('Binary stake required')
    elif intent.expiration_seconds is not None:
        raise ValueError('Binary expiry is not a spot/forex/equity exit')
    if intent.asset_class == AssetClass.CRYPTO_SPOT and intent.side == 'SELL':
        # Selling a long is allowed, but opening an uncovered short is not.
        if not intent.metadata.get('source_position_id'):
            raise ValueError('Spot SELL requires a tracked source position')

BROKER_CATALOG = {
    'coinbase': Capabilities(frozenset({AssetClass.CRYPTO_SPOT}),frozenset({OrderKind.MARKET}),supports_fills=True),
    'pocket_option': Capabilities(frozenset({AssetClass.BINARY}),frozenset({OrderKind.BINARY_DIRECTION}),supports_expiry=True),
    'oanda': Capabilities(frozenset({AssetClass.FOREX,AssetClass.CFD}),frozenset({OrderKind.MARKET,OrderKind.LIMIT}),supports_short=True,supports_native_stops=True,supports_fills=True),
    'alpaca': Capabilities(frozenset({AssetClass.EQUITY,AssetClass.CRYPTO_SPOT}),frozenset({OrderKind.MARKET,OrderKind.LIMIT}),supports_fills=True),
    'interactive_brokers': Capabilities(frozenset({AssetClass.EQUITY,AssetClass.FOREX}),frozenset({OrderKind.MARKET,OrderKind.LIMIT}),supports_fills=True,supports_native_stops=True),
    'mt5': Capabilities(frozenset({AssetClass.FOREX,AssetClass.CFD}),frozenset({OrderKind.MARKET,OrderKind.LIMIT}),supports_short=True,supports_native_stops=True),
}
# Catalog describes target adapter capabilities, NOT completed or approved integrations.
# live_supported=False for every entry until separately verified and enabled.
