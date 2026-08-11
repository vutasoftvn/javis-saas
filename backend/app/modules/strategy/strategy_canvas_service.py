from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.tenancy import (
    get_canvas_scoped,
    get_context_pack_scoped,
    get_evidence_items_scoped,
    get_revision_scoped,
)
from app.db.models import (
    AuditLog,
    Brain,
    ContextPack,
    ContextPackSource,
    CoreValue,
    EvidenceItem,
    StrategyCanvas,
    StrategyFoundation,
    StrategyRevision,
)
from app.db.repositories.vault_repo import check_permission

# Đúng bất biến Strategic Canvas 1-1-3 §3.1/§4.1.
REVISION_EDITABLE_STATUSES = {"draft", "changes_requested"}


class StrategyCanvasService:
    """Theo mẫu VaultRepository (app/db/repositories/vault_repo.py): mỗi method tự
    check permission, enforce invariant, ghi AuditLog và commit trong cùng transaction.
    Tập trung logic nghiệp vụ ở đây thay vì rải trong app/api/strategy.py, đúng yêu cầu
    §6.1 của spec (API handler chỉ xác thực request + gọi service)."""

    def __init__(self, db: Session, user_id: int, workspace_id: int, role: str):
        self.db = db
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.role = role

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_canvas(self, canvas_id: int) -> StrategyCanvas:
        return get_canvas_scoped(self.db, canvas_id, self.workspace_id)

    def _get_revision(self, revision_id: int) -> StrategyRevision:
        return get_revision_scoped(self.db, revision_id, self.workspace_id)

    def _get_context_pack(self, context_pack_id: int) -> ContextPack:
        return get_context_pack_scoped(self.db, context_pack_id, self.workspace_id)

    def _audit(self, action: str, target_type: str, target_id: int, metadata: Optional[dict] = None):
        # workspace_id is always merged in here (not left to each of the ~9 call
        # sites to remember) - it's the field list_audit_events filters on to
        # keep the audit trail tenant-scoped; a missing workspace_id makes an
        # entry invisible to the correct workspace's audit view.
        self.db.add(AuditLog(
            actor_type="user",
            actor_id=self.user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_jsonb={**(metadata or {}), "workspace_id": str(self.workspace_id)},
        ))

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def list_canvases(self) -> list[StrategyCanvas]:
        return self.db.query(StrategyCanvas).filter(
            StrategyCanvas.workspace_id == self.workspace_id
        ).order_by(StrategyCanvas.created_at.asc()).all()

    def get_canvas(self, canvas_id: int) -> StrategyCanvas:
        return self._get_canvas(canvas_id)

    def create_canvas(self, name: str, description: Optional[str] = None) -> StrategyCanvas:
        check_permission(self.role, "editor")

        # MVP một workspace luôn có đúng 1 Brain (tạo cùng lúc ở POST /auth/register) -
        # nhưng vẫn guard rõ ràng thay vì để FK NOT NULL ném lỗi 500 khó hiểu nếu một
        # workspace nào đó (dữ liệu cũ, seed thủ công...) chưa có Brain.
        brain = self.db.query(Brain).filter(Brain.workspace_id == self.workspace_id).first()
        if not brain:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Workspace chưa khởi tạo Brain, không thể tạo Strategy Canvas",
            )

        canvas = StrategyCanvas(
            workspace_id=self.workspace_id,
            brain_id=brain.id,
            name=name,
            description=description,
            status="draft",
            created_by=self.user_id,
        )
        self.db.add(canvas)
        self.db.flush()
        self._audit("create_strategy_canvas", "strategy_canvas", canvas.id, {"name": name})
        self.db.commit()
        self.db.refresh(canvas)
        return canvas

    def update_canvas(self, canvas_id: int, name: Optional[str] = None, description: Optional[str] = None) -> StrategyCanvas:
        check_permission(self.role, "editor")
        canvas = self._get_canvas(canvas_id)
        if name is not None:
            canvas.name = name
        if description is not None:
            canvas.description = description
        self._audit("update_strategy_canvas", "strategy_canvas", canvas.id, {"name": canvas.name})
        self.db.commit()
        self.db.refresh(canvas)
        return canvas

    def delete_canvas(self, canvas_id: int) -> None:
        check_permission(self.role, "editor")
        canvas = self._get_canvas(canvas_id)
        
        revisions = self.db.query(StrategyRevision).filter(StrategyRevision.canvas_id == canvas.id).all()
        rev_ids = [r.id for r in revisions]
        
        if rev_ids:
            # 1. Xóa ContextPack và các links
            cps = self.db.query(ContextPack).filter(ContextPack.strategy_revision_id.in_(rev_ids)).all()
            for cp in cps:
                self.db.query(ContextPackSource).filter(ContextPackSource.context_pack_id == cp.id).delete(synchronize_session=False)
                self.db.delete(cp)
                
            # 2. Xóa CoreValue và StrategyFoundation
            foundations = self.db.query(StrategyFoundation).filter(StrategyFoundation.strategy_revision_id.in_(rev_ids)).all()
            for f in foundations:
                self.db.query(CoreValue).filter(CoreValue.foundation_id == f.id).delete(synchronize_session=False)
                self.db.delete(f)
                
            # 3. Gỡ parent_revision_id để tránh ràng buộc FK
            for r in revisions:
                r.parent_revision_id = None
            self.db.flush()
            
            # 4. Xóa revisions
            for r in revisions:
                self.db.delete(r)
                
        self._audit("delete_strategy_canvas", "strategy_canvas", canvas.id, {"name": canvas.name})
        self.db.delete(canvas)
        self.db.commit()

    # ------------------------------------------------------------------
    # Revision lifecycle
    # ------------------------------------------------------------------

    def get_revision(self, revision_id: int) -> StrategyRevision:
        return self._get_revision(revision_id)

    def create_revision(self, canvas_id: int, base_revision_id: Optional[int] = None) -> StrategyRevision:
        check_permission(self.role, "editor")
        canvas = self._get_canvas(canvas_id)

        base_revision = None
        if base_revision_id is not None:
            base_revision = self._get_revision(base_revision_id)
            if base_revision.canvas_id != canvas.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Revision not found")

        next_no = (self.db.query(func.max(StrategyRevision.revision_no))
                   .filter(StrategyRevision.canvas_id == canvas.id).scalar() or 0) + 1

        revision = StrategyRevision(
            canvas_id=canvas.id,
            revision_no=next_no,
            status="draft",
            parent_revision_id=base_revision.id if base_revision else None,
            created_by=self.user_id,
        )
        self.db.add(revision)
        self.db.flush()

        # Copy Foundation + 3 Core Values từ revision cha làm seed draft, để founder
        # không phải nhập lại từ đầu mỗi lần muốn sửa một chi tiết sau khi đã approve
        # (đúng tinh thần "sửa phải tạo revision mới", không phải "gõ lại từ số 0").
        if base_revision is not None:
            base_foundation = self.db.query(StrategyFoundation).filter(
                StrategyFoundation.strategy_revision_id == base_revision.id
            ).first()
            if base_foundation is not None:
                new_foundation = StrategyFoundation(
                    strategy_revision_id=revision.id,
                    vision=base_foundation.vision,
                    mission=base_foundation.mission,
                    status="draft",
                )
                self.db.add(new_foundation)
                self.db.flush()
                base_values = self.db.query(CoreValue).filter(
                    CoreValue.foundation_id == base_foundation.id
                ).all()
                for v in base_values:
                    self.db.add(CoreValue(
                        foundation_id=new_foundation.id,
                        slot_no=v.slot_no,
                        title=v.title,
                        description=v.description,
                        decision_rule=v.decision_rule,
                    ))

        self._audit("create_strategy_revision", "strategy_revision", revision.id, {
            "canvas_id": str(canvas.id), "revision_no": next_no, "base_revision_id": str(base_revision_id) if base_revision_id else None,
        })
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def _foundation_is_complete(self, revision_id: int) -> bool:
        foundation = self.db.query(StrategyFoundation).filter(
            StrategyFoundation.strategy_revision_id == revision_id
        ).first()
        if not foundation or not foundation.vision or not foundation.mission:
            return False
        values = self.db.query(CoreValue).filter(CoreValue.foundation_id == foundation.id).all()
        if len(values) != 3:
            return False
        if {v.slot_no for v in values} != {1, 2, 3}:
            return False
        return all(v.decision_rule and v.decision_rule.strip() for v in values)

    def submit_review(self, revision_id: int) -> StrategyRevision:
        check_permission(self.role, "editor")
        revision = self._get_revision(revision_id)
        if revision.status not in REVISION_EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revision đang ở trạng thái '{revision.status}', không thể gửi duyệt",
            )
        if not self._foundation_is_complete(revision.id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Foundation chưa đủ 1 Vision, 1 Mission và 3 Core Values hợp lệ",
            )
        revision.status = "in_review"
        self._audit("submit_review_strategy_revision", "strategy_revision", revision.id)
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def approve_revision(self, revision_id: int, note: Optional[str] = None) -> StrategyRevision:
        # Founder trong MVP một-người luôn được gán role "admin" lúc đăng ký
        # (POST /auth/register) - role "owner" không bao giờ được gán ở đâu trong hệ
        # thống hiện tại, nên gate "owner-only" sẽ khiến không ai approve được gì.
        check_permission(self.role, "admin")
        revision = self._get_revision(revision_id)
        if revision.status != "in_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revision đang ở trạng thái '{revision.status}', phải 'in_review' mới approve được",
            )

        # Bắt buộc hạ revision approved cũ (nếu có) xuống superseded VÀ flush TRƯỚC khi
        # set revision này thành approved - nếu làm ngược lại sẽ vi phạm unique partial
        # index one_approved_revision_per_canvas ngay trong transaction.
        previous_approved = self.db.query(StrategyRevision).filter(
            StrategyRevision.canvas_id == revision.canvas_id,
            StrategyRevision.status == "approved",
            StrategyRevision.id != revision.id,
        ).first()
        if previous_approved is not None:
            previous_approved.status = "superseded"
            self.db.flush()

        revision.status = "approved"
        revision.approved_by = self.user_id
        revision.approved_at = datetime.utcnow()
        self._audit("approve_strategy_revision", "strategy_revision", revision.id, {
            "previous_approved_revision_id": str(previous_approved.id) if previous_approved else None,
            "note": note,
        })
        self.db.commit()
        self.db.refresh(revision)
        return revision

    def request_changes(self, revision_id: int, reason: str) -> StrategyRevision:
        check_permission(self.role, "editor")
        revision = self._get_revision(revision_id)
        if revision.status != "in_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revision đang ở trạng thái '{revision.status}', phải 'in_review' mới request-changes được",
            )
        revision.status = "changes_requested"
        # "reason" là ghi chú review, khác mục đích với stale_reason (dành cho lý do
        # downstream bị đánh dấu lỗi thời) - lưu vào audit metadata, không lạm dụng cột đó.
        self._audit("request_changes_strategy_revision", "strategy_revision", revision.id, {"reason": reason})
        self.db.commit()
        self.db.refresh(revision)
        return revision

    # ------------------------------------------------------------------
    # Foundation (1 Vision, 1 Mission, 3 Core Values)
    # ------------------------------------------------------------------

    def get_foundation(self, revision_id: int):
        revision = self._get_revision(revision_id)
        foundation = self.db.query(StrategyFoundation).filter(
            StrategyFoundation.strategy_revision_id == revision.id
        ).first()
        values = []
        if foundation is not None:
            values = self.db.query(CoreValue).filter(
                CoreValue.foundation_id == foundation.id
            ).order_by(CoreValue.slot_no.asc()).all()
        return foundation, values

    def save_foundation(self, revision_id: int, vision: str, mission: str, values: list[dict]) -> tuple:
        check_permission(self.role, "editor")
        revision = self._get_revision(revision_id)
        if revision.status not in REVISION_EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Revision đang ở trạng thái '{revision.status}', không thể sửa Foundation",
            )

        if not vision or not (20 <= len(vision) <= 500):
            raise HTTPException(status_code=422, detail="Vision phải có độ dài 20-500 ký tự")
        if not mission or not (20 <= len(mission) <= 500):
            raise HTTPException(status_code=422, detail="Mission phải có độ dài 20-500 ký tự")
        if len(values) != 3:
            raise HTTPException(status_code=422, detail="Phải có đúng 3 Core Values")
        slot_nos = [v.get("slot_no") for v in values]
        if set(slot_nos) != {1, 2, 3}:
            raise HTTPException(status_code=422, detail="Core Values phải đánh số đúng 1, 2, 3, không trùng")
        for v in values:
            if not v.get("title") or not v.get("description") or not (v.get("decision_rule") or "").strip():
                raise HTTPException(
                    status_code=422,
                    detail="Mỗi Core Value phải có title, description và decision_rule",
                )

        foundation = self.db.query(StrategyFoundation).filter(
            StrategyFoundation.strategy_revision_id == revision.id
        ).first()
        if foundation is None:
            foundation = StrategyFoundation(strategy_revision_id=revision.id, status="draft")
            self.db.add(foundation)
            self.db.flush()

        foundation.vision = vision
        foundation.mission = mission

        # Ghi đè toàn bộ 3 core values mỗi lần lưu (input luôn là toàn bộ 1-1-3, không
        # phải diff-update từng value) - đơn giản và không thể để sót slot cũ.
        self.db.query(CoreValue).filter(CoreValue.foundation_id == foundation.id).delete()
        self.db.flush()
        for v in values:
            self.db.add(CoreValue(
                foundation_id=foundation.id,
                slot_no=v["slot_no"],
                title=v["title"],
                description=v["description"],
                decision_rule=v["decision_rule"],
            ))

        self._audit("save_strategy_foundation", "strategy_foundation", foundation.id, {"revision_id": str(revision.id)})
        self.db.commit()
        self.db.refresh(foundation)
        return self.get_foundation(revision_id)

    # ------------------------------------------------------------------
    # Context Pack + Evidence
    # ------------------------------------------------------------------

    def create_context_pack(
        self, revision_id: int,
        business_context: Optional[dict] = None,
        internal_resources: Optional[dict] = None,
    ) -> ContextPack:
        check_permission(self.role, "editor")
        revision = self._get_revision(revision_id)
        pack = ContextPack(
            workspace_id=self.workspace_id,
            strategy_revision_id=revision.id,
            business_context=business_context or {},
            internal_resources=internal_resources or {},
            status="draft",
        )
        self.db.add(pack)
        self.db.flush()
        self._audit("create_context_pack", "context_pack", pack.id, {"revision_id": str(revision.id)})
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def update_context_pack(
        self, context_pack_id: int,
        business_context: Optional[dict] = None,
        internal_resources: Optional[dict] = None,
    ) -> ContextPack:
        check_permission(self.role, "editor")
        pack = self._get_context_pack(context_pack_id)
        if pack.status not in {"draft", "ready_for_review"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Context Pack đang ở trạng thái '{pack.status}', không thể sửa",
            )
        if business_context is not None:
            pack.business_context = business_context
        if internal_resources is not None:
            pack.internal_resources = internal_resources
        self._audit("update_context_pack", "context_pack", pack.id)
        self.db.commit()
        self.db.refresh(pack)
        return pack

    def link_evidence(self, context_pack_id: int, evidence_ids: list[int]) -> list[ContextPackSource]:
        check_permission(self.role, "editor")
        pack = self._get_context_pack(context_pack_id)
        # Verify TỪNG evidence_id thuộc đúng workspace trước khi link - đây chính là
        # chỗ dễ tái diễn lỗi cross-tenant lần thứ 5 nếu bỏ qua bước này.
        items = get_evidence_items_scoped(self.db, evidence_ids, self.workspace_id)

        existing_evidence_ids = {
            row.evidence_id for row in self.db.query(ContextPackSource).filter(
                ContextPackSource.context_pack_id == pack.id,
                ContextPackSource.evidence_id.isnot(None),
            ).all()
        }

        created = []
        for item in items:
            if item.id in existing_evidence_ids:
                continue
            link = ContextPackSource(
                workspace_id=self.workspace_id,
                context_pack_id=pack.id,
                evidence_id=item.id,
                source_type="evidence",
                included_by=self.user_id,
            )
            self.db.add(link)
            created.append(link)

        if created:
            self.db.flush()
            self._audit("link_evidence_context_pack", "context_pack", pack.id, {
                "evidence_ids": [str(i.id) for i in items],
            })
        self.db.commit()
        return created

    def approve_context_pack(self, context_pack_id: int) -> ContextPack:
        check_permission(self.role, "admin")
        pack = self._get_context_pack(context_pack_id)
        if pack.status == "approved":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Context Pack đã được duyệt")
        pack.status = "approved"
        pack.approved_by = self.user_id
        pack.approved_at = datetime.utcnow()
        self._audit("approve_context_pack", "context_pack", pack.id)
        self.db.commit()
        self.db.refresh(pack)
        return pack

    # ------------------------------------------------------------------
    # Evidence library
    # ------------------------------------------------------------------

    def create_evidence(
        self, title: str, summary: str, source_type: str, reliability: str,
        source_url_or_vault_uri: Optional[str] = None,
        published_at: Optional[datetime] = None,
        tags: Optional[list] = None,
    ) -> EvidenceItem:
        # Không cần permission cao hơn "đã là thành viên workspace" - đúng tinh thần
        # spec §2: Contributor được thêm evidence, không cần quyền chốt chiến lược.
        item = EvidenceItem(
            workspace_id=self.workspace_id,
            title=title,
            summary=summary,
            source_type=source_type,
            source_url_or_vault_uri=source_url_or_vault_uri,
            published_at=published_at,
            reliability=reliability,
            tags=tags or [],
            created_by=self.user_id,
        )
        self.db.add(item)
        self.db.flush()
        self._audit("create_evidence_item", "evidence_item", item.id, {"title": title})
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_evidence(
        self,
        source_type: Optional[str] = None,
        reliability: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[EvidenceItem]:
        query = self.db.query(EvidenceItem).filter(EvidenceItem.workspace_id == self.workspace_id)
        if source_type:
            query = query.filter(EvidenceItem.source_type == source_type)
        if reliability:
            query = query.filter(EvidenceItem.reliability == reliability)
        if tag:
            query = query.filter(EvidenceItem.tags.op('?')(tag))
        return query.order_by(EvidenceItem.created_at.desc()).all()
