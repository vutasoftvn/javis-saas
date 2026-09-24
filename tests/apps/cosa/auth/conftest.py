from __future__ import annotations

import pytest

_TEST_JWT_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod"


@pytest.fixture(autouse=True)
def _use_test_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep auth unit tests independent from a developer's loaded .env file (local session JWT_SECRET)."""

    monkeypatch.setenv("JWT_SECRET", _TEST_JWT_SECRET)
