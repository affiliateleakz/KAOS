"""Exercise the real staging script against a local fake SSH/SCP transport."""
import os
import importlib.util
from zipfile import ZipFile
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[1] / 'asura_stage.sh'
SHA = 'a' * 40


def setup(tmp_path):
    home = tmp_path / 'remote'
    home.mkdir()
    tools = tmp_path / 'bin'
    tools.mkdir()
    (tools / 'ssh').write_text('#!/bin/bash\nshift\nexec "$@"\n')
    (tools / 'scp').write_text('''#!/bin/bash
set -euo pipefail
target="${@: -1}"
target="${target#kaos-host:}"
cp "${@:1:$#-1}" "$HOME/$target"
''')
    for p in tools.iterdir():
        p.chmod(0o755)
    dist = tmp_path / 'dist'
    dist.mkdir()
    for name, files in {
        'kaos-cpanel-website.zip': {'index.html':'website','privacy.html':'privacy','.htaccess':'routing'},
        'kaos-cpanel-backend.zip': {'passenger_wsgi.py':'adapter','apps/api/server.py':'api','apps/api/requirements.txt':'dependencies'}
    }.items():
        with ZipFile(dist / name,'w') as archive:
            for filename,content in files.items():archive.writestr(filename,content)
    result = subprocess.run(['sha256sum', 'kaos-cpanel-website.zip', 'kaos-cpanel-backend.zip'], cwd=dist, capture_output=True, check=True)
    (dist / 'SHA256SUMS').write_bytes(result.stdout)
    (dist / 'RELEASE.txt').write_text(f'KAOS revision {SHA}\n')
    env = dict(os.environ, HOME=str(home), PATH=f'{tools}:{os.environ["PATH"]}', GIT_SHA=SHA)
    return home, dist, env


def run(tmp_path, env):
    return subprocess.run(['bash', str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True)


def test_private_verified_release_and_no_overwrite(tmp_path):
    home, _, env = setup(tmp_path)
    assert run(tmp_path, env).returncode == 0
    release = home / 'kaos_cpanel_releases' / SHA
    assert (release / 'COMPLETE').read_text().strip() == SHA
    # End-to-end handoff: real activation verifier finds and accepts SSH-staged files.
    spec=importlib.util.spec_from_file_location('activate_staged',SCRIPT.with_name('cpanel_activate.py'))
    activate=importlib.util.module_from_spec(spec);spec.loader.exec_module(activate)
    web,backend=activate.verified_packages(release,SHA)
    assert web['index.html']==b'website' and backend['apps/api/server.py']==b'api'
    assert not (home/'tradingwithkaos.com').exists()
    assert release.stat().st_mode & 0o777 == 0o700
    assert (release / 'kaos-cpanel-backend.zip').stat().st_mode & 0o777 == 0o600
    assert run(tmp_path, env).returncode != 0


def test_refuse_symlink_to_live_directory(tmp_path):
    home, _, env = setup(tmp_path)
    live = home / 'public_html'
    live.mkdir()
    (home / 'kaos_cpanel_releases').symlink_to(live)
    assert run(tmp_path, env).returncode != 0
    assert not list(live.iterdir())


def test_checksum_failure_never_marks_complete(tmp_path):
    home, dist, env = setup(tmp_path)
    (dist / 'kaos-cpanel-backend.zip').write_bytes(b'corrupt')
    assert run(tmp_path, env).returncode != 0
    assert not (home / 'kaos_cpanel_releases' / SHA / 'COMPLETE').exists()


def test_invalid_sha_cannot_reach_remote(tmp_path):
    home, _, env = setup(tmp_path)
    env['GIT_SHA'] = '../public_html;echo injected'
    assert run(tmp_path, env).returncode != 0
    assert not list(home.iterdir())
