"""Security checks that do not connect to MongoDB."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.main import app


# Do not enter the lifespan: these requests must work or fail before database access.
client = TestClient(app, base_url="http://127.0.0.1")


def test_only_local_hostnames_are_accepted():
    assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400
    assert client.get("/", headers={"Host": "localhost:8000"}).status_code == 200


def test_browser_security_headers_and_private_files():
    page = client.get("/")
    assert page.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert client.get("/.env").status_code == 404
    assert client.get("/static/.env").status_code == 404
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/tasks" in schema.json()["paths"]


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_cross_origin_writes_are_rejected(method):
    response = client.request(
        method, "/api/tasks", headers={"Origin": "https://untrusted.example"}
    )
    assert response.status_code == 403


def test_mutations_require_json():
    response = client.post("/api/tasks", data={"title": "Should not save"})
    assert response.status_code == 415


@pytest.mark.parametrize("option", [
    "tlsInsecure", "tlsAllowInvalidCertificates", "tlsAllowInvalidHostnames"
])
def test_unsafe_tls_options_are_rejected_without_leaking_uri(option):
    uri = f"mongodb://example-user:example-password@localhost/little_wins?{option}=true"
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, mongodb_uri=uri)
    assert "TLS verification bypass" in str(error.value)
    assert "example-password" not in str(error.value)
