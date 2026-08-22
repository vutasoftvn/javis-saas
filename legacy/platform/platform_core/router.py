"""Platform Domain Master Router"""
from fastapi import APIRouter

from platform_core.auth import router as auth
from platform_core.vault import router as vault
from platform_core.vault import sync_router as sync
from platform_core.vault import brains_router as brains
from platform_core.license import router as company_runtime
from platform_core.core import router as admin
from platform_core.core import feature_flags_router
from platform_core.core import prompts_router
from platform_core.core import domain_router as domain
from platform_core.core import events_router
from platform_core.core import founder_hub_router
from platform_core.core import missions_router
from platform_core.organization import router as organization_router

from platform_core.tech_radar import router as tech_radar_router
from platform_core.policy_funding.routers import project_funding_router
from platform_core.policy_funding.routers import policy_catalog_router
from platform_core.policy_funding.routers import admin_policy_router
from platform_core.policy_funding.routers import application_router
from platform_core.sync import router as platform_sync_router
from platform_core.control_plane import router_auth as platform_auth_router

router = APIRouter()

router.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
router.include_router(vault.router, prefix="/api/v1/vault", tags=["vault"])
router.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
router.include_router(brains.router, prefix="/api/v1/brains", tags=["brains"])
router.include_router(company_runtime.router, prefix="/api/v1/company-runtime", tags=["company-runtime"])
router.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
router.include_router(feature_flags_router.router, prefix="/api/v1/platform/feature-flags", tags=["platform"])
router.include_router(prompts_router.router, prefix="/api/v1/platform/prompts", tags=["platform-prompts"])
router.include_router(domain.router, prefix="/api/v1/domain", tags=["domain"])
router.include_router(events_router.router, prefix="/api/v1/events", tags=["events"])
router.include_router(founder_hub_router.router, prefix="/api/v1", tags=["founder-hub"])
router.include_router(missions_router.router, prefix="/api/v1/missions", tags=["missions"])
router.include_router(missions_router.router, prefix="/api/v1", tags=["missions-direct"])
router.include_router(organization_router.router, prefix="/api/v1/organization", tags=["organization"])
router.include_router(organization_router.router, prefix="/api/v1", tags=["organization-direct"])
router.include_router(tech_radar_router.router, prefix="/api/v1/tech-radar", tags=["tech-radar"])

router.include_router(project_funding_router.router, prefix="/api/v1/policy-funding", tags=["policy-funding-projects"])
router.include_router(project_funding_router.router, prefix="/api/v1", tags=["policy-funding-projects-direct"])
router.include_router(policy_catalog_router.router, prefix="/api/v1/policy-funding", tags=["policy-programs"])
router.include_router(policy_catalog_router.router, prefix="/api/v1", tags=["policy-programs-direct"])
router.include_router(admin_policy_router.router, prefix="/api/v1/policy-funding", tags=["admin-policy"])
router.include_router(application_router.router, prefix="/api/v1/policy-funding", tags=["policy-applications"])
router.include_router(platform_sync_router.router, prefix="/api/v1/platform", tags=["platform-sync"])
router.include_router(platform_auth_router.router, prefix="/api/v1/platform", tags=["platform-auth"])
