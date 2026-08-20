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
def setup_workflow_runs(app):
    from app.db.session import SessionLocal
    from app.platform.auth.models import Workspace
    from core.organization.models import OperatingUnit, Offering
    from app.db.models import Brain
    from app.integrations.workflows.models import WorkflowDefinition, WorkflowVersion, WorkflowRun
    
    db = SessionLocal()
    if not db.query(Workspace).filter_by(id=101).first():
        db.add(Workspace(id=101, name="Test Workspace"))
    if not db.query(Brain).filter_by(id=1).first():
        db.add(Brain(id=1, workspace_id=101, name="Test Brain"))
        
    db.commit()
    
    # Unit and offerings
    unit = db.query(OperatingUnit).filter_by(id=201).first()
    if not unit:
        unit = OperatingUnit(id=201, workspace_id=101, slug="saas", name="SaaS")
        db.add(unit)
    
    off1 = db.query(Offering).filter_by(id=301).first()
    if not off1:
        off1 = Offering(id=301, workspace_id=101, operating_unit_id=201, slug="off1", name="Off 1", kind="product")
        db.add(off1)
        
    off2 = db.query(Offering).filter_by(id=302).first()
    if not off2:
        off2 = Offering(id=302, workspace_id=101, operating_unit_id=201, slug="off2", name="Off 2", kind="product")
        db.add(off2)
    db.commit()

    # Definitions and Runs
    def1 = db.query(WorkflowDefinition).filter_by(id=401).first()
    if not def1:
        def1 = WorkflowDefinition(id=401, brain_id=1, slug="def1")
        db.add(def1)
        db.commit()
        ver1 = WorkflowVersion(id=501, definition_id=401)
        db.add(ver1)
        db.commit()
        
        run1 = WorkflowRun(id=601, version_id=501, trigger="manual", scope_snapshot_jsonb={"workspace_id": 101, "offering_id": 301})
        db.add(run1)
        run2 = WorkflowRun(id=602, version_id=501, trigger="manual", scope_snapshot_jsonb={"workspace_id": 101, "offering_id": 302})
        db.add(run2)
        db.commit()

    db.close()

@pytest.fixture
def app():
    from app.main import app as main_app
    yield main_app
    main_app.dependency_overrides.clear()

def test_workflow_run_list_filters_to_selected_offering_without_leaking_other_offering(client, owner_auth):
    response = client.get("/api/v1/workflows/runs?workspace_id=101&offering_id=301", headers=owner_auth)
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["runs"]]
    assert "601" in ids
    assert "602" not in ids

def test_run_detail_returns_404_when_scope_filter_does_not_match_its_snapshot(client, owner_auth):
    response = client.get("/api/v1/workflows/runs/602?workspace_id=101&offering_id=301", headers=owner_auth)
    assert response.status_code == 404
