# All models moved to core/marketing/form_models.py (COSA Structure.md §49
# Business Core migration). Re-exported here for backward compatibility with
# existing `from app.business.marketing.form_models import ...` call sites.
from core.marketing.form_models import FormDefinition, FormSubmission, WebEvent  # noqa: F401
