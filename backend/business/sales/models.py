# All Sales models moved to core/sales/models.py (COSA Structure.md §49 Business
# Core migration). Re-exported here for backward compatibility with existing
# `from business.sales.models import ...` call sites.
from business_core.sales.models import (  # noqa: F401
    Account,
    Contact,
    SalesLead,
    SalesOpportunity,
    SalesActivity,
    Customer,
)
