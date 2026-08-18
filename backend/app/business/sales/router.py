from fastapi import APIRouter

from app.business.sales.routers.accounts_router import router as accounts_router
from app.business.sales.routers.contacts_router import router as contacts_router
from app.business.sales.routers.leads_router import router as leads_router
from app.business.sales.routers.opportunities_router import router as opportunities_router
from app.business.sales.routers.customers_router import router as customers_router
from app.business.sales.routers.activities_router import router as activities_router
from app.business.sales.routers.funnel_router import router as funnel_router

router = APIRouter()

router.include_router(accounts_router)
router.include_router(contacts_router)
router.include_router(leads_router)
router.include_router(opportunities_router)
router.include_router(customers_router)
router.include_router(activities_router)
router.include_router(funnel_router)
