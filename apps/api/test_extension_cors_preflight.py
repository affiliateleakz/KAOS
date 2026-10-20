"""Chrome extension origin must be accepted by the FastAPI CORS configuration."""
from fastapi.testclient import TestClient
from server import app

def test_extension_login_preflight_allows_published_origin():
    origin = "chrome-extension://" + "gbobopmnjgeeegniphckfpalhnebapjm"
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "content-type" in response.headers["access-control-allow-headers"].lower()

def test_unknown_extension_origin_not_allowed():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "chrome-extension://" + "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert response.headers.get("access-control-allow-origin") is None
