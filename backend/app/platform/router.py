"""Platform Domain Master Router"""
from fastapi import APIRouter

from app.platform.auth import router as auth
from app.platform.vault import router as vault
from app.platform.vault import sync_router as sync
from app.platform.vault import brains_router as brains
from app.platform.license import router as company_runtime
from app.platform.core import router as admin
from app.platform.core import feature_flags_router
from app.platform.core import prompts_router
from app.platform.core import domain_router as domain
from app.platform.core import events_router
from app.platform.core import founder_hub_router
from app.platform.core import missions_router
from app.platform.organization import router as organization_router

from app.platform.tech_radar import router as tech_radar_router
from app.platform.policy_funding.routers import project_funding_router
from app.platform.policy_funding.routers import policy_catalog_router
from app.platform.policy_funding.routers import admin_policy_router
from app.platform.policy_funding.routers import application_router

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
router.include_router(founder_hub_router.router, prefix="/api/v1/founder-hub", tags=["founder-hub"])
router.include_router(missions_router.router, prefix="/api/v1/missions", tags=["missions"])
router.include_router(organization_router.router, prefix="/api/v1/organization", tags=["organization"])
router.include_router(tech_radar_router.router, prefix="/api/v1/tech-radar", tags=["tech-radar"])

router.include_router(project_funding_router.router, prefix="/api/v1/policy-funding/projects", tags=["policy-funding-projects"])
router.include_router(policy_catalog_router.router, prefix="/api/v1/policy-funding/programs", tags=["policy-programs"])
router.include_router(admin_policy_router.router, prefix="/api/v1/policy-funding/admin", tags=["admin-policy"])
router.include_router(application_router.router, prefix="/api/v1/policy-funding/applications", tags=["policy-applications"])
