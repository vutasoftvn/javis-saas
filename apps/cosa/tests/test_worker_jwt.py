import os
import pytest
import jwt
from apps.cosa.auth.jwt import mint_worker_service_jwt
from apps.cosa.company.executive_board_client import ExecutiveBoardClient
from apps.cosa.company.project_team_client import ProjectTeamClient

def test_mint_worker_service_jwt_claims():
    token = mint_worker_service_jwt(worker_id="test-worker-123", ttl_seconds=120)
    payload = jwt.decode(
        token,
        "test-worker-jwt-secret-min-32-chars-long-fixture",
        algorithms=["HS256"],
        audience="company-internal",
        issuer="apps-cosa",
    )
    assert payload["iss"] == "apps-cosa"
    assert payload["aud"] == "company-internal"
    assert payload["sub"] == "test-worker-123"
    assert payload["role"] == "worker_service"
    assert "jti" in payload
    assert "exp" in payload

def test_worker_jwt_fails_closed_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("WORKER_SERVICE_JWT_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        mint_worker_service_jwt()

    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        ExecutiveBoardClient()

    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        ProjectTeamClient()
