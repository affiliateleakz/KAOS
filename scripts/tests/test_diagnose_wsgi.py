import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('wsgi_diagnostic',Path(__file__).resolve().parents[1]/'diagnose_cpanel_wsgi.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_probes_only_health_and_empty_login_without_exposing_response(monkeypatch,capsys):
    calls=[]
    def app(env,start):
        calls.append((env['REQUEST_METHOD'],env['PATH_INFO'],env['wsgi.input'].read()))
        if env['REQUEST_METHOD']=='GET':start('200 OK',[]);return [b'{"status":"ok"}']
        start('422 Unprocessable Entity',[]);return [b'private-response-withheld']
    monkeypatch.setattr(probe.runpy,'run_path',lambda path:{'application':app})
    assert probe.main()==0
    assert calls==[('GET','/api',b''),('POST','/api/auth/login',b'{}')]
    assert 'private-response-withheld' not in capsys.readouterr().out


def test_probe_errors_hide_exception_values(monkeypatch,capsys):
    def fail(path):raise RuntimeError('sensitive-config-value')
    monkeypatch.setattr(probe.runpy,'run_path',fail)
    assert probe.main()==1
    output=capsys.readouterr().out
    assert 'RuntimeError' in output and 'sensitive-config-value' not in output
