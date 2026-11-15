"""Passenger entry point for KAOS FastAPI under the repository-shaped cPanel app root.

Expected layout: APP_ROOT/apps/api and APP_ROOT/packages/kaos-core.
"""
import os
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
def _get_app():
    from server import app
    return app

# Create the event-loop thread inside the serving worker, not a preloaded parent.
import threading
_adapter = None
_adapter_pid = None
_process_pid = os.getpid()
_adapter_lock = threading.Lock()

def _after_fork():
    global _adapter, _adapter_pid, _adapter_lock, _process_pid
    _adapter = None
    _adapter_pid = None
    _adapter_lock = threading.Lock()
    _process_pid = os.getpid()

if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork)

def application(environ, start_response):
    global _adapter, _adapter_pid
    pid = os.getpid()
    # Native host forks need not invoke Python at-fork callbacks. Reset before locking.
    if _process_pid != pid:
        _after_fork()
    with _adapter_lock:
        if _adapter is None or _adapter_pid != pid:
            _adapter = ASGIMiddleware(_get_app())
            _adapter_pid = pid
        adapter = _adapter
    return adapter(environ, start_response)
