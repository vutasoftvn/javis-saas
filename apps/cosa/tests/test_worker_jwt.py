import jwt
import pytest

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

    # Client được tạo được (composition/CLI không cần secret) nhưng request
    # đầu tiên fail-closed khi ký token.
    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        _ = ExecutiveBoardClient().service_token

    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        _ = ProjectTeamClient().service_token


def test_clients_mint_a_fresh_worker_jwt_per_request(monkeypatch):
    # Token chỉ sống 5 phút: client sống lâu phải ký lại mỗi request thay vì
    # giữ token ký lúc khởi động.
    secret = "y" * 40
    monkeypatch.setenv("WORKER_SERVICE_JWT_SECRET", secret)
    client = ProjectTeamClient()

    def jti(token: str) -> str:
        return jwt.decode(
            token, secret, algorithms=["HS256"], audience="company-internal", issuer="apps-cosa"
        )["jti"]

    assert jti(client.service_token) != jti(client.service_token)
    assert ProjectTeamClient(service_token="static").service_token == "static"


def test_worker_jwt_has_no_default_secret_outside_tests(monkeypatch):
    # development không còn secret mặc định (spec 2026-09-25 §5).
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("WORKER_SERVICE_JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="WORKER_SERVICE_JWT_SECRET"):
        mint_worker_service_jwt()


def test_worker_jwt_uses_configured_secret(monkeypatch):
    secret = "x" * 40
    monkeypatch.setenv("WORKER_SERVICE_JWT_SECRET", secret)
    token = mint_worker_service_jwt(worker_id="w-1")
    payload = jwt.decode(
        token, secret, algorithms=["HS256"], audience="company-internal", issuer="apps-cosa"
    )
    assert payload["sub"] == "w-1"
