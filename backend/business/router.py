"""Business Domain Master Router"""
from fastapi import APIRouter

from business.marketing import router as marketing
from business.marketing.public_router import router as public_marketing
from business.sales import router as sales
from business.sales import revenue_router
from business.sales import public_lead_router
from business.finance import router as finance
from business.finance import tt58_router
from business.legal import router as legal
from business.learning import router as learning
from business.packs import router as packs

router = APIRouter()

router.include_router(packs.router, prefix="/api/v1/business/packs", tags=["business-packs"])
router.include_router(marketing.router, prefix="/api/v1/marketing", tags=["marketing"])
# Public landing integrations retain their stable `/api/v1/public/*` contract.
# The router itself owns the `/public` prefix, so mounting it below marketing
# would otherwise create the unintended `/marketing/public/public/*` path.
router.include_router(public_marketing, prefix="/api/v1", tags=["public-marketing"])
router.include_router(sales.router, prefix="/api/v1/sales", tags=["sales"])
router.include_router(revenue_router.router, prefix="/api/v1/revenue", tags=["revenue-engine"])
router.include_router(revenue_router.router, prefix="/api/v1", tags=["revenue-engine-direct"])
router.include_router(public_lead_router.router, prefix="/api/v1/public-leads", tags=["public-leads"])
router.include_router(finance.router, prefix="/api/v1/finance", tags=["finance"])
router.include_router(tt58_router.router, prefix="/api/v1/finance/tt58", tags=["finance-tt58"])
router.include_router(tt58_router.router, prefix="/api/v1", tags=["finance-tt58-direct"])
router.include_router(legal.router, prefix="/api/v1/legal", tags=["legal"])
router.include_router(learning.router, prefix="/api/v1/learning", tags=["learning"])
