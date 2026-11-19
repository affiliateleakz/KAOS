import http.client
from http.server import ThreadingHTTPServer
from threading import Thread
import pytest
import server


@pytest.fixture
def endpoint(monkeypatch):
    monkeypatch.delenv('KAOS_RESEARCH_TOKEN', raising=False)
    monkeypatch.setenv('KAOS_RESEARCH_ALLOWED_ORIGINS', 'chrome-extension://gbobopmnjgeeegniphckfpalhnebapjm')
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    def request(method, path, headers=None, body=None):
        conn = http.client.HTTPConnection(*httpd.server_address, timeout=2)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result
    yield request
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def test_untrusted_websites_cannot_invoke_local_research(endpoint):
    status, headers, _ = endpoint('POST', '/research', {'Origin': 'https://untrusted.example'}, '{}')
    assert status == 403
    assert 'Access-Control-Allow-Origin' not in headers


def test_preflight_has_exact_origin_and_no_wildcard(endpoint):
    origin = 'chrome-extension://gbobopmnjgeeegniphckfpalhnebapjm'
    status, headers, _ = endpoint('OPTIONS', '/research', {'Origin': origin})
    assert status == 200
    assert headers['Access-Control-Allow-Origin'] == origin
    assert 'Authorization' in headers['Access-Control-Allow-Headers']


def test_negative_content_length_is_rejected_before_reading(endpoint):
    status, _, _ = endpoint('POST', '/research', {'Content-Length': '-1'})
    assert status == 400


def test_optional_token_protects_archive_and_costly_research(endpoint, monkeypatch):
    monkeypatch.setenv('KAOS_RESEARCH_TOKEN', 'test-only')
    assert endpoint('POST', '/research', {}, '{}')[0] == 401
    assert endpoint('GET', '/kaos-ai/archive')[0] == 401
    assert endpoint('POST', '/research', {'Authorization': 'Bearer test-only'}, '{}')[0] == 400


def test_null_and_wildcard_origins_are_never_allowed(monkeypatch):
    monkeypatch.setenv('KAOS_RESEARCH_ALLOWED_ORIGINS', '*,null')
    assert not server.origin_allowed('null')
    assert not server.origin_allowed('https://untrusted.example')


def test_dns_rebinding_host_is_rejected_even_without_origin(endpoint):
    assert endpoint('GET', '/kaos-ai/archive', {'Host': 'untrusted.example'})[0] == 403
