from fastapi import APIRouter

from platform_core.license.routers.contracts_router import router as contracts_router
from platform_core.license.routers.reviews_router import router as reviews_router
from platform_core.license.routers.blockers_router import router as blockers_router
from platform_core.license.routers.needs_you_router import router as needs_you_router
from platform_core.license.routers.handoffs_router import router as handoffs_router
from platform_core.license.routers.runtime_router import router as runtime_router

router = APIRouter()

router.include_router(contracts_router, tags=["company-runtime-contracts"])
router.include_router(reviews_router, tags=["company-runtime-reviews"])
router.include_router(blockers_router, tags=["company-runtime-blockers"])
router.include_router(needs_you_router, tags=["company-runtime-needs-you"])
router.include_router(handoffs_router, tags=["company-runtime-handoffs"])
router.include_router(runtime_router, tags=["company-runtime-core"])
