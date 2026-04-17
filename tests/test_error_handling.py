import requests
import pytest
from fastapi.testclient import TestClient

from web.main import app


@pytest.fixture
def client():
    # Temporarily add test routes to the production app for exception handler testing.
    # These routes are never registered in production — they're added only in-process
    # during testing and don't persist after the test process exits.
    @app.get("/test/http-error")
    def _raise_http_error():
        raise requests.HTTPError("Yahoo said no")

    @app.get("/test/unhandled")
    def _raise_unhandled():
        raise Exception("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_health_still_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_http_error_returns_502(client):
    resp = client.get("/test/http-error")
    assert resp.status_code == 502


def test_http_error_returns_html(client):
    resp = client.get("/test/http-error")
    assert "text/html" in resp.headers["content-type"]


def test_http_error_contains_yahoo_message(client):
    resp = client.get("/test/http-error")
    assert "Yahoo API request failed" in resp.text


def test_500_handler_fires_for_bare_exception(client):
    resp = client.get("/test/unhandled")
    assert resp.status_code == 500


def test_500_handler_returns_html(client):
    resp = client.get("/test/unhandled")
    assert "text/html" in resp.headers["content-type"]


def test_500_handler_contains_error_message(client):
    resp = client.get("/test/unhandled")
    assert "Something went wrong" in resp.text
