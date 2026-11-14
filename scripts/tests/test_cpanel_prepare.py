"""Run cPanel preparation with a fixture repository and simulated npm build."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def setup(tmp_path):
    home = tmp_path / 'home'
    repo = home / 'repositories' / 'KAOS'
    repo.mkdir(parents=True)
    for name in ('scripts/cpanel_prepare.sh', 'scripts/build_cpanel_packages.py',
                 'deploy/cpanel/passenger_wsgi.py', 'deploy/cpanel/frontend.htaccess'):
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dest)
    for name in ('apps/web/build/index.html', 'apps/web/build/privacy.html',
                 'apps/api/server.py', 'apps/api/requirements.txt',
                 'packages/kaos-core/kaos/__init__.py'):
        dest = repo / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('fixture')
    (repo / '.gitignore').write_text('dist/\napps/web/build/\n')
    python = home / 'virtualenv/tradingwithkaos.com/backend/3.11/bin/python'
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    tools = tmp_path / 'tools'
    tools.mkdir()
    for name in ('npm', 'node'):
        path = tools / name
        path.write_text('#!/bin/bash\nexit "${BUILD_FAIL:-0}"\n')
        path.chmod(0o755)
    env = dict(os.environ, HOME=str(home), PATH=f'{tools}:{os.environ["PATH"]}')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo, env=env).decode().strip()
    git('init', '-q')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-qm', 'fixture')
    return home, repo, env, git('rev-parse', 'HEAD')


def run(repo, env):
    return subprocess.run(['bash', 'scripts/cpanel_prepare.sh'], cwd=repo, env=env, capture_output=True)


def test_prepares_private_release_without_live_writes(tmp_path):
    home, repo, env, sha = setup(tmp_path)
    live = home / 'tradingwithkaos.com'
    live.mkdir()
    (live / 'index.html').write_text('original website')
    result = run(repo, env)
    assert result.returncode == 0, result.stderr.decode()
    release = home / 'kaos_cpanel_releases' / sha
    assert (release / 'COMPLETE').read_text().strip() == sha
    assert release.stat().st_mode & 0o777 == 0o700
    assert (release / 'kaos-cpanel-backend.zip').stat().st_mode & 0o777 == 0o600
    assert (live / 'index.html').read_text() == 'original website'
    assert list(live.iterdir()) == [live / 'index.html']
    assert run(repo, env).returncode != 0
    assert not (release.parent / '.prepare-lock').exists()


def test_failed_build_does_not_publish_release(tmp_path):
    home, repo, env, sha = setup(tmp_path)
    env['BUILD_FAIL'] = '1'
    assert run(repo, env).returncode != 0
    assert not (home / 'kaos_cpanel_releases' / sha).exists()
    assert not list((home / 'kaos_cpanel_releases').iterdir())


def test_refuses_modified_source(tmp_path):
    home, repo, env, _ = setup(tmp_path)
    (repo / 'apps/api/server.py').write_text('modified')
    assert run(repo, env).returncode != 0
    assert not (home / 'kaos_cpanel_releases').exists()


def test_refuses_symlink_destination(tmp_path):
    home, repo, env, _ = setup(tmp_path)
    live = home / 'tradingwithkaos.com'
    live.mkdir()
    (home / 'kaos_cpanel_releases').symlink_to(live)
    assert run(repo, env).returncode != 0
    assert not list(live.iterdir())
