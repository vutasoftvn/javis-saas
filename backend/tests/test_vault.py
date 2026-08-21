import pytest
from db.repositories.vault_repo import VaultRepository
from db.models import VaultDocument, VaultRevision
from fastapi import HTTPException
from core.snowflake import generate_snowflake_id

def test_vault_repo_permission():
    from unittest.mock import MagicMock
    db_mock = MagicMock()
    user_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    
    # Viewer can read
    repo_viewer = VaultRepository(db_mock, user_id, brain_id, "viewer")
    
    # Mock get_document to return None
    db_mock.query().filter().first.return_value = None
    assert repo_viewer.get_document("test.md") is None
    
    # Viewer cannot update
    with pytest.raises(HTTPException) as exc:
        repo_viewer.update_document("test.md", "wiki", b"content")
    assert exc.value.status_code == 403
    
    # Editor can update
    repo_editor = VaultRepository(db_mock, user_id, brain_id, "editor")
    # We won't test full update flow here as it requires DB, just checking it doesn't raise 403
    # Wait, it will raise because it tries to use the db mock
    try:
        repo_editor.update_document("test.md", "wiki", b"content")
    except HTTPException as e:
        assert e.status_code != 403 # Should pass permission check
    except Exception:
        pass

def test_vault_revision_conflict():
    from unittest.mock import MagicMock
    db_mock = MagicMock()
    user_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    
    repo_editor = VaultRepository(db_mock, user_id, brain_id, "editor")
    
    # Mock document exists with current_revision_id X
    doc_mock = MagicMock()
    current_rev_id = generate_snowflake_id()
    doc_mock.current_revision_id = current_rev_id
    
    db_mock.query().filter().first.return_value = doc_mock
    
    # If base_revision_id doesn't match current, raise 409
    wrong_rev_id = generate_snowflake_id()
    with pytest.raises(HTTPException) as exc:
        repo_editor.update_document("test.md", "wiki", b"content", base_revision_id=wrong_rev_id)
    assert exc.value.status_code == 409
    assert exc.value.detail == "VAULT_REVISION_CONFLICT"
    
    # If base_revision_id matches, it proceeds
    try:
        repo_editor.update_document("test.md", "wiki", b"content", base_revision_id=current_rev_id)
    except HTTPException as e:
        assert e.status_code != 409
    except Exception:
        pass


def test_vault_tools_registration():
    from core.tool_registry import get_tool_by_flat_name
    from core.tool_bootstrap import load_all_tools

    load_all_tools()
    save_tool = get_tool_by_flat_name("vault_save_document")
    list_tool = get_tool_by_flat_name("vault_list_documents")
    assert save_tool is not None
    assert list_tool is not None
    assert save_tool.namespace == "vault"
    assert list_tool.namespace == "vault"

