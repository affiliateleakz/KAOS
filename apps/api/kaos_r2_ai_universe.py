"""Curated, owner-managed R2 AI research universe (not an order universe).

Enrollment does not create source candles or grant broker/AI execution authority.
Scheduled jobs consume this roster in bounded rotations.
"""
from kaos_r2_market_audit import MARKETS as BASE_MARKETS

STOCKS = ["AAPL","NVDA","MSFT","AMZN","GOOGL","META","TSLA","AMD","PLTR","COIN","AVGO","ORCL","CRM","ADBE","NFLX","INTC","MU","QCOM","TXN","AMAT","LRCX","KLAC","ASML","ARM","SMCI","DELL","IBM","CSCO","NOW","SNOW","PANW","CRWD","NET","DDOG","MDB","SHOP","UBER","ABNB","DASH","PYPL","SQ","HOOD","SOFI","JPM","BAC","WFC","GS","MS","V","MA","AXP","C","SCHW","BLK","UNH","JNJ","ABBV","MRK","PFE","LLY","TMO","ABT","ISRG","GILD","REGN","COST","WMT","TGT","HD","LOW","MCD","SBUX","NKE","DIS","CMCSA","KO","PEP","PG","CAT","DE","GE","BA","F","GM","RIVN","XOM","CVX","COP","OXY","SLB"]
ETFS = ["SPY","QQQ","IWM","DIA","XLK","XLF","XLE","XLI","XLY","XLP","XLU","XLV","XLB","SMH","SOXX","GLD","SLV","TLT","HYG","ARKK"]
CRYPTO = ["BTC-USD","ETH-USD","SOL-USD","XRP-USD","DOGE-USD","ADA-USD","LINK-USD","AVAX-USD","LTC-USD","BCH-USD","DOT-USD","UNI-USD","ATOM-USD","AAVE-USD","ALGO-USD","XLM-USD","HBAR-USD","NEAR-USD","ICP-USD","FIL-USD","ETC-USD","XTZ-USD","EOS-USD","COMP-USD","MKR-USD","SUSHI-USD","SNX-USD","CRV-USD","GRT-USD","ENS-USD","OP-USD","ARB-USD","INJ-USD","SUI-USD","APT-USD","SEI-USD","FET-USD","RENDER-USD","PEPE-USD","SHIB-USD","BONK-USD","WIF-USD"]
CATALOG = tuple(dict.fromkeys(
    list(BASE_MARKETS) +
    [(symbol, "stock") for symbol in STOCKS] +
    [(symbol, "etf") for symbol in ETFS] +
    [(symbol, "crypto") for symbol in CRYPTO]
))
CATALOG_SET = set(CATALOG)
DEFAULT = tuple(BASE_MARKETS)
MAX_ENROLLED = 160

async def selected_markets(db):
    config = await db.kaos_r2_ai_universe.find_one({"_id": "owner"})
    if not config:
        return list(DEFAULT)
    selected = config.get("markets", [])
    allowed = set(tuple(pair) for pair in selected
                  if isinstance(pair, list) and len(pair) == 2
                  and all(isinstance(x, str) for x in pair))
    return [pair for pair in CATALOG if pair in allowed][:MAX_ENROLLED]

def validate_markets(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ENROLLED:
        raise ValueError("Select 1 to 160 research markets")
    pairs = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid market record")
        pair = (row.get("symbol"), row.get("asset_class"))
        if pair not in CATALOG_SET or pair in pairs:
            raise ValueError("Unknown or duplicate market")
        pairs.append(pair)
    return [pair for pair in CATALOG if pair in set(pairs)]
