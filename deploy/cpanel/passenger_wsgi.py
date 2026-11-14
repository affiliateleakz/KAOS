"""Passenger entry point for KAOS FastAPI under the repository-shaped cPanel app root.

Expected layout: APP_ROOT/apps/api and APP_ROOT/packages/kaos-core.
"""
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent
API_ROOT = APP_ROOT / "apps" / "api"
CORE_ROOT = APP_ROOT / "packages" / "kaos-core"

for path in (API_ROOT, CORE_ROOT):
    if not path.is_dir():
        raise RuntimeError(f"Required application directory not found: {path}")
    sys.path.insert(0, str(path))

from a2wsgi import ASGIMiddleware
from server import app

application = ASGIMiddleware(app)
