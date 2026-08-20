# LegalChecklistItem/LegalObligation moved to core/legal/models.py (COSA Structure.md
# §49 Business Core migration). Re-exported here for backward compatibility with
# existing `from app.business.legal.models import ...` call sites.
from core.legal.models import LegalChecklistItem, LegalObligation  # noqa: F401
