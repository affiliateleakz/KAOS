"""Build upload-ready cPanel ZIPs from validated KAOS source + compiled React build.

No deployment, secrets, credentials, or live-trading settings are included.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sys

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
WEB_BUILD = ROOT / "apps" / "web" / "build"
API = ROOT / "apps" / "api"
CORE = ROOT / "packages" / "kaos-core"
PASSENGER = ROOT / "deploy" / "cpanel" / "passenger_wsgi.py"
HTACCESS = ROOT / "deploy" / "cpanel" / "frontend.htaccess"

SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", ".venv", "venv", "node_modules"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".zip", ".log", ".sqlite", ".db", ".pem", ".key"}
SKIP_FILES = {".env", ".env.local", ".env.production", ".env.staging", ".DS_Store"}


def permitted(path: Path) -> bool:
    return (path.is_file() and not any(p in SKIP_DIRS for p in path.parts)
            and path.name not in SKIP_FILES and not path.name.startswith(".env.")
            and path.suffix.lower() not in SKIP_SUFFIXES)


def pack(output: Path, mappings):
    names = set()
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for source, prefix in mappings:
            if source.is_file():
                items = [(source, prefix)]
            elif source.is_dir():
                items = [(p, f"{prefix}/{p.relative_to(source).as_posix()}".lstrip("/"))
                         for p in sorted(source.rglob("*")) if permitted(p) and not (source == WEB_BUILD and p.name == ".htaccess")]
            else:
                raise RuntimeError(f"Missing required package input: {source}")
            for path, name in items:
                name = name.lstrip("/")
                if name in names:
                    raise RuntimeError(f"Duplicate ZIP entry: {name}")
                names.add(name)
                z.write(path, name)
    with ZipFile(output) as z:
        if z.testzip() is not None:
            raise RuntimeError(f"Invalid ZIP: {output}")
    print(f"Created {output} ({len(names)} files)")


def main():
    if not (WEB_BUILD / "index.html").exists():
        sys.exit("Compile apps/web first (npm ci && npm run build)")
    if not (WEB_BUILD / "privacy.html").exists():
        sys.exit("Privacy policy missing from compiled website")
    for p in (API / "server.py", API / "requirements.txt", CORE, PASSENGER, HTACCESS):
        if not p.exists():
            sys.exit(f"Required release input missing: {p}")
    DIST.mkdir(exist_ok=True)
    # Extract directly into the website document root (e.g., public_html).
    pack(DIST / "kaos-cpanel-website.zip", [
        (WEB_BUILD, ""),
        (HTACCESS, ".htaccess"),
    ])
    # Extract into the Python app root, NOT public_html.
    pack(DIST / "kaos-cpanel-backend.zip", [
        (PASSENGER, "passenger_wsgi.py"),
        (API, "apps/api"),
        (CORE, "packages/kaos-core"),
    ])


if __name__ == "__main__":
    main()
