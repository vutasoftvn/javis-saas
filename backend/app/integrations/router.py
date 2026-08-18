"""Integrations Domain Master Router"""
from fastapi import APIRouter

from app.integrations.channels.router import router as channels
from app.integrations.channels.plugins import plugins_router as plugins
from app.integrations.channels.outbox import outbox_router
from app.integrations.channels.zalo import connectors_zalo_router as connectors_zalo
from app.integrations.channels.google import google_router as connectors_google
from app.integrations.channels.email import email_approval_router as email_approvals
from app.integrations.channels.email.email_webhook_router import router as email_webhooks
from app.integrations.devices.router import router as devices_router
from app.integrations.realtime import router as realtime
from app.integrations.workflows import router as workflows

router = APIRouter()

router.include_router(channels, prefix="/api/v1/channels", tags=["channels"])
router.include_router(channels, prefix="/api/v1/connectors", tags=["connectors"])
router.include_router(connectors_zalo.router, prefix="/api/v1/connectors", tags=["connectors-zalo"])
router.include_router(connectors_google.router, prefix="/api/v1/connectors", tags=["connectors-google"])
router.include_router(email_approvals.router, prefix="/api/v1/connectors", tags=["email-approvals"])
router.include_router(email_webhooks, prefix="/api/v1/email-webhooks", tags=["email-webhooks"])
router.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
router.include_router(outbox_router.router, prefix="/api/v1/outbox", tags=["outbox-gateway"])
router.include_router(outbox_router.router, prefix="/api/v1", tags=["outbox-gateway-direct"])
router.include_router(realtime.router, prefix="/api/v1/realtime", tags=["realtime"])
router.include_router(devices_router, prefix="/api/v1/devices", tags=["devices"])
router.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
