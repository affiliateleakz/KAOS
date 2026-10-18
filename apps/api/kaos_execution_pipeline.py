"""KAOS 2.0 paper-only signal-to-order pipeline.
No live broker calls. No fictional fills. Caller supplies verified market snapshots.
"""
from dataclasses import replace
from kaos_broker_core import OrderIntent
from kaos_risk_engine import check_order, RiskRejected
from kaos_broker_registry import BrokerUnavailable

class PaperExecutionPipeline:
    def __init__(self, registry, limits):
        self.registry, self.limits = registry, limits
        self._seen = {}  # paper-mode only; durable storage needed for production

    async def submit(self, intent: OrderIntent, snapshot, *, closing_position=False):
        key = (intent.user_id, intent.broker, intent.account_id, intent.client_order_id)
        if key in self._seen:
            previous_intent, report = self._seen[key]
            if previous_intent != intent:
                raise RiskRejected("Reused client order ID with different order details")
            return report
        registration = self.registry._adapters.get(intent.broker)
        if registration is None or not registration.enabled or not registration.paper_only:
            raise BrokerUnavailable("No enabled paper adapter")
        check_order(intent, registration.adapter.capabilities, self.limits,
                    snapshot, live=False, closing_position=closing_position)
        report = await self.registry.submit(intent, paper=True)
        self._seen[key] = (intent, report)
        return report
