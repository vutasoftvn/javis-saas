import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.platform.core.legacy_facade import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_legacy_facade_headers():
    """Test that legacy endpoints return proper Deprecation and Sunset headers."""
    response = client.post("/legacy/agent/run", json={"test": "data"})
    assert response.status_code == 200
    
    # Kiểm tra headers
    assert response.headers.get("Deprecation") == "true"
    assert response.headers.get("Sunset") is not None
    assert 'rel="replacement"' in response.headers.get("Link", "")
    
    # Đảm bảo logic đã được forward
    assert response.json()["status"] == "forwarded_to_canonical"
