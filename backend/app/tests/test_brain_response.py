from app.core.snowflake import generate_snowflake_id
from app.modules.vault.brains_router import BrainResponse


def test_brain_response_serializes_snowflake_ids_as_strings():
    brain_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    response = BrainResponse.model_validate(
        {
            "id": brain_id,
            "workspace_id": workspace_id,
            "name": "Main",
            "created_at": "2026-08-13T00:00:00",
        }
    )

    assert response.model_dump(mode="json")["id"] == str(brain_id)
    assert response.model_dump(mode="json")["workspace_id"] == str(workspace_id)
