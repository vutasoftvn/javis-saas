from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from business.marketing.models import (
    MarketingExperiment,
    MarketingLearning,
    MarketingDecision,
)
from business.marketing.models_validation import Assumption, Evidence


class LearningLoopService:
    """
    Step 6: Learning Loop & Decision Journal (§36 - §39 trong E3.md).
    Trả lời 5 câu hỏi cốt lõi:
    1. What happened?
    2. Why?
    3. What did we learn?
    4. Which assumption changed?
    5. What should we do next?
    """

    @classmethod
    def evaluate_learning_loop(
        cls,
        experiment: Optional[MarketingExperiment],
        assumption: Optional[Assumption],
        observations: Dict[str, Any],
        actual_outcome: str,
    ) -> Dict[str, Any]:
        """
        AI tổng hợp 5 câu hỏi vòng lặp học hỏi từ kết quả thử nghiệm/chiến dịch.
        """
        conclusion = experiment.conclusion if experiment else "supported"
        statement = assumption.statement if assumption else (experiment.hypothesis if experiment else "Mô hình tăng trưởng")
        
        # 1. What happened?
        q1_what_happened = f"Thực hiện thử nghiệm '{experiment.hypothesis if experiment else 'Chiến dịch'}'. Kết quả thực tế: {actual_outcome}."

        # 2. Why?
        if conclusion == "supported":
            q2_why = "Khách hàng phản hồi tích cực vì giải pháp đánh đúng nỗi đau cấp thiết và thông điệp rõ ràng."
            q5_action = "scale"
            next_step = f"Mở rộng phân phối chiến dịch và chuẩn bị kịch bản bán hàng cho tệp khách hàng tiềm năng."
            decision_text = "Tiếp tục mở rộng (Scale)"
            decision_reason = f"Giả định '{statement}' đã được chứng minh bởi dữ liệu thực tế."
        elif conclusion == "contradicted":
            q2_why = "Tỷ lệ chuyển đổi thấp hoặc khách hàng không quan tâm do sai đối tượng mục tiêu hoặc định giá chưa phù hợp."
            q5_action = "stop"
            next_step = f"Dừng kênh hiện tại, cập nhật lại ICP/Offer Canvas và phỏng vấn thêm 5 khách hàng để tìm nguyên nhân gốc."
            decision_text = "Dừng thử nghiệm (Stop/Pivot)"
            decision_reason = f"Dữ liệu thực tế bác bỏ giả định: '{statement}'."
        else:
            q2_why = "Cỡ mẫu chưa đủ lớn hoặc tín hiệu thị trường phân tán, cần thêm dữ liệu để kết luận."
            q5_action = "retest"
            next_step = f"Điều chỉnh thông điệp và kéo dài thời gian thử nghiệm thêm 5 ngày để gom đủ mẫu."
            decision_text = "Thử nghiệm lại với mẫu lớn hơn (Retest)"
            decision_reason = "Tín hiệu chưa đủ ý nghĩa thống kê."

        # 3. What did we learn?
        q3_what_we_learned = f"Bài học: {actual_outcome}. Cần tập trung vào giá trị cốt lõi giải quyết nỗi đau của ICP."

        # 4. Which assumption changed?
        q4_assumption_changed = f"Giả định '{statement}' chuyển sang trạng thái: {assumption.status if assumption else conclusion} (Confidence: {assumption.confidence if assumption else 'high'})."

        # 5. What should we do next?
        q5_what_next = next_step

        return {
            "q1_what_happened": q1_what_happened,
            "q2_why": q2_why,
            "q3_what_we_learned": q3_what_we_learned,
            "q4_assumption_changed": q4_assumption_changed,
            "q5_what_should_we_do_next": q5_what_next,
            "decision_recommendation": q5_action,
            "proposed_decision": {
                "question": f"Có nên mở rộng tiếp thị cho giả định '{statement}' không?",
                "decision": decision_text,
                "reason": decision_reason,
                "next_action": next_step,
            }
        }

    @classmethod
    def record_learning_and_decision(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: Optional[int],
        experiment_id: Optional[int],
        campaign_id: Optional[int],
        summary: str,
        observation: str,
        hypothesis: str,
        action: str,
        result: str,
        learning: str,
        affected_assumption_ids: List[str],
        evidence_ids: List[str],
        decision_recommendation: str,
        create_decision_log: bool = True,
        decision_question: Optional[str] = None,
        decision_text: Optional[str] = None,
        decision_reason: Optional[str] = None,
        next_action: Optional[str] = None,
        owner: str = "Founder",
    ) -> Tuple[MarketingLearning, Optional[MarketingDecision]]:
        """
        Lưu Learning Object (§37) và Decision Journal (§38, §39, §53).
        """
        # 1. Tạo Learning Object
        learning_obj = MarketingLearning(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            experiment_id=experiment_id,
            campaign_id=campaign_id,
            summary=summary,
            observation=observation,
            hypothesis=hypothesis,
            action=action,
            result=result,
            learning=learning,
            affected_assumption_ids=affected_assumption_ids,
            evidence_ids=evidence_ids,
            decision_recommendation=decision_recommendation,
            confidence="high" if decision_recommendation in ("scale", "stop") else "medium",
        )
        db.add(learning_obj)
        db.flush()

        # 2. Tạo Decision Log nếu được yêu cầu
        decision_log = None
        if create_decision_log:
            decision_log = MarketingDecision(
                workspace_id=workspace_id,
                brain_id=brain_id,
                project_id=project_id,
                experiment_id=experiment_id,
                campaign_id=campaign_id,
                title=f"DEC-{learning_obj.id}: Quyết định từ Learning Loop",
                question=decision_question or f"Quyết định tiếp theo cho thử nghiệm {experiment_id or ''}?",
                decision=decision_text or f"Khuyến nghị: {decision_recommendation.upper()}",
                reason=decision_reason or learning,
                based_on_assumption_ids=affected_assumption_ids,
                based_on_evidence_ids=evidence_ids,
                next_action=next_action or f"Thực thi hành động {decision_recommendation}",
                owner=owner,
            )
            db.add(decision_log)
            db.flush()

        return learning_obj, decision_log
