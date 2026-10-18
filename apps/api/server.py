import os
import logging
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db import db, ensure_indexes
import routes_auth, routes_strategies, routes_community, routes_billing, routes_extension, routes_admin, routes_trading, routes_affiliate, routes_botsync, routes_ai
import seed
import routes_coinbase
import routes_finbert
import routes_opportunity
import routes_paper
import routes_broker_selection
import routes_research_replay

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=["600/minute"])
app = FastAPI(title="KAOS Trading API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/api")
async def api_root():
    return {"service": "KAOS Trading API", "status": "ok"}


# Secure headers
@app.get("/api/health")
async def health():
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


for mod in (routes_auth, routes_strategies, routes_community, routes_billing,
            routes_extension, routes_admin, routes_trading, routes_affiliate,
            routes_botsync, routes_ai):
    for attr in ("router", "social", "webhook_router", "v1", "member", "v1t", "mt", "at",
                 "aff", "aff_admin", "public", "bot", "v1ai", "mai", "aai", "share"):
        r = getattr(mod, attr, None)
        if r is not None:
            app.include_router(r)

app.include_router(routes_coinbase.router)
app.include_router(routes_finbert.router)
app.include_router(routes_opportunity.router)
app.include_router(routes_paper.router)
app.include_router(routes_broker_selection.router)
app.include_router(routes_research_replay.router)

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    import services_affiliate_ledger
    await services_affiliate_ledger.ensure_indexes()
    await seed.seed_admin()
    await seed.seed_demo()
    await seed.write_credentials()
    logger.info("Startup complete: indexes, admin, demo data seeded.")


@app.on_event("shutdown")
async def shutdown():
    pass
