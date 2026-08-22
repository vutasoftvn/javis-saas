# LegalChecklistItem/LegalObligation moved to core/legal/models.py (COSA Structure.md
# §49 Business Core migration). Re-exported here for backward compatibility with
# existing `from business.legal.models import ...` call sites.
from business_core.legal.models import LegalChecklistItem, LegalObligation  # noqa: F401
