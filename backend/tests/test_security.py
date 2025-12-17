
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_security_headers_presence():
    """
    Verify that critical security headers are present in API responses.
    """
    response = client.get("/api/health")
    assert response.status_code == 200

    # Prevent MIME-sniffing
    assert response.headers.get("x-content-type-options") == "nosniff"

    # Prevent clickjacking
    assert response.headers.get("x-frame-options") == "DENY"

    # XSS Protection
    assert response.headers.get("x-xss-protection") == "1; mode=block"

    # Referrer Policy
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

def test_security_headers_on_404():
    """
    Verify that security headers are present even on error responses.
    """
    response = client.get("/non-existent-endpoint")
    assert response.status_code == 404

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
