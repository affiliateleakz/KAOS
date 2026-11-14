"""Verify release layout and secret exclusions with synthetic build inputs."""
import importlib.util
from pathlib import Path
from zipfile import ZipFile

spec = importlib.util.spec_from_file_location('packager', Path(__file__).resolve().parents[1] / 'build_cpanel_packages.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


def test_release_layout_and_secret_exclusions(tmp_path, monkeypatch):
    for key in ('DIST', 'WEB_BUILD', 'API', 'CORE'):
        path = tmp_path / key
        path.mkdir()
        monkeypatch.setattr(packager, key, path)
    for key, names in {'WEB_BUILD': ['index.html', 'privacy.html'], 'API': ['server.py', 'requirements.txt', '.env', '.env.production', 'secret.pem'], 'CORE': ['kaos_core/__init__.py']}.items():
        for name in names:
            path = getattr(packager, key) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture')
    secret = tmp_path / 'outside-secret'
    secret.write_text('secret')
    (packager.API / 'linked.py').symlink_to(secret)
    packager.main()
    with ZipFile(packager.DIST / 'kaos-cpanel-backend.zip') as archive:
        names = set(archive.namelist())
        assert {'passenger_wsgi.py', 'apps/api/server.py', 'apps/api/requirements.txt', 'packages/kaos-core/kaos_core/__init__.py'} <= names
        assert not any('.env' in n or 'secret.pem' in n or 'linked.py' in n for n in names)
        assert archive.testzip() is None
    with ZipFile(packager.DIST / 'kaos-cpanel-website.zip') as archive:
        assert set(archive.namelist()) == {'index.html', 'privacy.html', '.htaccess'}
