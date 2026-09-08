from __future__ import annotations

import pytest


_TEST_PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


@pytest.fixture(autouse=True)
def _use_test_platform_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep auth unit tests independent from a developer's loaded .env file."""

    monkeypatch.setenv("PLATFORM_JWT_SECRET", _TEST_PLATFORM_JWT_SECRET)
