from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.snowflake import generate_snowflake_id

from pydantic import BaseModel, Field
from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember, OkrCycle, OkrObjective, KeyResult, Brain, TowsOption

router = APIRouter()


def _serialize_cycle(c: OkrCycle) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "start_date": c.start_date.isoformat() if c.start_date else None,
        "end_date": c.end_date.isoformat() if c.end_date else None,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_objective(o: OkrObjective) -> dict:
    return {
        "id": str(o.id),
        "cycle_id": str(o.cycle_id) if o.cycle_id else None,
        "strategic_objective_id": str(o.strategic_objective_id) if o.strategic_objective_id else None,
        "title": o.title,
        "owner_id": str(o.owner_id) if o.owner_id else None,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


def _serialize_key_result(k: KeyResult) -> dict:
    title = getattr(k, "title", None)
    if not title:
        title = f"Đạt {k.target_value or ''} {k.unit or ''}".strip()
    return {
        "id": str(k.id),
        "objective_id": str(k.objective_id),
        "title": title,
        "metric_id": str(k.metric_id) if k.metric_id else None,
        "baseline_value": k.baseline_value,
        "current_value": k.current_value,
        "target_value": k.target_value,
        "unit": k.unit,
        "cadence": k.cadence,
        "status": k.status,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


# ==========================================
# OKR Cycles
# ==========================================

class OkrCycleCreate(BaseModel):
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = "active"


class OkrCycleUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None


@router.get("/cycles")
def list_okr_cycles(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    cycles = db.query(OkrCycle).filter(OkrCycle.workspace_id == workspace_id).order_by(OkrCycle.created_at.desc()).all()
    return {"cycles": [_serialize_cycle(c) for c in cycles]}


@router.post("/cycles")
def create_okr_cycle(
    workspace_id: int,
    data: OkrCycleCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    brain_id = brain.id if brain else generate_snowflake_id()

    cycle = OkrCycle(
        workspace_id=workspace_id,
        brain_id=brain_id,
        name=data.name,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status or "active",
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return _serialize_cycle(cycle)


@router.put("/cycles/{cycle_id}")
def update_okr_cycle(
    cycle_id: int,
    workspace_id: int,
    data: OkrCycleUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    cycle = db.query(OkrCycle).filter(OkrCycle.id == cycle_id, OkrCycle.workspace_id == workspace_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="OKR cycle not found")
    
    if data.name is not None:
        cycle.name = data.name
    if data.start_date is not None:
        cycle.start_date = data.start_date
    if data.end_date is not None:
        cycle.end_date = data.end_date
    if data.status is not None:
        cycle.status = data.status

    db.commit()
    db.refresh(cycle)
    return _serialize_cycle(cycle)


@router.delete("/cycles/{cycle_id}")
def delete_okr_cycle(
    cycle_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    cycle = db.query(OkrCycle).filter(OkrCycle.id == cycle_id, OkrCycle.workspace_id == workspace_id).first()
    if not cycle:
        raise HTTPException(status_code=404, detail="OKR cycle not found")
    
    db.delete(cycle)
    db.commit()
    return {"status": "deleted", "id": str(cycle_id)}


# ==========================================
# OKR Objectives
# ==========================================

class OkrObjectiveCreate(BaseModel):
    title: str
    cycle_id: Optional[int] = None
    strategic_objective_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: Optional[str] = "active"


class OkrObjectiveUpdate(BaseModel):
    title: Optional[str] = None
    cycle_id: Optional[int] = None
    strategic_objective_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: Optional[str] = None


@router.get("/objectives")
def list_okr_objectives(
    workspace_id: int,
    cycle_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    query = db.query(OkrObjective).filter(OkrObjective.workspace_id == workspace_id)
    if cycle_id:
        query = query.filter(OkrObjective.cycle_id == cycle_id)
    objectives = query.order_by(OkrObjective.created_at.desc()).all()
    return {"objectives": [_serialize_objective(o) for o in objectives]}


@router.post("/objectives")
def create_okr_objective(
    workspace_id: int,
    data: OkrObjectiveCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    target_cycle_id = data.cycle_id
    if not target_cycle_id:
        active_cycle = db.query(OkrCycle).filter(OkrCycle.workspace_id == workspace_id).order_by(OkrCycle.created_at.desc()).first()
        if active_cycle:
            target_cycle_id = active_cycle.id
        else:
            brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
            new_cycle = OkrCycle(
                workspace_id=workspace_id,
                brain_id=brain.id if brain else generate_snowflake_id(),
                name="Q1 Annual Cycle",
                status="active"
            )
            db.add(new_cycle)
            db.flush()
            target_cycle_id = new_cycle.id

    obj = OkrObjective(
        workspace_id=workspace_id,
        cycle_id=target_cycle_id,
        strategic_objective_id=data.strategic_objective_id,
        title=data.title,
        owner_id=data.owner_id,
        status=data.status or "active",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _serialize_objective(obj)


@router.put("/objectives/{objective_id}")
def update_okr_objective(
    objective_id: int,
    workspace_id: int,
    data: OkrObjectiveUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    obj = db.query(OkrObjective).filter(OkrObjective.id == objective_id, OkrObjective.workspace_id == workspace_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    if data.title is not None:
        obj.title = data.title
    if data.cycle_id is not None:
        obj.cycle_id = data.cycle_id
    if data.strategic_objective_id is not None:
        obj.strategic_objective_id = data.strategic_objective_id
    if data.owner_id is not None:
        obj.owner_id = data.owner_id
    if data.status is not None:
        obj.status = data.status

    db.commit()
    db.refresh(obj)
    return _serialize_objective(obj)


@router.delete("/objectives/{objective_id}")
def delete_okr_objective(
    objective_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    obj = db.query(OkrObjective).filter(OkrObjective.id == objective_id, OkrObjective.workspace_id == workspace_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    # Delete related key results
    db.query(KeyResult).filter(KeyResult.objective_id == objective_id, KeyResult.workspace_id == workspace_id).delete()
    db.delete(obj)
    db.commit()
    return {"status": "deleted", "id": str(objective_id)}


class OkrAiGenerateRequest(BaseModel):
    tows_id: Optional[int] = None
    objectives_count: Optional[int] = Field(2, ge=1, le=3)
    krs_per_objective_count: Optional[int] = Field(3, ge=2, le=5)
    clear_existing: Optional[bool] = True
    cycle_id: Optional[int] = None


@router.post("/generate-ai")
def generate_ai_okrs(
    workspace_id: int,
    data: Optional[OkrAiGenerateRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    try:
        req = data or OkrAiGenerateRequest()

        # 1. Fetch active cycle or default
        cycle = None
        if req.cycle_id:
            cycle = db.query(OkrCycle).filter(OkrCycle.id == req.cycle_id, OkrCycle.workspace_id == workspace_id).first()
        if not cycle:
            cycle = db.query(OkrCycle).filter(OkrCycle.workspace_id == workspace_id).order_by(OkrCycle.created_at.desc()).first()
        if not cycle:
            brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
            cycle = OkrCycle(
                workspace_id=workspace_id,
                brain_id=brain.id if brain else generate_snowflake_id(),
                name="Chu kỳ Thực thi 12 Tuần",
                status="active"
            )
            db.add(cycle)
            db.flush()
        
        cycle_id = cycle.id

        # 2. Clear existing OKRs if requested (Default: True)
        if req.clear_existing is not False:
            old_objs = db.query(OkrObjective).filter(OkrObjective.workspace_id == workspace_id, OkrObjective.cycle_id == cycle_id).all()
            if old_objs:
                old_ids = [o.id for o in old_objs]
                db.query(KeyResult).filter(KeyResult.objective_id.in_(old_ids)).delete(synchronize_session=False)
                db.query(OkrObjective).filter(OkrObjective.id.in_(old_ids)).delete(synchronize_session=False)
                db.flush()

        # 3. Fetch TOWS option context if provided
        tows_opt = None
        if req.tows_id:
            tows_opt = db.query(TowsOption).filter(TowsOption.id == req.tows_id, TowsOption.workspace_id == workspace_id).first()
        
        tows_context = f"Chiến lược TOWS [{tows_opt.quadrant}]: {tows_opt.title}" if tows_opt else "Toàn bộ ma trận chiến lược TOWS và định hướng doanh nghiệp"

        # 4. Count of objectives to generate (1 to 3) & KRs per objective (2 to 5)
        count = req.objectives_count if req.objectives_count in (1, 2, 3) else 2
        kr_count = req.krs_per_objective_count if req.krs_per_objective_count and req.krs_per_objective_count in (2, 3, 4, 5) else 4

        # Dynamic generated OKRs with expanded pool of KRs (up to 5 per template)
        okr_templates = [
            {
                "title": f"Tăng tốc chiếm lĩnh thị trường theo {tows_context}",
                "krs": [
                    {"title": "Mở rộng 50 khách hàng B2B doanh nghiệp mới", "target_value": 50.0, "unit": "khách hàng B2B"},
                    {"title": "Nâng tỷ lệ giữ chân doanh thu NRR lên 90%", "target_value": 90.0, "unit": "% NRR"},
                    {"title": "Rút ngắn quy trình onboarding xuống 5 ngày", "target_value": 5.0, "unit": "ngày"},
                    {"title": "Đạt mức tăng trưởng doanh thu MRR 35%", "target_value": 35.0, "unit": "% MRR"},
                    {"title": "Duy trì chỉ số hài lòng khách hàng NPS ở 85 điểm", "target_value": 85.0, "unit": "điểm NPS"},
                ]
            },
            {
                "title": f"Tự động hóa quy trình vận hành & tối ưu hiệu suất nhờ {tows_context}",
                "krs": [
                    {"title": "Tự động hóa 70% các tác vụ vận hành nghiệp vụ", "target_value": 70.0, "unit": "% tác vụ"},
                    {"title": "Cắt giảm 20% chi phí vận hành doanh nghiệp OPEX", "target_value": 20.0, "unit": "% OPEX"},
                    {"title": "Nâng chỉ số hài lòng nhân sự nội bộ eNPS lên 85 điểm", "target_value": 85.0, "unit": "điểm eNPS"},
                    {"title": "Đạt 99% tỷ lệ tuân thủ cam kết chất lượng dịch vụ SLA", "target_value": 99.0, "unit": "% SLA"},
                    {"title": "Tiết kiệm 15 giờ/tuần xử lý quy trình thủ công", "target_value": 15.0, "unit": "giờ/tuần"},
                ]
            },
            {
                "title": f"Củng cố an toàn hệ thống và đáp ứng tiêu chuẩn tuân thủ bảo mật",
                "krs": [
                    {"title": "Đáp ứng 100% các tiêu chuẩn tuân thủ an toàn dữ liệu PDPD", "target_value": 100.0, "unit": "% PDPD"},
                    {"title": "Duy trì độ sẵn sàng hệ thống Uptime ở mức 99.9%", "target_value": 99.9, "unit": "% Uptime"},
                    {"title": "Kiểm soát 0 sự cố mất an toàn thông tin dữ liệu", "target_value": 0.0, "unit": "sự cố"},
                    {"title": "Rút ngắn thời gian phản ứng sự cố MTTR dưới 24 giờ", "target_value": 24.0, "unit": "giờ MTTR"},
                    {"title": "Mã hóa 100% các dữ liệu nhạy cảm trên toàn hệ thống", "target_value": 100.0, "unit": "% dữ liệu"},
                ]
            }
        ]

        selected_okrs = okr_templates[:count]
        created_objectives = []

        for item in selected_okrs:
            obj = OkrObjective(
                workspace_id=workspace_id,
                cycle_id=cycle_id,
                title=item["title"],
                status="active"
            )
            db.add(obj)
            db.flush()

            selected_krs = item["krs"][:kr_count]
            for kr_data in selected_krs:
                kr = KeyResult(
                    workspace_id=workspace_id,
                    objective_id=obj.id,
                    title=kr_data["title"],
                    baseline_value=0.0,
                    current_value=0.0,
                    target_value=kr_data["target_value"],
                    unit=kr_data["unit"],
                    cadence="weekly",
                    status="active"
                )
                db.add(kr)
            
            created_objectives.append(obj)

        db.commit()

        return {"objectives": [_serialize_objective(o) for o in created_objectives]}

    except Exception as e:
        print(f"Error in generate_ai_okrs: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# Key Results
# ==========================================

class KeyResultCreate(BaseModel):
    objective_id: int
    title: Optional[str] = None
    baseline_value: Optional[float] = 0.0
    current_value: Optional[float] = 0.0
    target_value: Optional[float] = 100.0
    unit: Optional[str] = "%"
    cadence: Optional[str] = "weekly"
    status: Optional[str] = "active"


class KeyResultUpdate(BaseModel):
    title: Optional[str] = None
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    unit: Optional[str] = None
    cadence: Optional[str] = None
    status: Optional[str] = None


@router.get("/key-results")
def list_key_results(
    workspace_id: int,
    objective_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    query = db.query(KeyResult).filter(KeyResult.workspace_id == workspace_id)
    if objective_id:
        query = query.filter(KeyResult.objective_id == objective_id)
    krs = query.order_by(KeyResult.created_at.asc()).all()
    return {"key_results": [_serialize_key_result(k) for k in krs]}


@router.post("/key-results")
def create_key_result(
    workspace_id: int,
    data: KeyResultCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    obj = db.query(OkrObjective).filter(OkrObjective.id == data.objective_id, OkrObjective.workspace_id == workspace_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Objective not found")

    kr = KeyResult(
        workspace_id=workspace_id,
        objective_id=data.objective_id,
        title=data.title,
        baseline_value=data.baseline_value if data.baseline_value is not None else 0.0,
        current_value=data.current_value if data.current_value is not None else 0.0,
        target_value=data.target_value if data.target_value is not None else 100.0,
        unit=data.unit or "%",
        cadence=data.cadence or "weekly",
        status=data.status or "active",
    )
    db.add(kr)
    db.commit()
    db.refresh(kr)
    return _serialize_key_result(kr)


@router.put("/key-results/{key_result_id}")
def update_key_result(
    key_result_id: int,
    workspace_id: int,
    data: KeyResultUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    kr = db.query(KeyResult).filter(KeyResult.id == key_result_id, KeyResult.workspace_id == workspace_id).first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key Result not found")

    if data.baseline_value is not None:
        kr.baseline_value = data.baseline_value
    if data.current_value is not None:
        kr.current_value = data.current_value
    if data.target_value is not None:
        kr.target_value = data.target_value
    if data.unit is not None:
        kr.unit = data.unit
    if data.cadence is not None:
        kr.cadence = data.cadence
    if data.status is not None:
        kr.status = data.status

    db.commit()
    db.refresh(kr)
    return _serialize_key_result(kr)


@router.delete("/key-results/{key_result_id}")
def delete_key_result(
    key_result_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    kr = db.query(KeyResult).filter(KeyResult.id == key_result_id, KeyResult.workspace_id == workspace_id).first()
    if not kr:
        raise HTTPException(status_code=404, detail="Key Result not found")

    db.delete(kr)
    db.commit()
    return {"status": "deleted", "id": str(key_result_id)}
