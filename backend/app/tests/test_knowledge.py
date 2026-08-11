import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember, Brain
from app.modules.vault.models import KnowledgeObject, KnowledgeRelation
from app.modules.vault.knowledge_router import (
    create_knowledge_item,
    list_knowledge_items,
    get_knowledge_item,
    get_knowledge_backlinks,
    promote_knowledge_item,
    KnowledgeObjectCreate,
    KnowledgePromoteRequest,
)


def test_knowledge_object_creation_and_wikilinks(monkeypatch):
    ws_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    # Mock brain lookup
    mock_brain = MagicMock(spec=Brain)
    mock_brain.id = brain_id
    mock_brain.workspace_id = ws_id
    db.query.return_value.filter.return_value.first.return_value = mock_brain
    
    data = KnowledgeObjectCreate(
        title="Kiến trúc Microservices V10",
        content="Xem thêm chi tiết tại [[Chiến lược AI]] và [[Hệ thống Memory Core]].",
        object_type="architecture",
        status="candidate"
    )
    
    res = create_knowledge_item(
        brain_id=brain_id,
        workspace_id=ws_id,
        data=data,
        member=member,
        db=db,
    )
    
    assert res["title"] == "Kiến trúc Microservices V10"
    assert res["object_type"] == "architecture"
    assert res["status"] == "candidate"
    assert db.add.called
    assert db.commit.called


def test_knowledge_promote_with_audit(monkeypatch):
    ws_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    obj_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    mock_brain = MagicMock(spec=Brain)
    mock_brain.id = brain_id
    mock_brain.workspace_id = ws_id
    
    mock_obj = MagicMock(spec=KnowledgeObject)
    mock_obj.id = obj_id
    mock_obj.brain_id = brain_id
    mock_obj.workspace_id = ws_id
    mock_obj.title = "Quy định Bảo mật Dữ liệu"
    mock_obj.status = "candidate"
    
    db.query.return_value.filter.return_value.first.side_effect = [
        mock_brain,  # brain lookup
        mock_obj,    # object lookup
    ]
    
    data = KnowledgePromoteRequest(target_status="approved")
    res = promote_knowledge_item(
        brain_id=brain_id,
        object_id=obj_id,
        workspace_id=ws_id,
        data=data,
        member=member,
        db=db,
    )
    
    assert res["status"] == "promoted"
    assert mock_obj.status == "approved"
    assert db.commit.called


def test_knowledge_cross_tenant_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    brain_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a
    
    db = MagicMock()
    
    data = KnowledgeObjectCreate(
        title="Tài liệu bí mật",
        object_type="decision"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        create_knowledge_item(
            brain_id=brain_id,
            workspace_id=ws_id_b,
            data=data,
            member=member,
            db=db,
        )
        
    assert exc_info.value.status_code == 403
