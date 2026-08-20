from sqlalchemy.orm import Session
from app.db.models import Workspace
from core.organization.models import OperatingUnit, Offering
from core.strategy.initiative import Initiative
from app.platform.organization.portfolio_schemas import OperatingUnitCreate, OfferingCreate

def create_operating_unit(db: Session, workspace_id: int, data: OperatingUnitCreate) -> OperatingUnit:
    unit = OperatingUnit(
        workspace_id=workspace_id,
        slug=data.slug,
        name=data.name,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit

def create_offering(db: Session, workspace_id: int, data: OfferingCreate) -> Offering:
    unit = db.query(OperatingUnit).filter_by(id=data.operating_unit_id, workspace_id=workspace_id).first()
    if not unit:
        raise ValueError("Operating unit not found")
    offering = Offering(
        workspace_id=workspace_id,
        operating_unit_id=data.operating_unit_id,
        slug=data.slug,
        name=data.name,
        kind=data.kind,
    )
    db.add(offering)
    db.commit()
    db.refresh(offering)
    return offering

def get_scope_options(db: Session, workspace_id: int) -> dict:
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise ValueError("Workspace not found")
        
    units = db.query(OperatingUnit).filter_by(workspace_id=workspace_id).all()
    offerings = db.query(Offering).filter_by(workspace_id=workspace_id).all()
    initiatives = db.query(Initiative).filter_by(workspace_id=workspace_id).all()
    
    out_units = []
    for u in units:
        u_offerings = []
        for o in offerings:
            if o.operating_unit_id == u.id:
                o_initiatives = [{"id": str(i.id), "title": i.title} for i in initiatives if i.offering_id == o.id]
                u_offerings.append({"id": str(o.id), "name": o.name, "kind": o.kind, "initiatives": o_initiatives})
        out_units.append({"id": str(u.id), "name": u.name, "offerings": u_offerings})
        
    return {
        "company": {"id": str(workspace.id), "name": workspace.name},
        "operating_units": out_units,
    }
