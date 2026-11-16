"""Explicit activation of a prepared cPanel release, initially for login validation.

Never runs database migrations or ASGI startup hooks. Existing .env, .htaccess,
uploads and legacy wsgi_app.py remain in place. No files are deleted.
"""
import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
from zipfile import ZipFile

WRAPPER = '''import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from a2wsgi import ASGIMiddleware
from starlette.responses import JSONResponse

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)
os.environ["KAOS_COINBASE_LIVE_ORDERS"] = "disabled"
os.environ["KAOS_LOGIN_VALIDATION_MODE"] = "true"
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["STRIPE_WEBHOOK_SECRET"] = ""
for path in (ROOT / "apps/api", ROOT / "packages/kaos-core"):
    sys.path.insert(0, str(path))
def _get_app():
    from server import app

    if not getattr(app.state, 'kaos_validation_policy_installed', False):
        # First activation supports sign-in/device validation, not payments or orders.
        @app.middleware("http")
        async def login_validation_only(request, call_next):
            path = request.url.path
            auth = path.startswith(("/api/auth/", "/api/v1/auth/"))
            allowed_write = auth or path in (
                "/api/v1/devices/register", "/api/v1/extension/google/access-token",
                "/api/v1/ai/learning-samples", "/api/v1/trading/events", "/api/v1/ai/training/train",
                "/api/admin/ai/continuous/owner/train", "/api/admin/radar/offerings",
                "/api/affiliate/activate", "/api/affiliate/connect/onboarding",
                "/api/v1/intelligence/sync-news", "/api/v1/intelligence/scan", "/api/v1/intelligence/signals/market", "/api/v1/intelligence/social/mentions", "/api/v1/intelligence/news/feed", "/api/v1/intelligence/signals/opportunities", "/api/v1/intelligence/research/asset")
            # These handlers still enforce the authenticated owner/admin authority.
            device_revoke = (
                request.method == "DELETE" and re.fullmatch(r"/api/v1/devices/[^/]+", path)
            ) or (
                request.method == "POST" and re.fullmatch(r"/api/admin/devices/[^/]+/revoke", path)
            )
            commerce_setup = request.method in ("PUT", "POST") and bool(re.fullmatch(r"/api/admin/commerce/providers/(stripe|paypal|nowpayments)(/test)?", path))
            commerce_setup = commerce_setup or (request.method == "POST" and path == "/api/admin/commerce/vault/initialize")
            radar_setup = (request.method == "PUT" and bool(re.fullmatch(r"/api/admin/radar/providers/(options_data|alphavantage|reddit|x|bluesky|facebook|sec|ethereum|government)", path))) or (request.method == "POST" and path in ("/api/admin/radar/vault/initialize", "/api/admin/radar/model/train", "/api/admin/radar/model/activate"))
            # Social content never executes code or orders. Handlers enforce member/author/moderator permissions.
            community_write = request.method in ("POST", "PUT", "PATCH", "DELETE") and (
                path.startswith("/api/community/posts") or
                bool(re.fullmatch(r"/api/users/[^/]+/follow", path)) or
                bool(re.fullmatch(r"/api/admin/reports/[^/]+/action", path)))
            # Plan configuration is not payment activation. The handler retains admin auth and validation.
            membership_setup = False
            if request.method == "POST" and path == "/api/admin/settings":
                try:
                    payload = await request.json()
                    membership_setup = isinstance(payload, dict) and payload.get("key") == "plans"
                except ValueError:
                    pass
            allowed_write = allowed_write or bool(device_revoke) or commerce_setup or radar_setup or community_write or membership_setup or (request.method == "POST" and bool(re.fullmatch(r"/api/admin/ai/continuous/publish/[a-f0-9]{64}", path)))
            pricing_read = path in ("/api/billing/plans", "/api/billing/availability", "/api/billing/memberships") and request.method in ("GET", "HEAD", "OPTIONS")
            if ((path.startswith("/api/billing") and not pricing_read) or
                    (request.method not in ("GET", "HEAD", "OPTIONS") and not allowed_write)):
                return JSONResponse({"detail": "Login validation mode: this operation is disabled"}, status_code=503)
            return await call_next(request)
        app.state.kaos_validation_policy_installed = True
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
'''


def safe_destination(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative:
        raise ValueError('Unsafe release path')
    dest = root.joinpath(*path.parts)
    for item in (root, *dest.parents, dest):
        if item.is_symlink():
            raise ValueError('Refusing symlink destination')
    return dest


def read_package(path, backend):
    result = {}
    with ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError('Invalid release ZIP')
        for info in archive.infolist():
            name = info.filename
            safe_destination(Path('/placeholder'), name)
            if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Unexpected directory/symlink ZIP entry')
            if name in result:
                raise ValueError('Duplicate release path')
            if backend:
                if name != 'passenger_wsgi.py' and not name.startswith(('apps/api/', 'packages/kaos-core/')):
                    raise ValueError('Unexpected backend path')
            elif name.startswith(('backend/', 'apps/', 'packages/', 'uploads/')):
                raise ValueError('Unexpected website path')
            if any(part.startswith('.env') for part in PurePosixPath(name).parts):
                raise ValueError('Environment files must not come from Git')
            result[name] = archive.read(info)
    required = {'passenger_wsgi.py', 'apps/api/server.py', 'apps/api/requirements.txt'} if backend else {'index.html', 'privacy.html', '.htaccess'}
    if not required <= result.keys():
        raise ValueError('Incomplete release package')
    return result


def verified_packages(release, sha):
    if (release / 'COMPLETE').read_text().strip() != sha:
        raise ValueError('Release is incomplete')
    if (release / 'RELEASE.txt').read_text().strip() != f'KAOS revision {sha}':
        raise ValueError('Release revision mismatch')
    sums = {}
    for line in (release / 'SHA256SUMS').read_text().splitlines():
        digest, name = line.split()
        sums[name] = digest
    for name in ('kaos-cpanel-website.zip', 'kaos-cpanel-backend.zip'):
        if hashlib.sha256((release / name).read_bytes()).hexdigest() != sums.get(name):
            raise ValueError('Release checksum mismatch')
    return (read_package(release / 'kaos-cpanel-website.zip', False),
            read_package(release / 'kaos-cpanel-backend.zip', True))


def write_file(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.kaos-install-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(site, web, backend):
    # Validate every destination before writing anything.
    api = safe_destination(site, 'backend')
    for name in web:
        safe_destination(site, name)
    for name in backend:
        safe_destination(api, name)
    if not (api / '.env').is_file() or not (site / '.htaccess').is_file():
        raise ValueError('Existing backend .env and website routing are required')
    # New source paths must not be directly downloadable on the API hostname.
    rule = '\n# KAOS private application sources\nRewriteEngine On\nRewriteRule ^(?:apps|packages)(?:/|$) - [F,L,NC]\n<FilesMatch "^(?:\\.env.*|.*\\.(?:py|pyc))$">\nRequire all denied\n</FilesMatch>\n'
    access = safe_destination(api, '.htaccess')
    previous = access.read_bytes() if access.exists() else b''
    if b'# KAOS private application sources' not in previous:
        write_file(access, previous + rule.encode(), 0o644)
    for name, data in backend.items():
        if name != 'passenger_wsgi.py':
            write_file(safe_destination(api, name), data, 0o600)
    for name, data in web.items():
        if name not in ('.htaccess', 'index.html'):
            dest = safe_destination(site, name)
            write_file(dest, data, 0o644)
            for parent in dest.parents:
                if parent == site:
                    break
                parent.chmod(0o755)
    write_file(site / 'index.html', web['index.html'], 0o644)
    # Switch only after all release files have been installed.
    write_file(api / 'passenger_wsgi.py', WRAPPER.encode(), 0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--activate', action='store_true')
    parser.add_argument('--entrypoint-only', action='store_true', help='Refresh only the startup adapter')
    args = parser.parse_args()
    sha = args.revision
    if len(sha) != 40 or any(c not in '0123456789abcdef' for c in sha):
        parser.error('A full lowercase commit SHA is required')
    home = Path.home()
    site = home / 'tradingwithkaos.com'
    release = home / 'kaos_cpanel_releases' / sha
    if release.is_symlink() or release.parent.is_symlink():
        raise ValueError('Refusing symlink release directory')
    web, backend = verified_packages(release, sha)
    print(f'Verified website and backend release {sha}')
    print(f'Destination: {site}; existing root .htaccess and backend .env preserved')
    if not args.activate:
        print('Check only. Use --activate to install in login-validation mode.')
        return
    # Validate dependencies/settings before live writes. No startup or DB query.
    python = home / 'virtualenv/tradingwithkaos.com/backend/3.11/bin/python'
    with tempfile.TemporaryDirectory(prefix='kaos-preflight-', dir=home) as temporary:
        candidate = Path(temporary)
        for name, data in backend.items():
            if name != 'passenger_wsgi.py':
                dest = safe_destination(candidate, name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        check = ('import sys; from dotenv import load_dotenv; '
                 'load_dotenv(sys.argv[1], override=False); '
                 'import os; assert all(os.getenv(k) for k in ("MONGO_URL","DB_NAME","JWT_SECRET","FRONTEND_URL")); '
                 'from server import app; import a2wsgi; print("Backend preflight OK")')
        env = dict(os.environ, PYTHONPATH=f'{candidate}/apps/api:{candidate}/packages/kaos-core')
        subprocess.run([str(python), '-c', check, str(site / 'backend/.env')], env=env, check=True)
    if args.entrypoint_only:
        write_file(safe_destination(site, 'backend/passenger_wsgi.py'), WRAPPER.encode(), 0o600)
    else:
        install(site, web, backend)
    print('Files installed. Restart the API in cPanel, then check /api and extension sign-in.')
    print('Payments and live orders remain disabled; member research and community actions are permitted.')
    print('Legacy wsgi_app.py remains available; no database migration or full backup was performed.')


if __name__ == '__main__':
    main()
