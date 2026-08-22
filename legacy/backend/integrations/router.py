"""Integrations Domain Master Router"""
from fastapi import APIRouter

from integrations.channels.router import router as channels
from integrations.channels.plugins import plugins_router as plugins
from integrations.channels.outbox import outbox_router
from integrations.channels.zalo import connectors_zalo_router as connectors_zalo
from integrations.channels.google import google_router as connectors_google
from integrations.channels.email import email_approval_router as email_approvals
from integrations.channels.email.email_webhook_router import router as email_webhooks
from integrations.devices.router import router as devices_router
from integrations.realtime import router as realtime
from integrations.workflows import router as workflows

router = APIRouter()

router.include_router(channels, prefix="/api/v1/channels", tags=["channels"])
router.include_router(channels, prefix="/api/v1/connectors", tags=["connectors"])
router.include_router(connectors_zalo.router, prefix="/api/v1/connectors", tags=["connectors-zalo"])
router.include_router(connectors_google.router, prefix="/api/v1/connectors", tags=["connectors-google"])
router.include_router(email_approvals.router, prefix="/api/v1/connectors", tags=["email-approvals"])
# The Resend sender uses this public webhook URL; preserve it during the
# domain-router migration.
router.include_router(email_webhooks, prefix="/api/v1", tags=["email-webhooks"])
router.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
router.include_router(outbox_router.router, prefix="/api/v1/outbox", tags=["outbox-gateway"])
router.include_router(outbox_router.router, prefix="/api/v1", tags=["outbox-gateway-direct"])
router.include_router(realtime.router, prefix="/api/v1/realtime", tags=["realtime"])
router.include_router(devices_router, prefix="/api/v1/devices", tags=["devices"])
router.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
