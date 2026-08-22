import copy
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from business.marketing.models_validation import (
    CanvasRevision,
    Evidence,
    Assumption,
)


class CanvasRevisionService:
    """
    Ground Truth Feedback Loop & Canvas Revision History (§41 - §43 trong E3.md).
    Hệ thống không âm thầm sửa đè Canvas mà tạo một Canvas Change Proposal
    để Founder phê duyệt trước khi cập nhật.
    """

    @classmethod
    def propose_revision_from_evidence(
        cls,
        canvas_type: str,
        current_canvas: Dict[str, Any],
        evidence_statement: str,
        is_contradiction: bool,
        affected_field: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI đề xuất cập nhật Ground Truth Canvas dựa trên Evidence/Learning mới (§42).
        """
        new_snapshot = copy.deepcopy(current_canvas)
        changed_fields: List[str] = []

        ev_lower = evidence_statement.lower()
        if canvas_type == "customer_research":
            target_field = affected_field or (
                "pains" if any(w in ev_lower for w in ("pain", "nỗi đau", "khó khăn", "phỏng vấn", "vấn đề", "gate", "yêu cầu", "rào cản", "lo ngại"))
                else "icp"
            )
            changed_fields.append(target_field)
            if is_contradiction:
                reason = f"Bằng chứng mâu thuẫn với nhận định ban đầu: {evidence_statement}. Cần loại bỏ hoặc tinh chỉnh mục tiêu."
                new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Đã điều chỉnh theo evidence: {evidence_statement}]".strip()
            else:
                reason = f"Bằng chứng mới củng cố và làm rõ nét: {evidence_statement}."
                new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Xác thực bởi evidence: {evidence_statement}]".strip()

        elif canvas_type == "offer":
            target_field = affected_field or (
                "pricing" if any(w in ev_lower for w in ("pricing", "giá", "ngân sách", "500k", "triệu", "chi phí", "đặt cọc", "trả"))
                else "core_offer"
            )
            changed_fields.append(target_field)
            if is_contradiction:
                reason = f"Dữ liệu thị trường bác bỏ mức giá/offer cũ: {evidence_statement}."
                new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Cần hạ giá/sửa offer: {evidence_statement}]".strip()
            else:
                reason = f"Mức giá/offer đã được khách hàng sẵn sàng chi trả: {evidence_statement}."
                new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Validated: {evidence_statement}]".strip()

        elif canvas_type == "product_marketing":
            target_field = affected_field or "positioning"
            changed_fields.append(target_field)
            reason = f"Cập nhật định vị sản phẩm dựa trên tín hiệu: {evidence_statement}."
            new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Refined: {evidence_statement}]".strip()

        else:
            target_field = affected_field or "brand_voice"
            changed_fields.append(target_field)
            reason = f"Cập nhật tài liệu thương hiệu dựa trên: {evidence_statement}."
            new_snapshot[target_field] = f"{current_canvas.get(target_field, '')} [Updated: {evidence_statement}]".strip()

        return {
            "canvas_type": canvas_type,
            "changed_fields": changed_fields,
            "previous_snapshot": current_canvas,
            "new_snapshot": new_snapshot,
            "reason": reason,
            "is_contradiction": is_contradiction,
        }

    @classmethod
    def create_revision_proposal(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: Optional[int],
        canvas_type: str,
        changed_fields: List[str],
        previous_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any],
        reason: str,
        evidence_ids: List[str],
        auto_approve: bool = False,
        approved_by: Optional[int] = None,
    ) -> CanvasRevision:
        """
        Tạo Canvas Revision Request / Proposal (§41, §43).
        """
        revision = CanvasRevision(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            canvas_type=canvas_type,
            status="approved" if auto_approve else "pending_review",
            changed_fields=changed_fields,
            previous_snapshot=previous_snapshot,
            new_snapshot=new_snapshot,
            reason=reason,
            evidence_ids=evidence_ids,
            approved_by=approved_by if auto_approve else None,
        )
        db.add(revision)
        db.flush()
        return revision

    @classmethod
    def approve_revision(
        cls,
        db: Session,
        workspace_id: int,
        revision_id: int,
        approved_by: Optional[int] = None,
    ) -> Optional[CanvasRevision]:
        """
        Founder phê duyệt áp dụng cập nhật Canvas (§41, §103).
        """
        rev = db.query(CanvasRevision).filter(
            CanvasRevision.id == revision_id,
            CanvasRevision.workspace_id == workspace_id,
        ).first()
        if not rev:
            return None

        rev.status = "approved"
        rev.approved_by = approved_by
        db.flush()
        return rev

    @classmethod
    def reject_revision(
        cls,
        db: Session,
        workspace_id: int,
        revision_id: int,
    ) -> Optional[CanvasRevision]:
        """
        Founder từ chối cập nhật Canvas.
        """
        rev = db.query(CanvasRevision).filter(
            CanvasRevision.id == revision_id,
            CanvasRevision.workspace_id == workspace_id,
        ).first()
        if not rev:
            return None

        rev.status = "rejected"
        db.flush()
        return rev
