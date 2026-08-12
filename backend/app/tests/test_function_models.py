from app.core.snowflake import generate_snowflake_id
from app.modules.legal.models import LegalChecklistItem, LegalObligation
from app.modules.sales.models import SalesLead


def test_function_models_use_snowflake_ids_and_workspace_scope():
    workspace_id = generate_snowflake_id()
    checklist = LegalChecklistItem(workspace_id=workspace_id, title="Privacy notice")
    obligation = LegalObligation(workspace_id=workspace_id, title="Annual filing")
    lead = SalesLead(workspace_id=workspace_id, name="Acme")

    assert checklist.workspace_id == obligation.workspace_id == lead.workspace_id == workspace_id
