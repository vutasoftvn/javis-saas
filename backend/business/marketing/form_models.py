# All models moved to core/marketing/form_models.py (COSA Structure.md §49
# Business Core migration). Re-exported here for backward compatibility with
# existing `from business.marketing.form_models import ...` call sites.
from business_core.marketing.form_models import FormDefinition, FormSubmission, WebEvent  # noqa: F401
