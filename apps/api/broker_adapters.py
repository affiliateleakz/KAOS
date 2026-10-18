"""Shared broker adapter layer: one interface for every broker, one registry the clients read.

Each adapter plugs into the same KAOS auth, vault, risk checks and live-order gate. Only adapters whose
status is not "not_built" do anything; the rest answer 501 with what access they need.
"""
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user


@dataclass
class BrokerAdapter:
    id: str
    name: str
    asset_classes: tuple
    status: str  # read_only_built | not_built | extension_only
    integration: str
    requires: str
    capabilities: dict = field(default_factory=lambda: {"account": False, "preview": False, "submit": False, "cancel": False})

    async def account(self, user):
        raise HTTPException(501, f"{self.name} adapter not built yet. Needs: {self.requires}")

    async def preview(self, user, order):
        raise HTTPException(501, f"{self.name} order preview not built yet. Needs: {self.requires}")


class PreviewOrder(BaseModel):
    product_id: str
    side: str
    quote_size: Optional[str] = None
    base_size: Optional[str] = None


class CoinbaseAdapter(BrokerAdapter):
    async def account(self, user):
        import routes_broker_coinbase
        return await routes_broker_coinbase.account(user=user)

    async def preview(self, user, order):
        import routes_coinbase
        return await routes_coinbase.preview(routes_coinbase.PreviewRequest(**order.model_dump()), user=user)


REGISTRY = {a.id: a for a in [
    CoinbaseAdapter("coinbase", "Coinbase Advanced", ("crypto",), "read_only_built", "Advanced Trade REST API",
                    "Member's CDP key (View for account data; Trade for preview/orders)",
                    {"account": True, "preview": True, "submit": "disabled", "cancel": "disabled"}),
    BrokerAdapter("alpaca", "Alpaca", ("stocks", "options", "crypto"), "not_built", "Trading API (OAuth or key)", "Alpaca account + API key; market-data subscription"),
    BrokerAdapter("ibkr", "Interactive Brokers", ("stocks", "options", "futures", "forex"), "not_built", "Client Portal / TWS gateway", "IBKR account and a running gateway"),
    BrokerAdapter("oanda", "OANDA", ("forex",), "not_built", "v20 REST API", "OANDA account + API token"),
    BrokerAdapter("kraken", "Kraken", ("crypto",), "not_built", "Spot REST API", "Kraken account + API key (no withdraw permission)"),
    BrokerAdapter("tradier", "Tradier", ("stocks", "options"), "not_built", "Brokerage API (OAuth)", "Tradier account + OAuth app"),
    BrokerAdapter("tastytrade", "tastytrade", ("stocks", "options", "futures"), "not_built", "Open API", "tastytrade account + API access approval"),
    BrokerAdapter("pocketoption", "Pocket Option", ("binary options",), "extension_only", "Chrome extension on the broker page (no public API)",
                  "Written permission from Pocket Option for any API/automated access"),
]}

router = APIRouter(prefix="/api/v1/brokers", tags=["brokers"])


def adapter(broker_id: str) -> BrokerAdapter:
    a = REGISTRY.get(broker_id)
    if not a:
        raise HTTPException(404, "Unknown broker")
    return a


@router.get("")
async def list_brokers():
    """Honest broker matrix: what works, what is in development, and what access each needs."""
    return {"brokers": [{"id": a.id, "name": a.name, "asset_classes": list(a.asset_classes), "status": a.status,
                         "integration": a.integration, "requires": a.requires, "capabilities": a.capabilities}
                        for a in REGISTRY.values()]}


@router.get("/{broker_id}/account")
async def broker_account(broker_id: str, user: dict = Depends(get_current_user)):
    return await adapter(broker_id).account(user)


@router.post("/{broker_id}/preview")
async def broker_preview(broker_id: str, order: PreviewOrder, user: dict = Depends(get_current_user)):
    return await adapter(broker_id).preview(user, order)
