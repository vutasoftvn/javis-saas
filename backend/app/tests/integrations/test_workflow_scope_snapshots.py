import pytest
from app.platform.auth.models import WorkspaceMember

@pytest.fixture
def owner_auth(app):
    from app.core.auth import get_current_workspace_member
    
    def override_get_current_workspace_member():
        return WorkspaceMember(id=2, workspace_id=101, user_id=2, role="owner")
        
    app.dependency_overrides[get_current_workspace_member] = override_get_current_workspace_member
    return {"Authorization": "Bearer fake-token"}

@pytest.fixture(autouse=True)
def setup_workspace_and_offering(app):
    from app.db.session import SessionLocal
    from app.platform.auth.models import Workspace
    from core.organization.models import OperatingUnit, Offering
    
    db = SessionLocal()
    workspace = db.query(Workspace).filter_by(id=101).first()
    if not workspace:
        db.add(Workspace(id=101, name="Test Workspace"))
        db.commit()
    
    unit = db.query(OperatingUnit).filter_by(id=201).first()
    if not unit:
        unit = OperatingUnit(id=201, workspace_id=101, slug="saas", name="SaaS")
        db.add(unit)
        db.commit()
        
    offering = db.query(Offering).filter_by(id=301).first()
    if not offering:
        offering = Offering(id=301, workspace_id=101, operating_unit_id=201, slug="cosa", name="COSA", kind="product")
        db.add(offering)
        db.commit()
    from app.db.models import Brain
    brain = db.query(Brain).filter_by(id=1).first()
    if not brain:
        brain = Brain(id=1, workspace_id=101, name="Test Brain")
        db.add(brain)
        db.commit()
    db.close()

@pytest.fixture
def definition(client, owner_auth):
    response = client.post(
        "/api/v1/workflows/definitions?workspace_id=101",
        json={"brain_id": 1, "slug": "test-workflow"},
        headers=owner_auth,
    )
    def_id = response.json()["id"]
    client.post(
        f"/api/v1/workflows/definitions/{def_id}/versions?workspace_id=101",
        json={"graph_jsonb": {}},
        headers=owner_auth,
    )
    class DefMock:
        id = def_id
    return DefMock()

@pytest.fixture
def app():
    from app.main import app as main_app
    yield main_app
    main_app.dependency_overrides.clear()

def test_workflow_run_persists_server_resolved_scope_not_client_snapshot(client, owner_auth, definition):
    response = client.post(
        f"/api/v1/workflows/definitions/{definition.id}/run?workspace_id=101",
        json={"offering_id": 301, "scope_snapshot": {"workspace_id": 999, "grants": ["admin"]}},
        headers=owner_auth,
    )
    assert response.status_code == 201
    assert response.json()["scope_snapshot"]["workspace_id"] == 101
    assert "admin" not in response.json()["scope_snapshot"]["grants"]

def test_workflow_run_cannot_start_in_foreign_offering(client, owner_auth, definition):
    response = client.post(f"/api/v1/workflows/definitions/{definition.id}/run?workspace_id=101", json={"offering_id": 9999}, headers=owner_auth)
    assert response.status_code == 403
