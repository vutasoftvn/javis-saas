from fastapi import APIRouter

from business.finance.routers import (
    books_router, documents_router, exceptions_router, overview_router,
    periods_router, profile_router, reports_router, transactions_router,
    regimes_router,
)

router = APIRouter()
router.include_router(profile_router.router, prefix="/profile", tags=["finance-profile"])
router.include_router(overview_router.router, prefix="/overview", tags=["finance-overview"])
router.include_router(transactions_router.router, prefix="/transactions", tags=["finance-transactions"])
router.include_router(documents_router.router, prefix="/documents", tags=["finance-documents"])
router.include_router(books_router.router, prefix="/books", tags=["finance-books"])
router.include_router(reports_router.router, prefix="/reports", tags=["finance-reports"])
router.include_router(periods_router.router, prefix="/periods", tags=["finance-periods"])
router.include_router(exceptions_router.router, prefix="/exceptions", tags=["finance-exceptions"])
router.include_router(regimes_router.router, prefix="/regimes", tags=["finance-regimes"])

