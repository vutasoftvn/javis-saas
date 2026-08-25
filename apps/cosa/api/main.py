from __future__ import annotations

from apps.cosa.api.app import create_cosa_app

__all__ = ["app"]

# FastAPI app instance for uvicorn to import directly
app = create_cosa_app()
