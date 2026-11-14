"""htmx and Alpine are served from web/static/vendor/, not CDNs (see docs/DECISIONS.md)."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from web.main import app

client = TestClient(app)


def test_pages_load_no_external_scripts():
    body = client.get("/demo/waiver").text
    srcs = re.findall(r'<script[^>]*src="([^"]+)"', body)
    assert srcs, "expected script tags"
    assert all(src.startswith("/static/") for src in srcs), srcs


def test_vendored_scripts_are_served():
    body = client.get("/demo/waiver").text
    for src in re.findall(r'<script[^>]*src="([^"]+)"', body):
        response = client.get(src)
        assert response.status_code == 200, src
        assert len(response.content) > 10_000, src
