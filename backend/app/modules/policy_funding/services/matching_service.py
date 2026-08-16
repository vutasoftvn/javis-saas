from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.modules.policy_funding.models import (
    PolicyProgram,
    EligibilityRule,
    ProjectStageAssessment,
    TrlAssessment,
    FundingNeed,
    ProjectProgramMatch,
    EligibilityEvaluation,
    MissingRequirement,
    CostAllocation,
)
from app.modules.strategy.models import Project


class PolicyMatchingService:
    """
    Dịch vụ khớp nối và đánh giá điều kiện chính sách, nguồn vốn hỗ trợ cho Project.
    """

    @classmethod
    def evaluate_project_against_program(
        cls,
        db: Session,
        project_id: int,
        program: PolicyProgram,
        workspace_id: int,
        stage_assessment: Optional[ProjectStageAssessment] = None,
        trl_assessment: Optional[TrlAssessment] = None,
        funding_need: Optional[FundingNeed] = None,
    ) -> Tuple[str, float, float, List[Dict[str, Any]], List[str]]:
        """
        Đánh giá 1 Project với 1 Program.
        Trả về: (eligibility_status, match_score, readiness_score, rule_results, missing_items)
        """
        # Lấy thông tin hiện tại nếu chưa truyền vào
        if stage_assessment is None:
            stage_assessment = db.scalar(
                select(ProjectStageAssessment)
                .where(
                    ProjectStageAssessment.project_id == project_id,
                    ProjectStageAssessment.workspace_id == workspace_id,
                )
                .order_by(ProjectStageAssessment.created_at.desc())
            )
        
        if trl_assessment is None:
            trl_assessment = db.scalar(
                select(TrlAssessment)
                .where(
                    TrlAssessment.project_id == project_id,
                    TrlAssessment.workspace_id == workspace_id,
                )
                .order_by(TrlAssessment.created_at.desc())
            )

        if funding_need is None:
            funding_need = db.scalar(
                select(FundingNeed)
                .where(
                    FundingNeed.project_id == project_id,
                    FundingNeed.workspace_id == workspace_id,
                )
                .order_by(FundingNeed.created_at.desc())
            )

        company_type = stage_assessment.company_type if stage_assessment else "STARTUP"
        current_stage = stage_assessment.stage if stage_assessment else "MVP"
        current_trl = trl_assessment.trl_current if trl_assessment else 3
        has_trl_evidence = bool(trl_assessment and trl_assessment.evidence_artifact_id)
        has_co_funding = bool(funding_need and funding_need.co_funding_confirmed)

        hard_fail = False
        rule_results: List[Dict[str, Any]] = []
        missing_items: List[str] = []

        # 1. HARD FILTER: Trạng thái chính sách & Draft Watchlist
        v_status = getattr(program, "verification_status", None)
        pub_matching = getattr(program, "publish_to_matching", None)

        if pub_matching is False or v_status == "DRAFT_WATCHLIST":
            return (
                "NEEDS_VERIFICATION",
                0.0,
                0.0,
                [{"rule": "Draft Watchlist", "status": v_status or "UNPUBLISHED", "note": "Chương trình thuộc danh sách dự thảo theo dõi hoặc chưa công bố matching."}],
                []
            )

        if program.status == "DRAFT":
            # DRAFT không được coi là quyền lợi có hiệu lực
            return (
                "NEEDS_VERIFICATION",
                50.0,
                30.0,
                [{"rule": "Policy Status", "status": "DRAFT", "note": "Chương trình còn là Dự thảo, chưa mở nhận hồ sơ chính thức."}],
                ["Chờ văn bản ban hành chính thức"]
            )
        
        if program.status in ["CLOSED", "EXPIRED", "SUSPENDED", "REJECTED_SOURCE_DATA", "VERIFIED_CLOSED"]:
            return (
                "INELIGIBLE",
                0.0,
                0.0,
                [{"rule": "Program Closed", "status": program.status, "note": "Chương trình hiện đã đóng hoặc hết hiệu lực."}],
                []
            )

        # 2. HARD FILTER: TRL tối thiểu
        if program.trl_min and current_trl < program.trl_min:
            hard_fail = True
            rule_results.append({
                "rule": "TRL tối thiểu",
                "required": f"TRL ≥ {program.trl_min}",
                "actual": f"TRL {current_trl}",
                "passed": False,
                "note": f"Mức độ sẵn sàng công nghệ hiện tại (TRL {current_trl}) chưa đạt ngưỡng tối thiểu ({program.trl_min}) của chương trình."
            })
            missing_items.append(f"Nâng cấp công nghệ và thử nghiệm để đạt TRL ≥ {program.trl_min}")
        elif program.trl_min:
            rule_results.append({
                "rule": "TRL tối thiểu",
                "required": f"TRL ≥ {program.trl_min}",
                "actual": f"TRL {current_trl}",
                "passed": True,
                "note": f"Đạt yêu cầu mức độ công nghệ (TRL {current_trl} ≥ {program.trl_min})."
            })

        # 3. HARD FILTER: Đối tượng doanh nghiệp (Company Types)
        target_company_types = program.company_types if isinstance(program.company_types, list) else []
        if target_company_types and company_type not in target_company_types:
            hard_fail = True
            rule_results.append({
                "rule": "Đối tượng doanh nghiệp",
                "required": target_company_types,
                "actual": company_type,
                "passed": False,
                "note": f"Loại hình doanh nghiệp ({company_type}) không nằm trong danh mục hỗ trợ của chương trình."
            })
            missing_items.append(f"Cần chuyển đổi hoặc đăng ký đúng loại hình: {', '.join(target_company_types)}")
        elif target_company_types:
            rule_results.append({
                "rule": "Đối tượng doanh nghiệp",
                "required": target_company_types,
                "actual": company_type,
                "passed": True,
                "note": f"Phù hợp loại hình doanh nghiệp ({company_type})."
            })

        # 4. SOFT MATCH SCORE CALCULATION (0..100)
        raw_match_score = 0.0
        # Company type match (+25)
        if not target_company_types or company_type in target_company_types:
            raw_match_score += 25.0
        
        # Stage match (+25)
        target_stages = program.project_stages if isinstance(program.project_stages, list) else []
        if not target_stages or current_stage in target_stages:
            raw_match_score += 25.0
            rule_results.append({
                "rule": "Giai đoạn phát triển",
                "required": target_stages,
                "actual": current_stage,
                "passed": True,
                "note": f"Giai đoạn ({current_stage}) phù hợp với chương trình."
            })
        else:
            rule_results.append({
                "rule": "Giai đoạn phát triển",
                "required": target_stages,
                "actual": current_stage,
                "passed": False,
                "note": f"Giai đoạn ({current_stage}) khác mục tiêu ưu tiên ({target_stages})."
            })
            raw_match_score += 10.0

        # TRL Level (+25)
        if not program.trl_min or current_trl >= program.trl_min:
            raw_match_score += 25.0
        else:
            raw_match_score += max(0.0, (current_trl / (program.trl_min or 1)) * 15.0)

        # Funding structure alignment (+25)
        raw_match_score += 25.0

        # Apply Verification Multiplier (1.0 vs 0.9 vs 0.6)
        v_status = getattr(program, "verification_status", None)
        if v_status is None:
            v_status = "VERIFIED_ACTIVE" if program.status == "ACTIVE" else "PENDING_FOUNDER_VERIFICATION"

        if v_status == "VERIFIED_ACTIVE":
            verification_multiplier = 1.0
        elif v_status == "VERIFIED_ENACTED":
            verification_multiplier = 0.9
        elif v_status in ["SOURCE_CLAIMED_CURRENT", "PENDING_FOUNDER_VERIFICATION"]:
            verification_multiplier = 0.6
            missing_items.append("Kiểm chứng dữ liệu nguồn với văn bản/cổng chính thức")
        else:
            verification_multiplier = 0.5

        final_match_score = raw_match_score * verification_multiplier

        # 5. READINESS SCORE CALCULATION (0..100)
        readiness_score = 30.0  # Base profile đã có

        if has_trl_evidence:
            readiness_score += 25.0
        else:
            missing_items.append("Bổ sung báo cáo thử nghiệm/minh chứng công nghệ (Evidence)")

        if program.matching_fund_pct and program.matching_fund_pct > 0:
            if has_co_funding:
                readiness_score += 25.0
            else:
                missing_items.append(f"Xác nhận số dư hoặc cam kết vốn đối ứng tối thiểu {program.matching_fund_pct}%")
        else:
            readiness_score += 25.0

        if stage_assessment and stage_assessment.is_founder_confirmed:
            readiness_score += 20.0
        else:
            missing_items.append("Founder xác nhận phân loại doanh nghiệp và giai đoạn dự án")

        # 6. OVERALL ELIGIBILITY STATUS
        if hard_fail:
            eligibility_status = "INELIGIBLE"
        elif v_status in ["SOURCE_CLAIMED_CURRENT", "PENDING_FOUNDER_VERIFICATION"]:
            eligibility_status = "POTENTIALLY_ELIGIBLE"
        elif readiness_score < 50.0 or len(missing_items) > 2:
            eligibility_status = "POTENTIALLY_ELIGIBLE"
        else:
            eligibility_status = "ELIGIBLE"

        return (
            eligibility_status,
            round(min(100.0, final_match_score), 1),
            round(min(100.0, readiness_score), 1),
            rule_results,
            missing_items,
        )

    @classmethod
    def run_full_matching_for_project(
        cls,
        db: Session,
        project_id: int,
        workspace_id: int,
        brain_id: int,
    ) -> List[ProjectProgramMatch]:
        """
        Chạy matching cho toàn bộ chương trình hợp lệ trong catalog.
        """
        programs = db.scalars(
            select(PolicyProgram)
            .where(
                PolicyProgram.workspace_id == workspace_id,
                PolicyProgram.publish_to_matching == True,
                PolicyProgram.verification_status != "DRAFT_WATCHLIST",
            )
        ).all()

        stage_assessment = db.scalar(
            select(ProjectStageAssessment)
            .where(
                ProjectStageAssessment.project_id == project_id,
                ProjectStageAssessment.workspace_id == workspace_id,
            )
            .order_by(ProjectStageAssessment.created_at.desc())
        )

        trl_assessment = db.scalar(
            select(TrlAssessment)
            .where(
                TrlAssessment.project_id == project_id,
                TrlAssessment.workspace_id == workspace_id,
            )
            .order_by(TrlAssessment.created_at.desc())
        )

        funding_need = db.scalar(
            select(FundingNeed)
            .where(
                FundingNeed.project_id == project_id,
                FundingNeed.workspace_id == workspace_id,
            )
            .order_by(FundingNeed.created_at.desc())
        )

        matches: List[ProjectProgramMatch] = []

        for program in programs:
            status, match_sc, read_sc, rules, missing = cls.evaluate_project_against_program(
                db=db,
                project_id=project_id,
                program=program,
                workspace_id=workspace_id,
                stage_assessment=stage_assessment,
                trl_assessment=trl_assessment,
                funding_need=funding_need,
            )

            # Tìm hoặc tạo match record
            existing_match = db.scalar(
                select(ProjectProgramMatch)
                .where(
                    ProjectProgramMatch.project_id == project_id,
                    ProjectProgramMatch.program_id == program.id,
                )
            )

            summary_text = (
                f"Đánh giá: {status}. Điểm phù hợp: {match_sc}/100, Điểm sẵn sàng: {read_sc}/100. "
                f"Đã đạt {sum(1 for r in rules if r.get('passed'))}/{len(rules)} tiêu chí."
            )

            if existing_match:
                existing_match.eligibility_status = status
                existing_match.match_score = match_sc
                existing_match.readiness_score = read_sc
                existing_match.passed_rules_count = sum(1 for r in rules if r.get("passed"))
                existing_match.total_rules_count = len(rules)
                existing_match.ai_summary = summary_text
                existing_match.calculated_at = datetime.utcnow()
                match_record = existing_match
            else:
                match_record = ProjectProgramMatch(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    program_id=program.id,
                    eligibility_status=status,
                    match_score=match_sc,
                    readiness_score=read_sc,
                    pipeline_stage="MATCHED",
                    passed_rules_count=sum(1 for r in rules if r.get("passed")),
                    total_rules_count=len(rules),
                    ai_summary=summary_text,
                    calculated_at=datetime.utcnow(),
                )
                db.add(match_record)

            # Cập nhật Missing Requirements
            for item in missing:
                existing_req = db.scalar(
                    select(MissingRequirement)
                    .where(
                        MissingRequirement.project_id == project_id,
                        MissingRequirement.program_id == program.id,
                        MissingRequirement.title == item,
                    )
                )
                if not existing_req:
                    db.add(
                        MissingRequirement(
                            workspace_id=workspace_id,
                            project_id=project_id,
                            program_id=program.id,
                            category="EVIDENCE",
                            title=item,
                            description=f"Yêu cầu hoàn thiện cho chương trình {program.name}",
                            is_resolved=False,
                        )
                    )

            matches.append(match_record)

        db.commit()
        return matches

    @classmethod
    def recalculate_program_matches(cls, db: Session, program_id: int) -> int:
        """
        Tính toán lại Match Score và Eligibility cho tất cả các Project liên quan khi một Program được Founder kiểm chứng hoặc cập nhật.
        """
        program = db.scalar(select(PolicyProgram).where(PolicyProgram.id == program_id))
        if not program:
            return 0

        # Lấy danh sách project matches hiện tại đối với program này
        matches = db.scalars(
            select(ProjectProgramMatch).where(ProjectProgramMatch.program_id == program_id)
        ).all()

        updated_count = 0
        for m in matches:
            stage_assessment = db.scalar(
                select(ProjectStageAssessment)
                .where(
                    ProjectStageAssessment.project_id == m.project_id,
                    ProjectStageAssessment.workspace_id == m.workspace_id,
                )
                .order_by(ProjectStageAssessment.created_at.desc())
            )
            trl_assessment = db.scalar(
                select(TrlAssessment)
                .where(
                    TrlAssessment.project_id == m.project_id,
                    TrlAssessment.workspace_id == m.workspace_id,
                )
                .order_by(TrlAssessment.created_at.desc())
            )
            funding_need = db.scalar(
                select(FundingNeed)
                .where(
                    FundingNeed.project_id == m.project_id,
                    FundingNeed.workspace_id == m.workspace_id,
                )
                .order_by(FundingNeed.created_at.desc())
            )

            status, match_sc, read_sc, rules, missing = cls.evaluate_project_against_program(
                db=db,
                project_id=m.project_id,
                program=program,
                workspace_id=m.workspace_id,
                stage_assessment=stage_assessment,
                trl_assessment=trl_assessment,
                funding_need=funding_need,
            )

            summary_text = (
                f"Đánh giá: {status}. Điểm phù hợp: {match_sc}/100, Điểm sẵn sàng: {read_sc}/100. "
                f"Đã đạt {sum(1 for r in rules if r.get('passed'))}/{len(rules)} tiêu chí."
            )

            m.eligibility_status = status
            m.match_score = match_sc
            m.readiness_score = read_sc
            m.passed_rules_count = sum(1 for r in rules if r.get("passed"))
            m.total_rules_count = len(rules)
            m.ai_summary = summary_text
            m.calculated_at = datetime.utcnow()
            updated_count += 1

        db.commit()
        return updated_count

    @classmethod
    def check_double_funding(
        cls,
        db: Session,
        project_id: int,
        work_package: str,
        cost_category: str,
        purpose: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Tuple[bool, str, List[int], List[int]]:
        """
        Kiểm tra xung đột chi phí / hạng mục giữa nhiều nguồn tài trợ (Double Funding Guard).
        """
        query = select(CostAllocation).where(
            CostAllocation.project_id == project_id,
            CostAllocation.cost_category == cost_category,
        )

        allocations = db.scalars(query).all()
        conflicting_award_ids: List[int] = []
        conflicting_app_ids: List[int] = []

        wp_clean = work_package.lower().strip()
        purpose_clean = purpose.lower().strip()

        for alloc in allocations:
            alloc_wp = alloc.work_package.lower().strip()
            alloc_purpose = alloc.purpose.lower().strip()

            # Trùng work package hoặc purpose tương đồng
            if wp_clean == alloc_wp or purpose_clean == alloc_purpose:
                # Kiểm tra trùng kỳ hạn nếu có
                if alloc.award_id:
                    conflicting_award_ids.append(alloc.award_id)
                if alloc.application_id:
                    conflicting_app_ids.append(alloc.application_id)

        if conflicting_award_ids or conflicting_app_ids:
            msg = (
                f"CẢNH BÁO TRÙNG NGUỒN HỖ TRỢ (Double Funding): Hạng mục '{work_package}' "
                f"thuộc nhóm chi phí '{cost_category}' đã được phân bổ trong các khoản tài trợ hoặc hồ sơ khác."
            )
            return True, msg, list(set(conflicting_award_ids)), list(set(conflicting_app_ids))

        return False, "Không phát hiện trùng lặp chi phí.", [], []


MatchingService = PolicyMatchingService

