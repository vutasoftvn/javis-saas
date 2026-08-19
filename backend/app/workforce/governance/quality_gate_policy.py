"""Cross-Cutting Quality Gate Policy (F4 Specification).

Chuyển đổi Anti-Pattern 'QA Agent' thành một Chính sách Thẩm định Chất lượng Xuyên suốt:
- Mọi WorkProduct được sinh ra từ bất kỳ Domain Agent nào (Sales, Marketing, Finance, Legal, Build)
  đều phải đi qua QualityGatePolicy để đánh giá trước khi bàn giao cho Founder.
- Tiêu chí đánh giá 4 chiều:
  1. Completeness: Tính đầy đủ, cấu trúc rõ ràng.
  2. Evidence-Backed: Có dữ liệu dẫn chứng, số liệu kiểm chứng (F1/F3).
  3. Policy & Budget Compliant: Không vi phạm ngân sách hoặc rủi ro pháp lý.
  4. Actionable: Có các bước hành động tiếp theo cụ thể.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class QualityGateEvaluation(BaseModel):
    passed: bool
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Điểm chất lượng từ 0 - 100")
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    is_evidence_backed: bool
    is_policy_compliant: bool
    is_actionable: bool
    feedback_notes: List[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class QualityGatePolicy:
    """Chính sách tự động kiểm tra chất lượng kết quả đầu ra của Domain Agents."""

    MIN_PASS_SCORE = 70.0

    @classmethod
    def evaluate_work_product(
        cls,
        title: str,
        content: str,
        domain: str = "GENERAL",
        evidence_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityGateEvaluation:
        """Đánh giá chất lượng của Work Product dựa trên 4 trụ cột F4."""
        feedback: List[str] = []
        metadata = metadata or {}
        text = f"{title}\n{content}".strip()

        # 1. Completeness (Độ hoàn thiện & cấu trúc)
        word_count = len(text.split())
        if word_count < 15:
            completeness = 0.3
            feedback.append("Nội dung quá ngắn gọn, thiếu chi tiết mô tả cần thiết.")
        elif word_count < 50:
            completeness = 0.7
            feedback.append("Nội dung cơ bản, có thể bổ sung thêm bối cảnh cụ thể.")
        else:
            completeness = 1.0

        # 2. Evidence-Backed (Bằng chứng & Dữ liệu)
        has_numbers = any(char.isdigit() for char in text)
        has_evidence_ref = bool(evidence_ids) or any(k in text.lower() for k in ["bằng chứng", "nguồn", "dữ liệu", "khảo sát", "phân tích", "báo cáo", "evidence"])
        
        if has_evidence_ref and has_numbers:
            is_evidence_backed = True
        elif has_numbers or has_evidence_ref:
            is_evidence_backed = True
        else:
            is_evidence_backed = False
            feedback.append("Thiếu số liệu hoặc dẫn chứng kiểm chứng thực tế.")

        # 3. Policy & Budget Compliance
        is_policy_compliant = True
        lower_text = text.lower()
        if "vượt ngân sách" in lower_text or "vi phạm" in lower_text or "rủi ro cao" in lower_text:
            if not metadata.get("risk_acknowledged", False):
                is_policy_compliant = False
                feedback.append("Phát hiện yếu tố rủi ro hoặc vượt ngân sách chưa được phê duyệt.")

        # 4. Actionability (Tính khả thi & Bước hành động)
        action_keywords = ["hành động", "bước tiếp theo", "kế hoạch", "triển khai", "đề xuất", "gợi ý", "action", "next step", "todo"]
        is_actionable = any(k in lower_text for k in action_keywords)
        if not is_actionable:
            feedback.append("Cần bổ sung phần 'Bước tiếp theo / Next Actions' cụ thể cho Founder hoặc Team.")

        # Tính toán điểm tổng hợp (0 - 100)
        score = (
            (completeness * 30.0) +
            (30.0 if is_evidence_backed else 10.0) +
            (20.0 if is_policy_compliant else 0.0) +
            (20.0 if is_actionable else 5.0)
        )
        score = min(100.0, max(0.0, score))

        passed = (score >= cls.MIN_PASS_SCORE) and is_policy_compliant

        if passed and not feedback:
            feedback.append("Work Product đạt chuẩn chất lượng cao, sẵn sàng bàn giao cho Founder.")

        return QualityGateEvaluation(
            passed=passed,
            quality_score=score,
            completeness_score=completeness,
            is_evidence_backed=is_evidence_backed,
            is_policy_compliant=is_policy_compliant,
            is_actionable=is_actionable,
            feedback_notes=feedback,
            evaluated_at=datetime.utcnow(),
        )
