"""Entrypoint role "central_control_plane" (Quyết định 3) - chỉ bề mặt
platform sync/entitlement (`app.platform.sync.router`). Không bao giờ import
founder_os/business/workforce/integrations, hay `app.platform.router`
aggregator.

    uvicorn app.central_main:app --host 0.0.0.0 --port 8000
"""
import os

import uvicorn

from bootstrap.create_app import CENTRAL_CONTROL_PLANE_ROLE, create_app

app = create_app(CENTRAL_CONTROL_PLANE_ROLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("central_main:app", host="0.0.0.0", port=port)
