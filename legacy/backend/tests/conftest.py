import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    """An override left by one test file (app.dependency_overrides[...] = ...)
    otherwise leaks into every test that runs afterward in the same session,
    since FastAPI stores it on the shared `app` instance."""
    yield
    app.dependency_overrides.clear()
