"""Fail-closed KAOS adapter registration and broker-neutral order dispatch.

Only adapters explicitly installed and enabled by the server can receive orders.
The catalog is documentation, never an execution permission grant.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
from kaos_broker_core import BrokerAdapter, Capabilities, OrderIntent, ExecutionReport, OrderState, validate_intent


class BrokerUnavailable(RuntimeError):
    pass


@dataclass
class AdapterRegistration:
    adapter: BrokerAdapter
    enabled: bool = False
    paper_only: bool = True


class BrokerRegistry:
    def __init__(self):
        self._adapters: Dict[str, AdapterRegistration] = {}

    def register(self, adapter: BrokerAdapter, *, enabled: bool = False, paper_only: bool = True):
        name = adapter.broker_id
        if not name or name in self._adapters:
            raise ValueError('Missing or duplicate broker adapter')
        if enabled and not paper_only and not adapter.capabilities.live_supported:
            raise BrokerUnavailable('Broker not certified for live execution')
        self._adapters[name] = AdapterRegistration(adapter, enabled, paper_only)

    def status(self):
        return {name: {'registered': True, 'enabled': r.enabled,
                       'paper_only': r.paper_only,
                       'live_certified': r.adapter.capabilities.live_supported}
                for name, r in sorted(self._adapters.items())}

    async def submit(self, intent: OrderIntent, *, paper: bool = True) -> ExecutionReport:
        reg = self._adapters.get(intent.broker)
        if not reg or not reg.enabled:
            raise BrokerUnavailable('Broker adapter is not enabled')
        if intent.broker != reg.adapter.broker_id:
            raise BrokerUnavailable('Broker identity mismatch')
        validate_intent(intent, reg.adapter.capabilities)
        if not paper:
            if reg.paper_only or not reg.adapter.capabilities.live_supported:
                raise BrokerUnavailable('Live broker execution is disabled')
            # Real-money dispatch must additionally enforce account authorization,
            # persistent reservations and risk controls at the authenticated API boundary.
            raise BrokerUnavailable('Live dispatch requires server-owned execution gateway')
        if not reg.paper_only:
            raise BrokerUnavailable('Paper orders require a dedicated paper adapter')
        report = await reg.adapter.submit(intent)
        if report.broker != intent.broker or report.account_id != intent.account_id or report.client_order_id != intent.client_order_id:
            raise BrokerUnavailable('Broker execution report identity mismatch')
        return report
