"""Entrypoint role "full" - đủ 5 domain (founder_os/business/workforce/
integrations/platform). Dùng cho local dev, backend desktop, self-host VPS.

    uvicorn app.full_main:app --host 0.0.0.0 --port 8000
"""
import os

import uvicorn

from app.bootstrap.create_app import FULL_ROLE, create_app

app = create_app(FULL_ROLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.full_main:app", host="0.0.0.0", port=port, reload=True)
