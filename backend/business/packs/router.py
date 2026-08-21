"""Business Knowledge Pack API Router."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_workspace_member
from db.models import WorkspaceMember
from db.session import get_db
from business.packs.service import BusinessPackService
from business.packs.schemas import (
    TemplateBundle,
    CapabilityDefinition,
    SOPDefinition,
)

router = APIRouter()
pack_service = BusinessPackService()


class OverrideCreateRequest(BaseModel):
    asset_id: str = Field(..., description="Định danh tài sản, ví dụ: governance.templates.nda-vn")
    asset_type: str = Field(..., description="Loại tài sản: template, sop, capability, reference")
    content_override: Dict[str, Any] = Field(default_factory=dict, description="Metadata / schema override")
    body_override: Optional[str] = Field(None, description="Markdown body override (nếu có)")
    notes: Optional[str] = Field(None, description="Ghi chú lý do tùy biến của doanh nghiệp")


class LegalAnnotationRequest(BaseModel):
    legal_source_id: str = Field(..., description="Mã nguồn pháp lý, ví dụ: vn-law-doanh-nghiep-2020")
    applicability_status: str = Field("applicable", description="Trạng thái: applicable, partially_applicable, exempt, unknown")
    notes: List[str] = Field(default_factory=list, description="Ghi chú áp dụng nội bộ")
    linked_sops: Optional[List[str]] = Field(default_factory=list)
    linked_templates: Optional[List[str]] = Field(default_factory=list)


def _guard(workspace_id: int, member: WorkspaceMember) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden: Invalid workspace context")


def _guard_admin(workspace_id: int, member: WorkspaceMember) -> None:
    _guard(workspace_id, member)
    role = getattr(member, "role", "MEMBER").upper()
    if role not in ["ADMIN", "OWNER", "FOUNDER"]:
        raise HTTPException(status_code=403, detail="Admin or Founder privilege required for Business Pack customization")


@router.get("", summary="Liệt kê danh sách Business Knowledge Packs khả dụng")
async def list_packs(
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    packs = await pack_service.list_available_packs(db, workspace_id)
    return {"status": "success", "data": packs}


@router.get("/{pack_id}", summary="Lấy chi tiết một Business Knowledge Pack")
async def get_pack_details(
    pack_id: str,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    pack = await pack_service.get_pack_details(db, workspace_id, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Business pack '{pack_id}' not found")
    return {"status": "success", "data": pack}


@router.get("/{pack_id}/capabilities/{capability_id}", summary="Phân giải Capability Definition")
async def get_capability(
    pack_id: str,
    capability_id: str,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    cap = await pack_service.resolver.resolve_capability(db, workspace_id, pack_id, capability_id)
    if not cap:
        raise HTTPException(status_code=404, detail=f"Capability '{capability_id}' not found in pack '{pack_id}'")
    return {"status": "success", "data": cap.dict()}


@router.get("/{pack_id}/templates/{template_id}", summary="Phân giải Template (ưu tiên Company Override)")
async def get_template(
    pack_id: str,
    template_id: str,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    bundle = await pack_service.resolver.resolve_template(db, workspace_id, pack_id, template_id)
    if not bundle:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found in pack '{pack_id}'")
    return {"status": "success", "data": bundle.dict()}


@router.get("/{pack_id}/sops/{sop_id}", summary="Phân giải SOP (ưu tiên Company Override)")
async def get_sop(
    pack_id: str,
    sop_id: str,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    sop = await pack_service.resolver.resolve_sop(db, workspace_id, pack_id, sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail=f"SOP '{sop_id}' not found in pack '{pack_id}'")
    return {"status": "success", "data": sop.dict()}


@router.post("/{pack_id}/overrides", status_code=201, summary="Tạo hoặc cập nhật Company Override (Admin Only)")
async def create_override(
    pack_id: str,
    payload: OverrideCreateRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_admin(workspace_id, member)
    record = await pack_service.create_or_update_override(
        db=db,
        workspace_id=workspace_id,
        pack_id=pack_id,
        asset_id=payload.asset_id,
        asset_type=payload.asset_type,
        content_override=payload.content_override,
        body_override=payload.body_override,
        user_id=member.user_id,
        notes=payload.notes,
    )
    return {
        "status": "success",
        "data": {
            "id": str(record.id),
            "asset_id": record.asset_id,
            "pack_id": record.pack_id,
            "is_active": record.is_active,
            "version": record.version,
        },
    }


@router.delete("/{pack_id}/overrides/{asset_id}", summary="Khôi phục tài sản về Factory Default (Admin Only)")
async def reset_to_factory(
    pack_id: str,
    asset_id: str,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_admin(workspace_id, member)
    success = await pack_service.reset_to_factory(db, workspace_id, asset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"No active company override found for asset '{asset_id}'")
    return {"status": "success", "message": f"Asset '{asset_id}' reset to Factory Default"}


@router.get("/{pack_id}/legal/resolve", summary="Phân giải căn cứ pháp lý cho Capability")
async def resolve_legal_sources(
    pack_id: str,
    workspace_id: int = Query(...),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    sources = await pack_service.legal_resolver.resolve_legal_sources_for_capability(
        db=db,
        workspace_id=workspace_id,
        pack_id=pack_id,
        jurisdiction="VN",
        tags=tag_list,
    )
    return {"status": "success", "data": sources}


@router.post("/{pack_id}/legal/annotations", status_code=201, summary="Ghi chú diễn giải pháp lý doanh nghiệp (Admin Only)")
async def add_legal_annotation(
    pack_id: str,
    payload: LegalAnnotationRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_admin(workspace_id, member)
    record = await pack_service.legal_resolver.add_or_update_annotation(
        db=db,
        workspace_id=workspace_id,
        legal_source_id=payload.legal_source_id,
        applicability_status=payload.applicability_status,
        notes=payload.notes,
        user_id=member.user_id,
        linked_sops=payload.linked_sops,
        linked_templates=payload.linked_templates,
    )
    return {
        "status": "success",
        "data": {
            "id": str(record.id),
            "legal_source_id": record.legal_source_id,
            "applicability_status": record.applicability_status,
            "notes_count": len(record.notes),
        },
    }


# =========================================================================
# Phase 5: Update & Conflict Management Endpoints
# =========================================================================

class CheckUpdateRequest(BaseModel):
    update_manifest: Optional[Dict[str, Any]] = None


class ResolveConflictRequest(BaseModel):
    asset_id: str = Field(..., description="Mã tài sản, vd: governance.templates.nda-vn")
    resolution: str = Field(..., description="Chiến lược: KEEP_COMPANY, ACCEPT_FACTORY, MERGE, RESET_FACTORY")
    merged_body: Optional[str] = None
    merged_metadata: Optional[Dict[str, Any]] = None


class GenerateDiffRequest(BaseModel):
    old_content: str
    new_content: str
    from_label: str = "Old Factory"
    to_label: str = "Company Override / New Factory"


@router.post("/{pack_id}/updates/check", summary="Kiểm tra bản cập nhật và phát hiện xung đột ghi đè")
async def check_pack_updates(
    pack_id: str,
    payload: CheckUpdateRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard(workspace_id, member)
    from business.packs.update_engine import PackUpdateEngine
    engine = PackUpdateEngine(pack_service.loader)
    result = await engine.check_for_updates(
        db=db,
        workspace_id=workspace_id,
        pack_id=pack_id,
        update_manifest=payload.update_manifest,
    )
    return {"status": "success", "data": result}


@router.post("/{pack_id}/updates/diff", summary="Tạo bảng so sánh diff trực quan")
async def generate_diff(
    pack_id: str,
    payload: GenerateDiffRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    _guard(workspace_id, member)
    from business.packs.update_engine import PackUpdateEngine
    engine = PackUpdateEngine(pack_service.loader)
    diff_text = engine.generate_diff(
        old_text=payload.old_content,
        new_text=payload.new_content,
        from_label=payload.from_label,
        to_label=payload.to_label,
    )
    return {"status": "success", "data": {"diff": diff_text}}


@router.post("/{pack_id}/updates/resolve", summary="Giải quyết xung đột cập nhật (Admin Only)")
async def resolve_update_conflict(
    pack_id: str,
    payload: ResolveConflictRequest,
    workspace_id: int = Query(...),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: AsyncSession = Depends(get_db),
):
    _guard_admin(workspace_id, member)
    from business.packs.update_engine import PackUpdateEngine
    engine = PackUpdateEngine(pack_service.loader)
    res = await engine.apply_resolution(
        db=db,
        workspace_id=workspace_id,
        asset_id=payload.asset_id,
        resolution=payload.resolution,
        merged_body=payload.merged_body,
        merged_metadata=payload.merged_metadata,
        user_id=member.user_id,
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return {"status": "success", "data": res}
