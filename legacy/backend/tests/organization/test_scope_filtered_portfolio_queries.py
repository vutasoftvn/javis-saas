import pytest
from platform_core.auth.models import WorkspaceMember

@pytest.fixture
def owner_auth(app):
    from core.auth import get_current_workspace_member
    
    def override_get_current_workspace_member():
        return WorkspaceMember(id=2, workspace_id=101, user_id=2, role="owner")
        
    app.dependency_overrides[get_current_workspace_member] = override_get_current_workspace_member
    return {"Authorization": "Bearer fake-token"}

@pytest.fixture(autouse=True)
def setup_portfolio_projects(app):
    from db.session import SessionLocal
    from platform_core.auth.models import Workspace
    from business_core.organization.models import OperatingUnit, Offering
    from business_core.strategy.initiative import Initiative
    from business_core.strategy.project import Project
    
    db = SessionLocal()
    if not db.query(Workspace).filter_by(id=101).first():
        db.add(Workspace(id=101, name="Test Workspace"))
        db.commit()
    
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

    proj1 = db.query(Project).filter_by(id=501).first()
    if not proj1:
        proj1 = Project(id=501, workspace_id=101, brain_id=1, title="Proj 1", status="planning")
        db.add(proj1)
        
    proj2 = db.query(Project).filter_by(id=502).first()
    if not proj2:
        proj2 = Project(id=502, workspace_id=101, brain_id=1, title="Proj 2", status="planning")
        db.add(proj2)
    db.commit()

    init1 = db.query(Initiative).filter_by(id=401).first()
    if not init1:
        init1 = Initiative(id=401, workspace_id=101, brain_id=1, title="Init 1", offering_id=301, project_id=501)
        db.add(init1)
    else:
        init1.project_id = 501
    
    init2 = db.query(Initiative).filter_by(id=402).first()
    if not init2:
        init2 = Initiative(id=402, workspace_id=101, brain_id=1, title="Init 2", offering_id=302, project_id=502)
        db.add(init2)
    else:
        init2.project_id = 502
    db.commit()

    from business_core.organization.models import OperatingUnit, Offering
    from db.models import Brain
    from founder_os.strategy.models import Portfolio, PortfolioProject
    
    port1 = db.query(Portfolio).filter_by(id=901).first()
    if not port1:
        port1 = Portfolio(id=901, workspace_id=101, brain_id=1, name="Test Portfolio")
        db.add(port1)
        db.commit()
        
    pp1 = db.query(PortfolioProject).filter_by(id=1001).first()
    if not pp1:
        db.add(PortfolioProject(id=1001, portfolio_id=901, project_id=501, workspace_id=101))
        db.add(PortfolioProject(id=1002, portfolio_id=901, project_id=502, workspace_id=101))
        db.commit()

    db.close()

@pytest.fixture
def app():
    from main import app as main_app
    yield main_app
    main_app.dependency_overrides.clear()

def test_portfolio_projects_list_filters_by_offering(client, app, owner_auth, monkeypatch):
    monkeypatch.setattr("founder_os.strategy.portfolio_router.require_flag", lambda *args, **kwargs: True)
    url = app.url_path_for("list_portfolio_projects", portfolio_id=901)
    response = client.get(f"{url}?workspace_id=101&offering_id=301", headers=owner_auth)
    assert response.status_code == 200
    ids = [item["project_id"] for item in response.json()["projects"]]
    assert "501" in ids
    assert "502" not in ids
