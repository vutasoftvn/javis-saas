import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_

from founder_os.validation.models import (
    ValidationAssumption,
    ValidationHypothesis,
    ValidationExperiment,
    ExperimentType,
    AssumptionStatus,
)
from founder_os.validation.schemas import (
    RiskMatrixResponse,
    RiskQuadrantItem,
    GeneratedHypothesisResponse,
    RecommendedExperimentResponse,
    HypothesisCreate,
    ExperimentCreate,
)
from founder_os.validation.service import ValidationEngineService
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)


class RiskPrioritizationService:
    @staticmethod
    def get_risk_matrix(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> RiskMatrixResponse:
        """
        Phân loại các giả định theo 4 góc phần tư Risk Matrix ($Importance \times Uncertainty$).
        - Critical Risk: Importance >= 4 & Uncertainty >= 4 (Điểm 16-25, vùng tử huyệt)
        - Monitor Risk: Importance >= 4 & Uncertainty <= 3
        - Exploratory Risk: Importance <= 3 & Uncertainty >= 4
        - Low Risk: Importance <= 3 & Uncertainty <= 3
        """
        assumptions = db.scalars(
            select(ValidationAssumption).where(
                and_(
                    ValidationAssumption.workspace_id == workspace_id,
                    ValidationAssumption.project_id == project_id,
                )
            ).order_by(desc(ValidationAssumption.risk_score))
        ).all()

        crit = []
        mon = []
        exp = []
        low = []
        highest = 0

        for a in assumptions:
            item = RiskQuadrantItem(
                id=a.id,
                category=a.category,
                statement=a.statement,
                importance=a.importance,
                uncertainty=a.uncertainty,
                risk_score=a.risk_score,
                status=a.status,
                confidence=a.confidence,
            )
            if a.risk_score > highest:
                highest = a.risk_score

            if a.importance >= 4 and a.uncertainty >= 4:
                crit.append(item)
            elif a.importance >= 4 and a.uncertainty <= 3:
                mon.append(item)
            elif a.importance <= 3 and a.uncertainty >= 4:
                exp.append(item)
            else:
                low.append(item)

        return RiskMatrixResponse(
            project_id=project_id,
            critical_risks=crit,
            monitor_risks=mon,
            exploratory_risks=exp,
            low_risks=low,
            total_assumptions=len(assumptions),
            highest_risk_score=highest,
        )

    @staticmethod
    def get_riskiest_assumptions(
        db: Session,
        workspace_id: int,
        project_id: int,
        limit: int = 5,
    ) -> List[ValidationAssumption]:
        return db.scalars(
            select(ValidationAssumption).where(
                and_(
                    ValidationAssumption.workspace_id == workspace_id,
                    ValidationAssumption.project_id == project_id,
                )
            ).order_by(desc(ValidationAssumption.risk_score)).limit(limit)
        ).all()

    @staticmethod
    async def generate_hypothesis_from_assumption(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        assumption_id: int,
        auto_save: bool = True,
    ) -> GeneratedHypothesisResponse:
        """
        AI Hypothesis Builder: Tự động chuyển đổi Assumption thành Testable Hypothesis (5 thành phần).
        """
        assumption = db.get(ValidationAssumption, assumption_id)
        if not assumption:
            raise ValueError(f"Assumption {assumption_id} not found")

        prompt = (
            f"You are COSA Hypothesis Builder. Convert this business assumption into a testable hypothesis with 5 parts:\n"
            f"- Action: Small concrete action to execute\n"
            f"- Target Segment: Specific group to test on\n"
            f"- Metric: Concrete measurable metric\n"
            f"- Threshold: Success threshold required to validate\n"
            f"- Timeframe Days: Integer number of days\n\n"
            f"Assumption Category: {assumption.category}\n"
            f"Assumption Statement: {assumption.statement}\n"
            f"Risk Score: {assumption.risk_score}/25\n\n"
            f"Respond with a valid JSON object ONLY:\n"
            f"{{\n"
            f'  "action": "...",\n'
            f'  "target_segment": "...",\n'
            f'  "metric": "...",\n'
            f'  "threshold": "...",\n'
            f'  "timeframe_days": 7,\n'
            f'  "rationale": "..."\n'
            f"}}"
        )

        try:
            worker_res = await run_worker_prompt(
                db=db,
                workspace_id=workspace_id,
                prompt=prompt,
                max_wait_seconds=30.0,
            )
            cleaned = worker_res.text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
            parsed = json.loads(cleaned)
        except Exception as e:
            logger.warning("generate_hypothesis_from_assumption LLM fallback: %s", e)
            parsed = {
                "action": f"Contact 20 potential customers regarding {assumption.category.lower()}",
                "target_segment": "Target customer segment",
                "metric": "Positive confirmation rate",
                "threshold": ">= 30% positive responses",
                "timeframe_days": 7,
                "rationale": "Standard customer validation threshold",
            }

        formatted_stmt = (
            f"IF [{parsed['action']}] FOR [{parsed['target_segment']}] "
            f"THEN [{parsed['metric']}] WILL REACH [{parsed['threshold']}] "
            f"WITHIN [{parsed.get('timeframe_days', 7)} DAYS]"
        )

        if auto_save:
            ValidationEngineService.build_hypothesis(
                db=db,
                workspace_id=workspace_id,
                brain_id=brain_id,
                project_id=project_id,
                hypo_in=HypothesisCreate(
                    assumption_id=assumption.id,
                    action=parsed["action"],
                    target_segment=parsed["target_segment"],
                    metric=parsed["metric"],
                    threshold=parsed["threshold"],
                    timeframe_days=parsed.get("timeframe_days", 7),
                ),
            )
            assumption.status = AssumptionStatus.HYPOTHESIZED.value
            db.commit()

        return GeneratedHypothesisResponse(
            assumption_id=assumption.id,
            action=parsed["action"],
            target_segment=parsed["target_segment"],
            metric=parsed["metric"],
            threshold=parsed["threshold"],
            timeframe_days=parsed.get("timeframe_days", 7),
            statement=formatted_stmt,
            rationale=parsed.get("rationale"),
        )

    @staticmethod
    async def recommend_experiment_for_hypothesis(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        hypothesis_id: int,
        auto_save: bool = True,
    ) -> RecommendedExperimentResponse:
        """
        Đề xuất Thử nghiệm nhỏ nhất (Smallest Useful Experiment) cho một Giả thuyết.
        """
        hypothesis = db.get(ValidationHypothesis, hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        prompt = (
            f"You are COSA Experiment Designer. Recommend the SMALLEST USEFUL EXPERIMENT to test this hypothesis.\n"
            f"Avoid full product builds. Prefer low-cost tests (Interviews, Landing page, Paid offer, Concierge MVP, Pricing calls).\n\n"
            f"Hypothesis Statement: {hypothesis.statement}\n"
            f"Action: {hypothesis.action}\n"
            f"Target: {hypothesis.target_segment}\n"
            f"Metric: {hypothesis.metric}\n"
            f"Threshold: {hypothesis.threshold}\n\n"
            f"Respond with a valid JSON object ONLY:\n"
            f"{{\n"
            f'  "experiment_type": "CUSTOMER_INTERVIEW / LANDING_PAGE / FAKE_DOOR / PAID_OFFER / PRICING_TEST",\n'
            f'  "name": "...",\n'
            f'  "description": "...",\n'
            f'  "smallest_useful_scope": "...",\n'
            f'  "success_threshold": "...",\n'
            f'  "duration_days": 7,\n'
            f'  "budget_amount": 0.0\n'
            f"}}"
        )

        try:
            worker_res = await run_worker_prompt(
                db=db,
                workspace_id=workspace_id,
                prompt=prompt,
                max_wait_seconds=30.0,
            )
            cleaned = worker_res.text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
            parsed = json.loads(cleaned)
        except Exception as e:
            logger.warning("recommend_experiment_for_hypothesis LLM fallback: %s", e)
            parsed = {
                "experiment_type": ExperimentType.CUSTOMER_INTERVIEW.value,
                "name": "Targeted Customer Outreach",
                "description": f"Direct outreach test for {hypothesis.target_segment}",
                "smallest_useful_scope": "10-20 qualified direct contacts",
                "success_threshold": hypothesis.threshold,
                "duration_days": hypothesis.timeframe_days,
                "budget_amount": 0.0,
            }

        exp_type_val = parsed.get("experiment_type", "CUSTOMER_INTERVIEW")
        exp_type_enum = (
            ExperimentType(exp_type_val)
            if exp_type_val in ExperimentType.__members__
            else ExperimentType.CUSTOMER_INTERVIEW
        )

        if auto_save:
            ValidationEngineService.create_experiment(
                db=db,
                workspace_id=workspace_id,
                brain_id=brain_id,
                project_id=project_id,
                exp_in=ExperimentCreate(
                    hypothesis_id=hypothesis.id,
                    experiment_type=exp_type_enum,
                    name=parsed["name"],
                    description=parsed.get("description"),
                    smallest_useful_scope=parsed.get("smallest_useful_scope"),
                    success_threshold=parsed.get("success_threshold", hypothesis.threshold),
                    duration_days=parsed.get("duration_days", hypothesis.timeframe_days),
                    budget_amount=float(parsed.get("budget_amount", 0.0)),
                ),
            )
            hypothesis.status = "TESTING"
            db.commit()

        return RecommendedExperimentResponse(
            hypothesis_id=hypothesis.id,
            experiment_type=exp_type_enum.value,
            name=parsed["name"],
            description=parsed.get("description", ""),
            smallest_useful_scope=parsed.get("smallest_useful_scope", ""),
            success_threshold=parsed.get("success_threshold", hypothesis.threshold),
            duration_days=parsed.get("duration_days", hypothesis.timeframe_days),
            budget_amount=float(parsed.get("budget_amount", 0.0)),
        )

    @staticmethod
    def detect_solution_bias_risk(
        db: Session,
        workspace_id: int,
        project_id: int,
    ) -> Dict[str, Any]:
        """
        Nhận diện nguy cơ Solution Bias (F2.md §6, §10):
        Khi Solution detail/maturity cao nhưng Problem evidence còn thấp (ASSUMPTION/UNKNOWN).
        """
        from founder_os.validation.models import DimensionState, DimensionName, DimensionStateEnum
        from founder_os.validation.schemas import SolutionBiasRiskResponse

        problem_dim = db.scalar(
            select(DimensionState).where(
                and_(
                    DimensionState.workspace_id == workspace_id,
                    DimensionState.project_id == project_id,
                    DimensionState.dimension == DimensionName.PROBLEM.value,
                )
            )
        )
        solution_dim = db.scalar(
            select(DimensionState).where(
                and_(
                    DimensionState.workspace_id == workspace_id,
                    DimensionState.project_id == project_id,
                    DimensionState.dimension == DimensionName.SOLUTION.value,
                )
            )
        )

        prob_state = problem_dim.state if problem_dim else DimensionStateEnum.UNKNOWN.value
        sol_state = solution_dim.state if solution_dim else DimensionStateEnum.UNKNOWN.value

        bias_risk = "NONE"
        warning_title = None
        warning_msg = None

        # Logic so sánh độ lệch maturity
        sol_high = sol_state in ["SUPPORTED", "VALIDATED", "HYPOTHESIS", "TESTING"]
        prob_low = prob_state in ["UNKNOWN", "BELIEF", "ASSUMPTION"]

        if sol_high and prob_low:
            bias_risk = "HIGH"
            warning_title = "⚠ SOLUTION BIAS RISK: Giải Pháp Đi Tìm Vấn Đề"
            warning_msg = (
                "Dự án đang mô tả hoặc chuẩn bị xây dựng Solution rất chi tiết nhưng "
                f"Problem hiện vẫn ở trạng thái '{prob_state}'. "
                "Khuyến nghị: Tạm dừng mở rộng tính năng, ưu tiên phỏng vấn kiểm chứng nỗi đau khách hàng."
            )
        elif prob_low:
            bias_risk = "MEDIUM"
            warning_title = "Cảnh Báo Giả Định Vấn Đề"
            warning_msg = "Problem chưa có đủ bằng chứng thực tế từ khách hàng."

        counter_questions = [
            "Nếu trong 12 tháng tới không được phép dùng Solution hiện tại, anh/chị sẽ giải quyết cùng Problem bằng cách nào?",
            "Customer hiện đang giải quyết vấn đề này như thế nào, và tại sao họ vẫn chấp nhận cách đó?",
            "Nếu phải dành 30 ngày chỉ để nói chuyện với customer mà chưa build thêm, điều gì làm anh/chị lo ngại nhất?",
            "Nếu launch mà không ai mua, giả định nào có khả năng sai nhất?"
        ]

        return {
            "project_id": project_id,
            "solution_bias_risk": bias_risk,
            "solution_maturity": sol_state,
            "problem_evidence_maturity": prob_state,
            "warning_title": warning_title,
            "warning_message": warning_msg,
            "recommended_action": "Run Problem Validation Interview before major builds" if bias_risk == "HIGH" else "Continue discovery",
            "counter_questions": counter_questions,
            "allow_proceed_anyway": True,
        }

