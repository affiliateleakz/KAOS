"""Paper-only risk-first dispatch with durable idempotency across restarts.
UNKNOWN reservations require manual review; no automatic retry after crash.
"""
import json
from kaos_broker_core import ExecutionReport, OrderState
from kaos_broker_registry import BrokerUnavailable
from kaos_risk_engine import check_order, RiskRejected
from kaos_paper_journal import JournalConflict


class DurablePaperPipeline:
    def __init__(self, registry, limits, journal):
        self.registry, self.limits, self.journal = registry, limits, journal

    async def submit(self, intent, snapshot, *, closing_position=False):
        registration = self.registry._adapters.get(intent.broker)
        if registration is None or not registration.enabled or not registration.paper_only:
            raise BrokerUnavailable('No enabled paper adapter')
        # Risk check precedes first reservation; replay still cannot bypass identity check.
        check_order(intent, registration.adapter.capabilities, self.limits, snapshot,
                    live=False, closing_position=closing_position)
        try:
            state, report_json = self.journal.reserve(intent)
        except JournalConflict as exc:
            raise RiskRejected(str(exc)) from exc
        if state != 'NEW':
            if report_json is None:
                raise RiskRejected('UNKNOWN paper reservation: manual reconciliation required; no resubmit')
            data = json.loads(report_json)
            data['state'] = OrderState(data['state'])
            return ExecutionReport(**data)
        try:
            report = await self.registry.submit(intent, paper=True)
        except Exception:
            # A transport failure may have occurred after broker acceptance.
            # Leave reservation UNKNOWN and fail closed.
            raise
        self.journal.finish(intent, report)
        return report
