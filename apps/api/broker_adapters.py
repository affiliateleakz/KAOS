"""Shared broker adapter layer: one interface for every broker, one registry the clients read.

Each adapter plugs into the same KAOS auth, vault, risk checks and live-order gate. An adapter existing
does not mean the broker is connected: `status` is one of STATES, advanced only on evidence.
Unbuilt adapters answer 501 with what access they need.
"""
from dataclasses import dataclass, field
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user


STATES = ("planned", "adapter_development", "authentication_implemented", "read_only_verified",
          "order_management_tested", "trading_approved", "temporarily_unavailable")


@dataclass
class BrokerAdapter:
    id: str
    name: str
    asset_classes: tuple
    status: str  # one of STATES
    integration: str
    requires: str
    capabilities: dict = field(default_factory=lambda: {"account": False, "preview": False, "submit": False, "cancel": False})

    async def account(self, user):
        raise HTTPException(501, f"{self.name} adapter not built yet. Needs: {self.requires}")

    async def preview(self, user, order):
        raise HTTPException(501, f"{self.name} order preview not built yet. Needs: {self.requires}")


class AlpacaAdapter(BrokerAdapter):
    async def account(self, user):
        import routes_broker_alpaca
        return await routes_broker_alpaca.account(user=user)


class OandaAdapter(BrokerAdapter):
    async def account(self, user):
        import routes_broker_oanda
        return await routes_broker_oanda.account(user=user)


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
    CoinbaseAdapter("coinbase", "Coinbase Advanced", ("crypto",), "authentication_implemented", "Advanced Trade REST API",
                    "Member's CDP key (View for account data; Trade for preview/orders)",
                    {"account": True, "preview": True, "submit": "disabled", "cancel": True}),
    AlpacaAdapter("alpaca", "Alpaca", ("stocks", "options", "crypto"), "authentication_implemented", "Paper Trading API: authenticated read-only account, positions, orders", "Member paper API key/secret; real account and live orders unsupported", {"account": True, "preview": False, "submit": False, "cancel": False}),
    BrokerAdapter("ibkr", "Interactive Brokers", ("stocks", "options", "futures", "forex"), "planned", "Client Portal / TWS gateway", "IBKR account and a running gateway"),
    OandaAdapter("oanda", "OANDA", ("forex",), "authentication_implemented", "v20 Practice API read-only", "Practice account ID and API token; real trading unsupported", {"account": True, "preview": False, "submit": False, "cancel": False}),
    BrokerAdapter("kraken", "Kraken", ("crypto",), "planned", "Spot REST API", "Kraken account + API key (no withdraw permission)"),
    BrokerAdapter("tradier", "Tradier", ("stocks", "options"), "planned", "Brokerage API (OAuth)", "Tradier account + OAuth app"),
    BrokerAdapter("tastytrade", "tastytrade", ("stocks", "options", "futures"), "planned", "Open API", "tastytrade account + API access approval"),
    BrokerAdapter("mt5", "MetaTrader 5 brokers", ("forex", "CFDs"), "planned", "MetaTrader 5 terminal/gateway per broker",
                  "MT5 account at a broker that permits API/EA access; a running terminal or bridge"),
    BrokerAdapter("pocketoption", "Pocket Option", ("binary options",), "adapter_development", "Chrome extension on the broker page (no public API); repair in progress",
                  "Written permission from Pocket Option for any API/automated access"),
    # Popular retail brokers: listed for discovery only. No account or order endpoints are enabled.
    # API access and commercial authorization must be established broker-by-broker.
    BrokerAdapter("robinhood", "Robinhood", ("stocks", "options", "crypto"), "planned",
                  "Official crypto API; stock/options third-party execution not established",
                  "Confirm broker-authorized commercial access and asset-specific execution permissions"),
    BrokerAdapter("schwab", "Charles Schwab / thinkorswim", ("stocks", "options", "futures"), "planned",
                  "Schwab developer platform; thinkorswim is a trading interface",
                  "Approved Schwab developer application, OAuth scopes, and commercial access"),
    BrokerAdapter("fidelity", "Fidelity", ("stocks", "options"), "planned",
                  "Third-party retail trading API availability unverified",
                  "Written broker approval and documented account/trading API"),
    BrokerAdapter("webull", "Webull", ("stocks", "options", "futures", "crypto"), "planned",
                  "Official OpenAPI; product availability depends on account and region",
                  "OpenAPI access eligibility, app approval, permissions and commercial terms"),
    BrokerAdapter("etrade", "E*TRADE", ("stocks", "options"), "planned",
                  "E*TRADE developer API, subject to eligibility and approval",
                  "Approved developer credentials, OAuth and permitted account/order scopes"),
    BrokerAdapter("crypto_com", "Crypto.com", ("crypto",), "planned",
                  "Crypto.com Exchange API, distinct from retail app",
                  "Eligible exchange account and authorized Exchange API key"),
    BrokerAdapter("tradestation", "TradeStation", ("stocks", "options", "futures"), "planned",
                  "TradeStation API subject to eligibility and application approval",
                  "Approved API access and brokerage account"),
    BrokerAdapter("forex_com", "FOREX.com", ("forex",), "planned",
                  "Broker API availability and regional permissions require verification",
                  "Eligible account and approved broker API access"),
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
