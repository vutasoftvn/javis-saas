from __future__ import annotations

from apps.cosa.api.app import create_cosa_app
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

__all__ = ["app"]

# Test FastAPI app instance with authentication already overridden
# This is used by E2E tests that start uvicorn as a subprocess
app = create_cosa_app()
override_authenticated_identity(app)
