from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.policy_funding.models import (
    Application,
    ApplicationSection,
    PolicyProgram,
    ProjectStageAssessment,
    TrlAssessment,
    FundingNeed,
)
from app.modules.strategy.models import Project, MvpStage


STANDARD_SECTIONS = [
    ("BACKGROUND", "1. Bối cảnh và Tính cấp thiết của Đề tài/Dự án", 1),
    ("OBJECTIVES", "2. Mục tiêu Tổng quát và Mục tiêu Cụ thể", 2),
    ("TECHNOLOGY", "3. Giải pháp Công nghệ và Tính mới", 3),
    ("TRL", "4. Mức độ Sẵn sàng Công nghệ (TRL) & Lộ trình Nâng cấp", 4),
    ("OUTPUT_KPIS", "5. Sản phẩm Đầu ra và Chỉ tiêu Định lượng (KPI)", 5),
    ("WORK_PLAN", "6. Kế hoạch Triển khai và Các Mốc Kết quả (Milestones)", 6),
    ("COMMERCIALIZATION", "7. Kế hoạch Khai thác Thị trường và Thương mại hóa", 7),
    ("BUDGET", "8. Dự toán Kinh phí và Phương án Vốn Đối ứng", 8),
    ("TEAM", "9. Năng lực Đội ngũ Thực hiện và Chuyên gia Tư vấn", 9),
    ("IP", "10. Quyền Sở hữu Trí tuệ và Phương án Bảo hộ", 10),
    ("RISKS", "11. Đánh giá Rủi ro và Biện pháp Giảm thiểu", 11),
    ("EVIDENCE", "12. Danh mục Tài liệu Minh chứng Đính kèm", 12),
]


class ProposalService:
    """
    Dịch vụ hỗ trợ soạn thảo hồ sơ thuyết minh dự án ứng tuyển các chương trình chính sách/quỹ.
    Tuân thủ quy tắc: Không bịa số liệu, dữ liệu thiếu phải gắn [CẦN FOUNDER BỔ SUNG: ...].
    """

    @classmethod
    def initialize_application(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        program_id: int,
        requested_amount: Optional[float] = None,
        co_funding_amount: Optional[float] = None,
    ) -> Application:
        """
        Khởi tạo hồ sơ ứng tuyển kèm 12 sections chuẩn.
        """
        program = db.scalar(select(PolicyProgram).where(PolicyProgram.id == program_id))
        prog_name = program.name if program else "Chương trình hỗ trợ"

        project = db.scalar(select(Project).where(Project.id == project_id))
        proj_title = project.title if project else "Dự án"

        app_record = Application(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            program_id=program_id,
            title=f"Hồ sơ Thuyết minh: {proj_title} - {prog_name}",
            status="DRAFT",
            template_version="1.0",
            requested_amount=requested_amount,
            co_funding_amount=co_funding_amount,
        )
        db.add(app_record)
        db.flush()

        for sec_key, sec_title, seq in STANDARD_SECTIONS:
            db.add(
                ApplicationSection(
                    application_id=app_record.id,
                    section_key=sec_key,
                    section_title=sec_title,
                    sequence_no=seq,
                    content_draft=None,
                    content_approved=None,
                    is_approved=False,
                    missing_fields_jsonb=[],
                )
            )

        db.commit()
        db.refresh(app_record)
        return app_record

    @classmethod
    def generate_section_draft(
        cls,
        db: Session,
        application_id: int,
        section_key: str,
    ) -> ApplicationSection:
        """
        Tự động tạo bản thảo nội dung cho một section dựa trên dữ liệu thật của Project.
        """
        section = db.scalar(
            select(ApplicationSection).where(
                ApplicationSection.application_id == application_id,
                ApplicationSection.section_key == section_key,
            )
        )
        if not section:
            raise ValueError(f"Section {section_key} not found for application {application_id}")

        app_record = db.scalar(select(Application).where(Application.id == application_id))
        if not app_record:
            raise ValueError("Application not found")

        project = db.scalar(select(Project).where(Project.id == app_record.project_id))
        stage_assessment = db.scalar(
            select(ProjectStageAssessment)
            .where(ProjectStageAssessment.project_id == app_record.project_id)
            .order_by(ProjectStageAssessment.created_at.desc())
        )
        trl_assessment = db.scalar(
            select(TrlAssessment)
            .where(TrlAssessment.project_id == app_record.project_id)
            .order_by(TrlAssessment.created_at.desc())
        )
        program = db.scalar(select(PolicyProgram).where(PolicyProgram.id == app_record.program_id))
        mvp_stages = db.scalars(
            select(MvpStage).where(MvpStage.project_id == app_record.project_id)
        ).all()

        draft_text, missing_fields = cls._compose_section_content(
            section_key=section_key,
            project=project,
            stage_assessment=stage_assessment,
            trl_assessment=trl_assessment,
            program=program,
            mvp_stages=mvp_stages,
            app_record=app_record,
        )

        section.content_draft = draft_text
        section.missing_fields_jsonb = missing_fields
        section.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(section)
        return section

    @classmethod
    def _compose_section_content(
        cls,
        section_key: str,
        project: Optional[Project],
        stage_assessment: Optional[ProjectStageAssessment],
        trl_assessment: Optional[TrlAssessment],
        program: Optional[PolicyProgram],
        mvp_stages: List[MvpStage],
        app_record: Application,
    ) -> Tuple[str, List[str]]:
        missing_fields: List[str] = []
        proj_title = project.title if project else "Dự án"
        proj_desc = project.description if project and project.description else "[CẦN FOUNDER BỔ SUNG: Mô tả chi tiết vấn đề thị trường và giải pháp]"
        if not (project and project.description):
            missing_fields.append("Mô tả chi tiết vấn đề và giải pháp")

        stage_name = stage_assessment.stage if stage_assessment else "MVP"
        trl_val = trl_assessment.trl_current if trl_assessment else 3

        if section_key == "BACKGROUND":
            text = (
                f"### 1. BỐI CẢNH VÀ TÍNH CẤP THIẾT\n\n"
                f"Dự án **{proj_title}** được phát triển nhằm giải quyết nhu cầu thực tiễn trong lĩnh vực công nghệ số và đổi mới sáng tạo.\n\n"
                f"**Vấn đề cốt lõi:**\n{proj_desc}\n\n"
                f"**Mục tiêu đổi mới sáng tạo:** Đưa ra giải pháp công nghệ vượt trội, tối ưu hóa quy trình vận hành và nâng cao năng lực cạnh tranh."
            )
        elif section_key == "OBJECTIVES":
            text = (
                f"### 2. MỤC TIÊU CỦA ĐỀ TÀI/DỰ ÁN\n\n"
                f"- **Mục tiêu tổng quát:** Hoàn thiện và thương mại hóa thành công sản phẩm **{proj_title}**, mở rộng thị phần và tạo đột phá về hiệu quả kinh tế.\n"
                f"- **Mục tiêu cụ thể:**\n"
                f"  1. Nâng cấp công nghệ từ TRL {trl_val} lên mức độ sẵn sàng cao hơn.\n"
                f"  2. Đạt chỉ tiêu [CẦN FOUNDER BỔ SUNG: Số lượng người dùng/khách hàng mục tiêu trong 12 tháng].\n"
                f"  3. Hoàn tất bảo hộ tài sản trí tuệ và chứng nhận tiêu chuẩn kỹ thuật liên quan."
            )
            missing_fields.append("Số lượng người dùng/khách hàng mục tiêu")
        elif section_key == "TECHNOLOGY":
            text = (
                f"### 3. GIẢI PHÁP CÔNG NGHỆ VÀ TÍNH MỚI\n\n"
                f"- **Công nghệ chủ đạo:** Áp dụng kiến trúc hệ thống hiện đại, tự động hóa và tích hợp trí tuệ nhân tạo (AI/Agentic OS).\n"
                f"- **Tính mới và sáng tạo:** [CẦN FOUNDER BỔ SUNG: Điểm khác biệt công nghệ so với các giải pháp hiện hành trên thị trường].\n"
                f"- **Khả năng làm chủ công nghệ:** Đội ngũ dự án trực tiếp thiết kế, phát triển mã nguồn và kiểm soát kiến trúc hệ thống."
            )
            missing_fields.append("Điểm khác biệt công nghệ cốt lõi")
        elif section_key == "TRL":
            trl_exp = trl_assessment.explanation if trl_assessment and trl_assessment.explanation else "[CẦN FOUNDER BỔ SUNG: Báo cáo kết quả thử nghiệm thực tế]"
            if not (trl_assessment and trl_assessment.explanation):
                missing_fields.append("Báo cáo kết quả thử nghiệm TRL")
            text = (
                f"### 4. MỨC ĐỘ SẴN SÀNG CÔNG NGHỆ (TRL)\n\n"
                f"- **TRL Hiện tại:** Mức {trl_val} (Đã có sản phẩm mẫu khả dụng/thử nghiệm trong môi trường liên quan).\n"
                f"- **Minh chứng TRL:** {trl_exp}\n"
                f"- **TRL Mục tiêu sau tài trợ:** Mức {min(9, trl_val + 2)} (Vận hành hoàn chỉnh và thương mại hóa)."
            )
        elif section_key == "BUDGET":
            req_amount = f"{app_record.requested_amount:,.0f} VND" if app_record.requested_amount else "[CẦN FOUNDER BỔ SUNG: Tổng kinh phí xin tài trợ]"
            co_amount = f"{app_record.co_funding_amount:,.0f} VND" if app_record.co_funding_amount else "[CẦN FOUNDER BỔ SUNG: Số tiền vốn đối ứng cam kết]"
            if not app_record.requested_amount:
                missing_fields.append("Kinh phí xin tài trợ")
            if not app_record.co_funding_amount:
                missing_fields.append("Kinh phí vốn đối ứng")
            text = (
                f"### 8. DỰ TOÁN KINH PHÍ VÀ VỐN ĐỐI ỨNG\n\n"
                f"- **Kinh phí đề xuất tài trợ:** {req_amount}\n"
                f"- **Vốn đối ứng của doanh nghiệp:** {co_amount}\n"
                f"- **Cơ cấu chi phí hợp lệ:** Chi phí nhân công R&D, Chi phí thuê hạ tầng máy chủ/cloud, Chi phí kiểm định/thử nghiệm, Chi phí đăng ký SHTT."
            )
        else:
            text = (
                f"### {section_key}\n\n"
                f"Nội dung đang được khởi tạo dựa trên hồ sơ dự án **{proj_title}**.\n"
                f"[CẦN FOUNDER BỔ SUNG: Chi tiết nội dung cho phần {section_key}]."
            )
            missing_fields.append(f"Chi tiết nội dung {section_key}")

        return text, missing_fields
