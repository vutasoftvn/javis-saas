import pytest
from platform_core.auth.models import WorkspaceMember

@pytest.fixture
def member_auth(app):
    from core.auth import get_current_workspace_member
    
    def override_get_current_workspace_member():
        return WorkspaceMember(id=1, workspace_id=101, user_id=1, role="member")
        
    app.dependency_overrides[get_current_workspace_member] = override_get_current_workspace_member
    return {"Authorization": "Bearer fake-token"}

@pytest.fixture
def owner_auth(app):
    from core.auth import get_current_workspace_member
    
    def override_get_current_workspace_member():
        return WorkspaceMember(id=2, workspace_id=101, user_id=2, role="owner")
        
    app.dependency_overrides[get_current_workspace_member] = override_get_current_workspace_member
    return {"Authorization": "Bearer fake-token"}

@pytest.fixture
def app():
    from main import app as main_app
    yield main_app
    main_app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def setup_workspace(app):
    from db.session import SessionLocal
    from platform_core.auth.models import Workspace
    
    db = SessionLocal()
    workspace = db.query(Workspace).filter_by(id=101).first()
    if not workspace:
        db.add(Workspace(id=101, name="Test Workspace"))
        db.commit()
    db.close()

def test_member_cannot_create_operating_unit(client, member_auth):
    response = client.post("/api/v1/organization/operating-units?workspace_id=101", json={"slug": "services", "name": "Services"}, headers=member_auth)
    assert response.status_code == 403

import uuid

def test_owner_can_create_hierarchy_and_read_scope_options(client, owner_auth, monkeypatch):
    monkeypatch.setattr("founder_os.strategy.portfolio_router.require_flag", lambda *args, **kwargs: True)

    uniq = str(uuid.uuid4())[:8]

    # 1. Create Operating Unit
    unit = client.post("/api/v1/organization/operating-units?workspace_id=101", json={
        "slug": f"services-{uniq}",
        "name": "Services",
    }, headers=owner_auth)
    assert unit.status_code == 201, unit.json()
    
    ou_id = unit.json()["id"]
    
    offering = client.post("/api/v1/organization/offerings?workspace_id=101", json={
        "operating_unit_id": ou_id,
        "slug": f"ai-agents-{uniq}",
        "name": "AI Agents",
        "kind": "service"
    }, headers=owner_auth)
    
    options = client.get("/api/v1/organization/scope-options?workspace_id=101", headers=owner_auth)
    assert options.status_code == 200
    
    ou_list = options.json()["operating_units"]
    ou = next((o for o in ou_list if o["id"] == ou_id), None)
    assert ou is not None
    assert any(off["id"] == offering.json()["id"] for off in ou["offerings"])

def test_workspace_parameter_tampering_is_forbidden(client, owner_auth):
    assert client.get("/api/v1/organization/scope-options?workspace_id=999", headers=owner_auth).status_code == 403
