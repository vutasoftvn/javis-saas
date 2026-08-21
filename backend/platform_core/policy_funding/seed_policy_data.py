from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from platform_core.policy_funding.models import (
    SourceDocument,
    SourceSnapshot,
    PolicyProgram,
    PolicyProgramClaim,
    EligibilityRule,
)


def seed_meetup_policy_data(db: Session, workspace_id: int, brain_id: int):
    """
    Nạp dữ liệu chính sách và nguồn lực ban đầu từ tài liệu Founders' Meetup #1:
    - 23 seed records từ 6 nhóm quyền lợi
    - 5 chương trình quốc gia dự thảo 2026-2035 (DRAFT_WATCHLIST)
    - Tách biệt claims theo Claim-based architecture
    - Mặc định trạng thái PENDING_FOUNDER_VERIFICATION, source_type PRESENTATION
    """
    # 1. Source Document: Tài liệu Founders' Meetup #1
    meetup_source = db.scalar(
        select(SourceDocument).where(
            SourceDocument.workspace_id == workspace_id,
            SourceDocument.title == "Next Wave of Startups 2026 — Founders’ Meetup #1",
        )
    )
    if not meetup_source:
        meetup_source = SourceDocument(
            workspace_id=workspace_id,
            brain_id=brain_id,
            title="Next Wave of Startups 2026 — Founders’ Meetup #1",
            authority="Trung tâm ĐMST Quốc gia (NIC) / Bộ KH&CN / Chuyên gia Meetup",
            document_type="PRESENTATION",
            verification_status="PENDING_FOUNDER_VERIFICATION",
            verification_note="Tài liệu slide hội thảo ban đầu; chưa xác minh độc lập với cổng thông tin pháp luật chính thức.",
            issued_at=datetime(2026, 7, 15),
        )
        db.add(meetup_source)
        db.flush()

    def _ensure_program(
        code: str,
        name: str,
        summary: str,
        program_type: str,
        authority: str,
        geography: str,
        company_types: List[str],
        project_stages: List[str],
        trl_min: Optional[int],
        funding_min: Optional[float],
        funding_max: Optional[float],
        matching_fund_pct: float,
        eligible_costs: List[str],
        status: str,
        verification_status: str,
        publish_to_matching: bool,
        source_claim: str,
        legal_basis: Optional[str] = None,
        claimed_values: Optional[Dict[str, Any]] = None,
        claims: Optional[List[Dict[str, Any]]] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
    ) -> PolicyProgram:
        p = db.scalar(
            select(PolicyProgram).where(
                PolicyProgram.workspace_id == workspace_id,
                PolicyProgram.code == code,
            )
        )
        if not p:
            p = PolicyProgram(
                workspace_id=workspace_id,
                brain_id=brain_id,
                name=name,
                code=code,
                summary=summary,
                program_type=program_type,
                legal_basis=legal_basis,
                authority=authority,
                geography=geography,
                company_types=company_types,
                project_stages=project_stages,
                trl_min=trl_min,
                industries=["AI", "SAAS", "BIOTECH", "GREENTECH", "HARDWARE", "ALL"],
                funding_min=funding_min,
                funding_max=funding_max,
                currency="VND",
                matching_fund_pct=matching_fund_pct,
                eligible_costs=eligible_costs,
                status=status,
                verification_status=verification_status,
                matching_mode="soft",
                publish_to_matching=publish_to_matching,
                source_claim=source_claim,
                claimed_values_jsonb=claimed_values or {},
                source_document_id=meetup_source.id,
                last_verified_at=datetime.utcnow(),
            )
            db.add(p)
            db.flush()

            if claims:
                for c in claims:
                    db.add(
                        PolicyProgramClaim(
                            program_id=p.id,
                            claim_type=c.get("claim_type", "SUPPORT_AMOUNT"),
                            claim_key=c.get("claim_key", "general"),
                            claim_value=c.get("claim_value", ""),
                            source_document_id=meetup_source.id,
                            source_page=c.get("source_page"),
                            source_excerpt=c.get("source_excerpt"),
                            is_verified=False,
                        )
                    )

            if rules:
                for r in rules:
                    db.add(
                        EligibilityRule(
                            program_id=p.id,
                            rule_type=r.get("rule_type", "HARD"),
                            category=r.get("category", "LEGAL"),
                            title=r.get("title", ""),
                            description=r.get("description"),
                            field_path=r.get("field_path"),
                            operator=r.get("operator"),
                            expected_value_jsonb=r.get("expected_value_jsonb", {}),
                            legal_reference=r.get("legal_reference"),
                            weight=r.get("weight", 1.0),
                            source_document_id=meetup_source.id,
                        )
                    )
        return p

    # -------------------------------------------------------------
    # P0: CÁC CHƯƠNG TRÌNH ƯU TIÊN CAO NHẤT
    # -------------------------------------------------------------

    # Seed 02: NATIF Tài trợ & đặt hàng ĐMST
    _ensure_program(
        code="NATIF-INNOVATION-GRANT",
        name="NATIF — Tài trợ & đặt hàng nhiệm vụ đổi mới sáng tạo",
        summary="Tài trợ và đặt hàng 5 nhóm nhiệm vụ: Đổi mới công nghệ, ĐMST, Phát triển SHTT, Nâng cao năng suất chất lượng, Hỗ trợ khởi nghiệp sáng tạo.",
        program_type="GRANT",
        authority="Quỹ Đổi mới công nghệ Quốc gia (NATIF)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=3,
        funding_min=500000000.0,
        funding_max=5000000000.0,
        matching_fund_pct=30.0,
        eligible_costs=["RD_SALARY", "EQUIPMENT", "TESTING", "IP_REGISTRATION"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Thời hạn hợp đồng <= 60 tháng, cơ chế khoán chi đến sản phẩm cuối cùng, cần pháp nhân & phương án đối ứng.",
        claimed_values={"max_contract_months": 60, "requires_legal_entity": True, "requires_financial_plan": True},
        claims=[
            {"claim_type": "DURATION", "claim_key": "max_contract_months", "claim_value": "Thời hạn hợp đồng <= 60 tháng"},
            {"claim_type": "FINANCIAL", "claim_key": "disbursement_mode", "claim_value": "Khoán chi đến sản phẩm cuối cùng"},
            {"claim_type": "ELIGIBILITY", "claim_key": "company_eligibility", "claim_value": "Có pháp nhân, năng lực triển khai và vốn đối ứng có minh chứng"},
        ],
        rules=[
            {"rule_type": "HARD", "category": "LEGAL", "title": "Doanh nghiệp có tư cách pháp nhân hợp lệ", "field_path": "company.has_legal_entity", "operator": "EQ", "expected_value_jsonb": {"value": True}},
            {"rule_type": "HARD", "category": "TECH_TRL", "title": "TRL tối thiểu 3 (PoC / Thử nghiệm khả thi)", "field_path": "project.trl", "operator": "GTE", "expected_value_jsonb": {"value": 3}},
        ],
    )

    # Seed 03: NATIF Hỗ trợ lãi suất vay đổi mới công nghệ
    _ensure_program(
        code="NATIF-INTEREST-SUBSIDY",
        name="NATIF — Hỗ trợ lãi suất vay đổi mới công nghệ",
        summary="NATIF chi trả 50% lãi suất vay thực tế (trần 6%/năm) tối đa 5 năm (60 tháng) cho các khoản vay thương mại phục vụ đổi mới công nghệ.",
        program_type="INTEREST_SUBSIDY",
        authority="Quỹ Đổi mới công nghệ Quốc gia (NATIF)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME", "DIGITAL_SME"],
        project_stages=["MVP", "MARKET_VALIDATION", "ACCELERATION", "GROWTH", "SCALE_UP"],
        trl_min=5,
        funding_min=100000000.0,
        funding_max=1500000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["INTEREST_SUBSIDY", "LOAN_REFINANCING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Hỗ trợ 50% lãi vay thực tế, trần 6%/năm, thời hạn tối đa 60 tháng, xét duyệt <= 30 ngày, khoản vay còn hạn >= 12 tháng.",
        claimed_values={"support_ratio": 0.5, "rate_cap": "6%/năm", "max_duration_months": 60, "review_days": 30, "min_remaining_loan_months": 12},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "support_ratio", "claim_value": "50% lãi suất vay thực tế"},
            {"claim_type": "RATE_CAP", "claim_key": "rate_cap", "claim_value": "Mức trần hỗ trợ 6%/năm"},
            {"claim_type": "DURATION", "claim_key": "max_duration", "claim_value": "Thời hạn hỗ trợ tối đa 5 năm / 60 tháng"},
            {"claim_type": "PROCESS", "claim_key": "review_time", "claim_value": "Thời hạn xét duyệt hồ sơ <= 30 ngày"},
            {"claim_type": "ELIGIBILITY", "claim_key": "loan_term", "claim_value": "Khoản vay còn thời hạn >= 12 tháng tại ngân hàng thương mại"},
        ],
        rules=[
            {"rule_type": "HARD", "category": "FINANCIAL", "title": "Có khoản vay hợp lệ tại ngân hàng thương mại", "field_path": "project.has_commercial_loan", "operator": "EQ", "expected_value_jsonb": {"value": True}},
        ],
    )

    # Seed 04: NATIF Voucher — Phiếu hỗ trợ tài chính cho SP/DV mới
    _ensure_program(
        code="NATIF-INNOVATION-VOUCHER",
        name="NATIF Voucher — Phiếu hỗ trợ tài chính cho sản phẩm/dịch vụ mới",
        summary="Thúc đẩy thương mại hóa bằng cách phát hành voucher số hóa cho khách hàng/người dùng trải nghiệm sản phẩm ĐMST của startup.",
        program_type="VOUCHER",
        authority="Quỹ Đổi mới công nghệ Quốc gia (NATIF)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=6,
        funding_min=50000000.0,
        funding_max=300000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["MARKETING_PILOT", "CUSTOMER_VOUCHER", "TESTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Tối đa 3 loại SP/DV mới mỗi năm, voucher hiệu lực <= 12 tháng, NATIF hoàn trả phần giảm trừ cho DN.",
        claimed_values={"max_products_per_year": 3, "voucher_validity_months": 12},
        claims=[
            {"claim_type": "LIMIT", "claim_key": "max_products_per_year", "claim_value": "Tối đa 3 loại sản phẩm/dịch vụ mới trong 1 năm tài chính"},
            {"claim_type": "DURATION", "claim_key": "validity_months", "claim_value": "Voucher có hiệu lực <= 12 tháng"},
            {"claim_type": "REIMBURSEMENT", "claim_key": "payout_flow", "claim_value": "Phát hành số hóa, khách hàng mua giảm giá, NATIF hoàn tiền cho DN"},
        ],
        rules=[
            {"rule_type": "HARD", "category": "TECH_TRL", "title": "Sản phẩm đạt mức sẵn sàng thử nghiệm thị trường (TRL >= 6)", "field_path": "project.trl", "operator": "GTE", "expected_value_jsonb": {"value": 6}},
        ],
    )

    # Seed 17: TP.HCM NQ 20/2023 — Hỗ trợ 3 giai đoạn (Tiền ươm tạo, Ươm tạo, Tăng tốc)
    _ensure_program(
        code="HCMC-NQ20-STAGE-SUPPORT",
        name="TP.HCM — Gói hỗ trợ khởi nghiệp sáng tạo theo giai đoạn (NQ 20/2023)",
        summary="Gói hỗ trợ tài chính không hoàn lại cho dự án ĐMST tại TP.HCM: Tiền ươm tạo (40M, 6 tháng), Ươm tạo (80M, 12 tháng), Tăng tốc (400M, 12 tháng).",
        program_type="LOCAL_STARTUP_SUPPORT",
        authority="Sở KH&CN TP.HCM / HĐND TP.HCM",
        geography="LOCAL_HCM",
        company_types=["STARTUP", "SPIN_OFF", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["IDEA", "POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=2,
        funding_min=40000000.0,
        funding_max=400000000.0,
        matching_fund_pct=20.0,
        eligible_costs=["RD_SALARY", "EQUIPMENT", "TESTING", "EXPERT_ADVISORY", "MARKETING_PILOT"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Căn cứ NQ 20/2023/NQ-HĐND, áp dụng 9 lĩnh vực ưu tiên, mức 40M - 80M - 400M tùy giai đoạn.",
        legal_basis="Nghị quyết 20/2023/NQ-HĐND TP.HCM",
        claimed_values={"pre_incubation_vnd": 40000000, "incubation_vnd": 80000000, "acceleration_vnd": 400000000},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "pre_incubation", "claim_value": "Tiền ươm tạo: 40 triệu đồng (<= 6 tháng)"},
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "incubation", "claim_value": "Ươm tạo: 80 triệu đồng (<= 12 tháng)"},
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "acceleration", "claim_value": "Tăng tốc: 400 triệu đồng (<= 12 tháng, ưu tiên có đối ứng)"},
        ],
        rules=[
            {"rule_type": "HARD", "category": "LEGAL", "title": "Hoạt động hoặc đăng ký pháp nhân tại TP.HCM", "field_path": "project.geography", "operator": "IN", "expected_value_jsonb": {"value": ["LOCAL_HCM", "TP.HCM"]}},
        ],
    )

    # Seed 18: TP.HCM NQ 23/2026 — Hỗ trợ KNS sáng tạo công nghiệp công nghệ số
    _ensure_program(
        code="HCMC-NQ23-2026-DIGITAL-TECH",
        name="TP.HCM — Hỗ trợ khởi nghiệp sáng tạo công nghiệp công nghệ số (NQ 23/2026)",
        summary="Hỗ trợ 50% chi phí cho dự án công nghệ số tại TP.HCM: Đào tạo (100M), Chuyên gia (100M), R&D/Pilot (150M), Tư vấn (50M), Mua/Đổi mới công nghệ (400M).",
        program_type="LOCAL_DIGITAL_INNOVATION_SUPPORT",
        authority="Sở Thông tin và Truyền thông TP.HCM / HĐND TP.HCM",
        geography="LOCAL_HCM",
        company_types=["STARTUP", "DIGITAL_SME", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=3,
        funding_min=50000000.0,
        funding_max=400000000.0,
        matching_fund_pct=50.0,
        eligible_costs=["TRAINING", "EXPERT_ADVISORY", "RD_SALARY", "CONSULTING", "EQUIPMENT"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Căn cứ NQ 23/2026/NQ-HĐND có hiệu lực từ 01/7/2026, hỗ trợ 50% chi phí theo các nhóm trần cụ thể.",
        legal_basis="Nghị quyết 23/2026/NQ-HĐND TP.HCM",
        claimed_values={"support_ratio": 0.5, "effective_date": "2026-07-01", "training_vnd": 100000000, "expert_vnd": 100000000, "rnd_pilot_vnd": 150000000, "consulting_vnd": 50000000, "tech_purchase_vnd": 400000000},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "support_ratio", "claim_value": "Hỗ trợ 50% chi phí thực tế"},
            {"claim_type": "CAP", "claim_key": "training_cap", "claim_value": "Đào tạo: tối đa 100 triệu đồng"},
            {"claim_type": "CAP", "claim_key": "expert_cap", "claim_value": "Chuyên gia: tối đa 100 triệu đồng"},
            {"claim_type": "CAP", "claim_key": "rnd_pilot_cap", "claim_value": "R&D / Sản xuất thử: tối đa 150 triệu đồng"},
            {"claim_type": "CAP", "claim_key": "consulting_cap", "claim_value": "Tư vấn: tối đa 50 triệu đồng"},
            {"claim_type": "CAP", "claim_key": "tech_purchase_cap", "claim_value": "Mua & đổi mới công nghệ: tối đa 400 triệu đồng/dự án"},
        ],
        rules=[
            {"rule_type": "HARD", "category": "LEGAL", "title": "Dự án thuộc lĩnh vực công nghệ số / phần mềm tại TP.HCM", "field_path": "project.industry", "operator": "IN", "expected_value_jsonb": {"value": ["AI", "SAAS", "DIGITAL_TECH"]}},
        ],
    )

    # Seed 21: AWS Activate Founders ($1,000 USD Cloud Credit)
    _ensure_program(
        code="AWS-ACTIVATE-FOUNDERS",
        name="AWS Activate Founders — Cloud Credit cho startup",
        summary="Gói hỗ trợ tín dụng dịch vụ hạ tầng đám mây AWS trị giá 1,000 USD dành cho startup tự cấp vốn (bootstrapped/self-funded).",
        program_type="CLOUD_CREDIT",
        authority="Amazon Web Services (AWS)",
        geography="GLOBAL",
        company_types=["STARTUP", "DIGITAL_SME"],
        project_stages=["IDEA", "POC", "PROTOTYPE", "MVP"],
        trl_min=1,
        funding_min=25000000.0,
        funding_max=25000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["CLOUD_HOSTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: 1.000 USD AWS credits cho startup bootstrapped, chưa cần qua Activate Provider.",
        claimed_values={"claimed_value_usd": 1000, "support_mode": "NON_CASH"},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "credit_usd", "claim_value": "1.000 USD AWS cloud credits (phi tiền mặt)"},
            {"claim_type": "TARGET", "claim_key": "funding_stage", "claim_value": "Dành cho startup self-funded / bootstrapped"},
        ],
    )

    # Seed 22: AWS Activate Portfolio ($100,000 USD Cloud Credit)
    _ensure_program(
        code="AWS-ACTIVATE-PORTFOLIO",
        name="AWS Activate Portfolio — Cloud Credit cho startup thuộc vườn ươm/quỹ",
        summary="Gói tín dụng hạ tầng đám mây lên đến 100,000 USD cho startup thuộc mạng lưới đối tác Activate Provider (Venture Capital, Incubator, Accelerator).",
        program_type="CLOUD_CREDIT",
        authority="Amazon Web Services (AWS)",
        geography="GLOBAL",
        company_types=["STARTUP", "DIGITAL_SME", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["MVP", "MARKET_VALIDATION", "ACCELERATION", "SCALE_UP"],
        trl_min=4,
        funding_min=250000000.0,
        funding_max=2500000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["CLOUD_HOSTING", "TESTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Tối đa 100.000 USD AWS credits cho startup trong mạng lưới đối tác đến vòng Series A.",
        claimed_values={"claimed_value_max_usd": 100000, "support_mode": "NON_CASH"},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "credit_max_usd", "claim_value": "Tối đa 100.000 USD AWS credits (phi tiền mặt)"},
            {"claim_type": "ELIGIBILITY", "claim_key": "provider_affiliation", "claim_value": "Phải có mã định danh Org ID từ VC / Vườn ươm đối tác"},
        ],
    )

    # -------------------------------------------------------------
    # P1: CÁC CHƯƠNG TRÌNH HỖ TRỢ R&D, DỊCH VỤ, HẠ TẦNG
    # -------------------------------------------------------------

    # Seed 01: NAFOSTED Nghiên cứu ứng dụng
    _ensure_program(
        code="NAFOSTED-APPLIED-RD",
        name="NAFOSTED — Tài trợ nghiên cứu ứng dụng",
        summary="Tài trợ nghiên cứu ứng dụng cho doanh nghiệp KH&CN và viện trường, mức trần 8 tỷ đồng/nhiệm vụ qua hệ thống số hóa STM.",
        program_type="GRANT",
        authority="Quỹ Phát triển Khoa học và Công nghệ Quốc gia (NAFOSTED)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["POC", "PROTOTYPE", "MVP", "RND"],
        trl_min=3,
        funding_min=1000000000.0,
        funding_max=8000000000.0,
        matching_fund_pct=20.0,
        eligible_costs=["RD_SALARY", "EQUIPMENT", "TESTING", "IP_REGISTRATION"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Trần 8 tỷ đồng/nhiệm vụ, khuyến khích >= 20% vốn đối ứng ngoài ngân sách, nộp qua hệ thống STM.",
        claimed_values={"funding_max_vnd": 8000000000, "matching_fund_claimed": "Khuyến khích >= 20%"},
        claims=[
            {"claim_type": "SUPPORT_AMOUNT", "claim_key": "funding_cap", "claim_value": "Mức trần 8 tỷ đồng / nhiệm vụ"},
            {"claim_type": "MATCHING_FUND", "claim_key": "matching_ratio", "claim_value": "Khuyến khích >= 20% vốn đối ứng ngoài ngân sách"},
            {"claim_type": "APPLICATION_CHANNEL", "claim_key": "channel", "claim_value": "Số hóa qua hệ thống STM NAFOSTED"},
        ],
    )

    # Seed 05: Phiếu hỗ trợ ĐMST — Dịch vụ thử nghiệm/kiểm định/tư vấn
    _ensure_program(
        code="INNOVATION-SERVICE-VOUCHER",
        name="Phiếu hỗ trợ đổi mới sáng tạo — Dịch vụ thử nghiệm/kiểm định/tư vấn",
        summary="Voucher chi trả dịch vụ thử nghiệm, kiểm định chất lượng, tư vấn pháp lý/công nghệ và tiếp cận thị trường.",
        program_type="SERVICE_VOUCHER",
        authority="Bộ KH&CN / NIC / Sở KH&CN địa phương",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION"],
        trl_min=3,
        funding_min=30000000.0,
        funding_max=150000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["TESTING", "IP_REGISTRATION", "CONSULTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Chi trả trực tiếp cho đơn vị cung cấp dịch vụ thử nghiệm/kiểm định được chỉ định.",
        claims=[
            {"claim_type": "ELIGIBLE_COSTS", "claim_key": "services", "claim_value": "Thử nghiệm, kiểm định chất lượng, tư vấn chuyên sâu, tiếp cận thị trường"},
        ],
    )

    # Seed 06: Hỗ trợ chuyên gia & tư vấn
    _ensure_program(
        code="EXPERT-CONSULTING-SUPPORT",
        name="Hỗ trợ chuyên gia & tư vấn chuyên sâu",
        summary="Hỗ trợ kinh phí thuê chuyên gia trong nước và quốc tế về công nghệ, pháp lý, tài chính, quản trị và kết nối đầu tư.",
        program_type="EXPERT_SUPPORT",
        authority="Bộ KH&CN / Trung tâm ĐMST Quốc gia (NIC)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["POC", "MVP", "ACCELERATION"],
        trl_min=3,
        funding_min=20000000.0,
        funding_max=100000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["EXPERT_ADVISORY", "CONSULTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Hỗ trợ chuyên gia công nghệ, pháp lý, tài chính, quản trị, kết nối đầu tư.",
        claims=[
            {"claim_type": "SERVICES", "claim_key": "expert_domains", "claim_value": "Công nghệ, Pháp lý, Tài chính, Quản trị, Kết nối đầu tư"},
        ],
    )

    # Seed 07: Hỗ trợ thử nghiệm & sản xuất thử
    _ensure_program(
        code="PILOT-PRODUCTION-SUPPORT",
        name="Hỗ trợ thử nghiệm & sản xuất thử",
        summary="Hỗ trợ chi phí cơ sở vật chất, linh kiện, vật tư chế tạo mẫu thử nghiệm và chuẩn bị thương mại hóa.",
        program_type="PILOT_PRODUCTION_SUPPORT",
        authority="Quỹ Đổi mới Công nghệ Quốc gia / Cục Phát triển Doanh nghiệp",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["PROTOTYPE", "MVP", "MARKET_VALIDATION"],
        trl_min=4,
        funding_min=100000000.0,
        funding_max=500000000.0,
        matching_fund_pct=30.0,
        eligible_costs=["EQUIPMENT", "TESTING", "RD_SALARY"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Hỗ trợ cơ sở vật chất, vật tư, linh kiện, sản phẩm mẫu.",
        claims=[
            {"claim_type": "ELIGIBLE_COSTS", "claim_key": "pilot_costs", "claim_value": "Cơ sở vật chất, vật tư, linh kiện, sản phẩm mẫu"},
        ],
    )

    # Seed 08: Hỗ trợ chuyển giao công nghệ
    _ensure_program(
        code="TECH-TRANSFER-SUPPORT",
        name="Hỗ trợ chuyển giao & giải mã công nghệ",
        summary="Hỗ trợ mua bản quyền công nghệ, giải mã, làm chủ công nghệ nguồn và giao dịch qua các sàn công nghệ.",
        program_type="TECHNOLOGY_TRANSFER_SUPPORT",
        authority="Cục Ứng dụng & Phát triển Công nghệ (Bộ KH&CN)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["MVP", "ACCELERATION", "SCALE_UP"],
        trl_min=5,
        funding_min=200000000.0,
        funding_max=2000000000.0,
        matching_fund_pct=40.0,
        eligible_costs=["EQUIPMENT", "IP_REGISTRATION", "CONSULTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Mua bản quyền, giải mã, làm chủ công nghệ, kết nối chuyển giao qua sàn.",
        claims=[
            {"claim_type": "ACTIVITIES", "claim_key": "transfer_scope", "claim_value": "Mua bản quyền, giải mã công nghệ, làm chủ công nghệ, kết nối giao dịch"},
        ],
    )

    # Seed 09: Hạ tầng dùng chung cho ĐMST
    _ensure_program(
        code="SHARED-INNOVATION-INFRA",
        name="Hạ tầng dùng chung cho đổi mới sáng tạo",
        summary="Tiếp cận phòng LAB đo kiểm, cơ sở ươm tạo, Maker Space, khu CNC và không gian làm việc chung phi tiền mặt.",
        program_type="INFRASTRUCTURE_SUPPORT",
        authority="Ban quản lý Khu CNC / NIC / Vườn ươm",
        geography="NATIONAL",
        company_types=["STARTUP", "SPIN_OFF", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["IDEA", "POC", "PROTOTYPE", "MVP"],
        trl_min=1,
        funding_min=0.0,
        funding_max=100000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["EQUIPMENT", "TESTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Hỗ trợ phi tiền mặt (Lab, Co-working, Maker Space, Khu CNC).",
        claimed_values={"support_mode": "NON_CASH"},
        claims=[
            {"claim_type": "RESOURCES", "claim_key": "facility_types", "claim_value": "Phòng LAB, cơ sở ươm tạo, khu công nghệ cao, co-working, maker space"},
        ],
    )

    # Seed 10: Hỗ trợ đào tạo nguồn nhân lực
    _ensure_program(
        code="WORKFORCE-TRAINING-SUPPORT",
        name="Hỗ trợ đào tạo nguồn nhân lực công nghệ",
        summary="Tài trợ hoặc hoàn trả chi phí tham gia các khóa đào tạo chuyên sâu, chứng chỉ công nghệ quốc tế cho nhân sự chủ chốt.",
        program_type="TRAINING_SUPPORT",
        authority="Bộ KH&CN / NIC / Sở TTTT",
        geography="NATIONAL",
        company_types=["STARTUP", "DIGITAL_SME", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["MVP", "ACCELERATION", "SCALE_UP"],
        trl_min=3,
        funding_min=20000000.0,
        funding_max=100000000.0,
        matching_fund_pct=30.0,
        eligible_costs=["TRAINING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Hỗ trợ khóa đào tạo, chứng chỉ công nghệ, ưu tiên nhân lực chủ chốt của dự án.",
        claims=[
            {"claim_type": "ELIGIBLE_COSTS", "claim_key": "training_types", "claim_value": "Khóa đào tạo chuyên sâu, chứng chỉ công nghệ trong và ngoài nước"},
        ],
    )

    # -------------------------------------------------------------
    # P2: ƯU ĐÃI THỂ CHẾ, TÍN DỤNG & NGUỒN LỰC HỆ SINH THÁI
    # -------------------------------------------------------------

    # Seed 11: Ưu đãi thuế cho DN KH&CN / công nghệ
    _ensure_program(
        code="SCIENCE-TECH-TAX-INCENTIVE",
        name="Ưu đãi thuế cho doanh nghiệp KH&CN/công nghệ",
        summary="Cơ chế miễn, giảm thuế thu nhập doanh nghiệp theo giai đoạn hoạt động cho doanh nghiệp đạt chứng nhận Doanh nghiệp KH&CN.",
        program_type="TAX_INCENTIVE",
        authority="Tổng cục Thuế / Bộ Tài chính / Bộ KH&CN",
        geography="NATIONAL",
        company_types=["SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["MARKET_VALIDATION", "ACCELERATION", "GROWTH", "SCALE_UP"],
        trl_min=6,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=["TAX_INCENTIVE"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Miễn/giảm thuế TNDN theo giai đoạn hoạt động cho DN KH&CN.",
        claims=[
            {"claim_type": "INCENTIVE", "claim_key": "cit_exemption", "claim_value": "Miễn/giảm thuế TNDN theo giai đoạn (cần chứng nhận DN KH&CN)"},
        ],
    )

    # Seed 12: Ưu đãi tiền thuê đất & mặt bằng
    _ensure_program(
        code="TECH-LAND-INCENTIVE",
        name="Ưu đãi đất & mặt bằng khu công nghệ cao",
        summary="Miễn, giảm tiền thuê đất và hỗ trợ mặt bằng công nghệ tại các khu công nghệ cao và khu CNTT tập trung.",
        program_type="LAND_INCENTIVE",
        authority="BQL Khu Công nghệ cao / UBND Tỉnh/TP",
        geography="NATIONAL",
        company_types=["SCIENCE_TECH_ENTERPRISE", "STARTUP"],
        project_stages=["ACCELERATION", "SCALE_UP", "GROWTH"],
        trl_min=7,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=["LAND_INCENTIVE"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Ưu đãi tiền thuê đất và mặt bằng tại khu CNC/khu CNTT tập trung.",
        claims=[
            {"claim_type": "INCENTIVE", "claim_key": "land_lease_reduction", "claim_value": "Ưu đãi tiền thuê đất và mặt bằng tại khu CNC"},
        ],
    )

    # Seed 13: Mua sắm công & đặt hàng sản phẩm đổi mới
    _ensure_program(
        code="PUBLIC-PROCUREMENT-INNOVATION",
        name="Mua sắm công & đặt hàng sản phẩm đổi mới sáng tạo",
        summary="Cơ chế ưu tiên mua sắm công, đặt hàng, giao trực tiếp và khoán chi theo kết quả đầu ra cho sản phẩm Make in Viet Nam.",
        program_type="PUBLIC_PROCUREMENT",
        authority="Bộ Kế hoạch và Đầu tư / Các cơ quan Nhà nước",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["MVP", "MARKET_VALIDATION", "ACCELERATION", "GROWTH"],
        trl_min=7,
        funding_min=500000000.0,
        funding_max=10000000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["EQUIPMENT", "TESTING"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Ưu tiên mua sắm công, đặt hàng, khoán chi theo kết quả cho sản phẩm Make in Viet Nam.",
        claims=[
            {"claim_type": "POLICY", "claim_key": "procurement_mode", "claim_value": "Giao trực tiếp / Đặt hàng / Khoán chi theo sản phẩm đầu ra Make in Viet Nam"},
        ],
    )

    # Seed 14: Sandbox — Cơ chế thử nghiệm có kiểm soát
    _ensure_program(
        code="REGULATORY-SANDBOX",
        name="Sandbox — Cơ chế thử nghiệm có kiểm soát",
        summary="Cơ chế thử nghiệm có kiểm soát cho công nghệ, sản phẩm hoặc mô hình kinh doanh mới (AI, Blockchain, Fintech, Tài sản số) trong phạm vi cho phép.",
        program_type="SANDBOX",
        authority="Ngân hàng Nhà nước / Bộ TTTT / UBND TP.HCM",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "DIGITAL_SME"],
        project_stages=["PROTOTYPE", "MVP", "MARKET_VALIDATION"],
        trl_min=4,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=[],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Thử nghiệm có kiểm soát cho AI, Blockchain, Tài sản số, Mô hình kinh doanh mới.",
        claims=[
            {"claim_type": "SCOPE", "claim_key": "sandbox_areas", "claim_value": "AI, Blockchain, Tài sản số, Công nghệ mới theo quyết định của cơ quan thẩm quyền"},
        ],
    )

    # Seed 15: Quỹ bảo lãnh tín dụng DNNVV
    _ensure_program(
        code="SME-CREDIT-GUARANTEE",
        name="Quỹ bảo lãnh tín dụng cho doanh nghiệp nhỏ và vừa",
        summary="Bảo lãnh vay vốn tại các ngân hàng thương mại cho startup và doanh nghiệp spin-off đã có doanh thu hoặc phương án hoàn vốn khả thi.",
        program_type="CREDIT_GUARANTEE",
        authority="Quỹ Bảo lãnh Tín dụng Địa phương / Ngân hàng Phát triển (VDB)",
        geography="NATIONAL",
        company_types=["STARTUP", "SPIN_OFF", "INNOVATIVE_SME"],
        project_stages=["MARKET_VALIDATION", "ACCELERATION", "GROWTH"],
        trl_min=6,
        funding_min=500000000.0,
        funding_max=5000000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["CREDIT_GUARANTEE"],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Kênh bảo lãnh tín dụng địa phương cho startup/spin-off đã có doanh thu.",
        claims=[
            {"claim_type": "FINANCIAL", "claim_key": "guarantee_scope", "claim_value": "Bảo lãnh tín dụng cho DN đã có doanh thu / dòng tiền"},
        ],
    )

    # Seed 16: Kênh vốn cổ phần & gọi vốn cộng đồng
    _ensure_program(
        code="EQUITY-CROWDFUNDING-CHANNEL",
        name="Kênh vốn cổ phần & gọi vốn cộng đồng",
        summary="Nền tảng kết nối mạng lưới nhà đầu tư thiên thần, sàn giao dịch vốn khởi nghiệp sáng tạo và gọi vốn cộng đồng.",
        program_type="CAPITAL_CHANNEL",
        authority="Bộ Kế hoạch và Đầu tư / NIC / Mạng lưới Angel",
        geography="NATIONAL",
        company_types=["STARTUP", "SPIN_OFF"],
        project_stages=["POC", "MVP", "ACCELERATION"],
        trl_min=3,
        funding_min=100000000.0,
        funding_max=5000000000.0,
        matching_fund_pct=0.0,
        eligible_costs=[],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Khuyến khích phát triển nền tảng crowdfunding và sàn giao dịch vốn ĐMST.",
        claims=[
            {"claim_type": "CHANNEL", "claim_key": "equity_channel", "claim_value": "Kết nối nhà đầu tư và nền tảng gọi vốn cộng đồng hợp pháp"},
        ],
    )

    # Seed 19: TP.HCM Mạng lưới trung tâm ĐMST (QĐ 3190)
    _ensure_program(
        code="HCMC-INNOVATION-CENTER-NETWORK",
        name="TP.HCM — Mạng lưới trung tâm đổi mới sáng tạo (QĐ 3190)",
        summary="Đề án phát triển mạng lưới trung tâm ĐMST tầm cỡ quốc tế tại TP.HCM hỗ trợ không gian nghiên cứu, ươm tạo và kết nối thị trường.",
        program_type="ECOSYSTEM_INFRASTRUCTURE",
        authority="UBND TP.HCM / Sở KH&CN TP.HCM",
        geography="LOCAL_HCM",
        company_types=["STARTUP", "SPIN_OFF", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["IDEA", "POC", "MVP", "ACCELERATION"],
        trl_min=2,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=[],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: QĐ 3190/QĐ-UBND Đề án phát triển mạng lưới trung tâm ĐMST tại TP.HCM.",
        legal_basis="Quyết định 3190/QĐ-UBND TP.HCM",
        claims=[
            {"claim_type": "INFRASTRUCTURE", "claim_key": "network_hubs", "claim_value": "Mạng lưới trung tâm ĐMST quốc tế tại TP.HCM"},
        ],
    )

    # Seed 20: TP.HCM Chính sách thu hút chuyên gia (QĐ 05/2026) - Reference Only
    _ensure_program(
        code="HCMC-TALENT-ATTRACTION-REF",
        name="TP.HCM — Chính sách thu hút chuyên gia, nhà khoa học (QĐ 05/2026)",
        summary="Chính sách thu hút chuyên gia, nhà khoa học, người có tài năng đặc biệt làm việc cho các chương trình ĐMST của TP.HCM.",
        program_type="TALENT_POLICY",
        authority="UBND TP.HCM / Sở Nội vụ / Sở KH&CN",
        geography="LOCAL_HCM",
        company_types=["SCIENCE_TECH_ENTERPRISE", "SPIN_OFF", "STARTUP"],
        project_stages=["RND", "MVP", "ACCELERATION"],
        trl_min=3,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=[],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=False,  # Reference only
        source_claim="Theo slide Founders’ Meetup #1: QĐ 05/2026/QĐ-UBND thu hút chuyên gia, nhà khoa học. Dữ liệu tham khảo, chưa ánh xạ trực tiếp thành quyền lợi dự án.",
        legal_basis="Quyết định 05/2026/QĐ-UBND TP.HCM",
        claims=[
            {"claim_type": "REFERENCE", "claim_key": "talent_scope", "claim_value": "Thu hút chuyên gia, nhà khoa học, người có tài năng đặc biệt"},
        ],
    )

    # Seed 23: Nguồn lực hệ sinh thái ĐMST (Phi tiền mặt)
    _ensure_program(
        code="ECOSYSTEM-SOFT-SUPPORT",
        name="Nguồn lực hệ sinh thái đổi mới sáng tạo",
        summary="Các hoạt động hỗ trợ phi tiền mặt: mạng lưới cố vấn (mentor), ngày hội ĐMST, giải thưởng, bản đồ công nghệ và truyền thông thương hiệu.",
        program_type="ECOSYSTEM_SUPPORT",
        authority="NIC / Sở KH&CN / Các đối tác hệ sinh thái",
        geography="NATIONAL",
        company_types=["STARTUP", "SPIN_OFF", "DIGITAL_SME"],
        project_stages=["IDEA", "POC", "PROTOTYPE", "MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=1,
        funding_min=0.0,
        funding_max=0.0,
        matching_fund_pct=0.0,
        eligible_costs=[],
        status="ACTIVE",
        verification_status="PENDING_FOUNDER_VERIFICATION",
        publish_to_matching=True,
        source_claim="Theo slide Founders’ Meetup #1: Đào tạo, mạng lưới chuyên gia/mentor, ngày hội ĐMST, giải thưởng, bản đồ và sàn giao dịch công nghệ.",
        claimed_values={"support_mode": "NON_CASH"},
        claims=[
            {"claim_type": "RESOURCES", "claim_key": "support_types", "claim_value": "Mentor, Tech Day, Giải thưởng ĐMST, Bản đồ công nghệ, Truyền thông"},
        ],
    )

    # -------------------------------------------------------------
    # DRAFT WATCHLIST: 5 CHƯƠNG TRÌNH QUỐC GIA DỰ THẢO 2026-2035
    # -------------------------------------------------------------

    _ensure_program(
        code="DRAFT-NAT-STARTUP-2026-2035",
        name="[Dự thảo] Chương trình Khởi nghiệp sáng tạo quốc gia giai đoạn 2026–2035",
        summary="Dự thảo chương trình quốc gia hỗ trợ PoC/MVP khoảng 500 triệu/doanh nghiệp, tổng kinh phí ước tính 1.650 tỷ đồng. Đang lấy ý kiến.",
        program_type="GRANT",
        authority="Bộ Khoa học và Công nghệ (Đang lấy ý kiến)",
        geography="NATIONAL",
        company_types=["STARTUP", "INNOVATIVE_SME"],
        project_stages=["POC", "MVP"],
        trl_min=3,
        funding_min=200000000.0,
        funding_max=500000000.0,
        matching_fund_pct=20.0,
        eligible_costs=["RD_SALARY", "TESTING", "MARKETING_PILOT"],
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        source_claim="Theo slide Founders’ Meetup #1: Dự thảo lấy ý kiến 7/2026; chưa có hiệu lực thi hành; theo dõi tiến độ ban hành.",
        claims=[
            {"claim_type": "DRAFT_CLAIM", "claim_key": "estimated_funding", "claim_value": "Dự kiến hỗ trợ PoC/MVP ~ 500 triệu/doanh nghiệp"},
        ],
    )

    _ensure_program(
        code="DRAFT-NAT-TECH-INNOVATION-2026",
        name="[Dự thảo] Chương trình Quốc gia Đổi mới công nghệ giai đoạn 2026–2035",
        summary="Dự thảo chương trình quốc gia đổi mới công nghệ, nâng cao năng lực hấp thu công nghệ cho doanh nghiệp Việt Nam.",
        program_type="GRANT",
        authority="Bộ Khoa học và Công nghệ (Dự thảo)",
        geography="NATIONAL",
        company_types=["SCIENCE_TECH_ENTERPRISE", "INNOVATIVE_SME"],
        project_stages=["MVP", "ACCELERATION", "SCALE_UP"],
        trl_min=4,
        funding_min=500000000.0,
        funding_max=3000000000.0,
        matching_fund_pct=30.0,
        eligible_costs=["EQUIPMENT", "RD_SALARY"],
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        source_claim="Theo slide Founders’ Meetup #1: Dự thảo chương trình quốc gia 2026-2035.",
    )

    _ensure_program(
        code="DRAFT-NAT-IP-DEV-2026",
        name="[Dự thảo] Chương trình Quốc gia Phát triển sở hữu trí tuệ giai đoạn 2026–2035",
        summary="Dự thảo hỗ trợ đăng ký sáng chế trong và ngoài nước, bảo hộ tài sản trí tuệ và thương mại hóa IP.",
        program_type="GRANT",
        authority="Cục Sở hữu Trí tuệ (Dự thảo)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "SPIN_OFF"],
        project_stages=["PROTOTYPE", "MVP", "MARKET_VALIDATION"],
        trl_min=3,
        funding_min=50000000.0,
        funding_max=300000000.0,
        matching_fund_pct=0.0,
        eligible_costs=["IP_REGISTRATION"],
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        source_claim="Theo slide Founders’ Meetup #1: Dự thảo hỗ trợ SHTT 2026-2035.",
    )

    _ensure_program(
        code="DRAFT-NAT-PRODUCTIVITY-QUALITY-2026",
        name="[Dự thảo] Chương trình Quốc gia Nâng cao năng suất, chất lượng 2026–2035",
        summary="Dự thảo hỗ trợ doanh nghiệp áp dụng các hệ thống quản lý, công cụ cải tiến năng suất chất lượng tiên tiến.",
        program_type="GRANT",
        authority="Tổng cục Tiêu chuẩn Đo lường Chất lượng (Dự thảo)",
        geography="NATIONAL",
        company_types=["INNOVATIVE_SME", "SCIENCE_TECH_ENTERPRISE"],
        project_stages=["ACCELERATION", "SCALE_UP"],
        trl_min=5,
        funding_min=50000000.0,
        funding_max=200000000.0,
        matching_fund_pct=20.0,
        eligible_costs=["CONSULTING", "TRAINING"],
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        source_claim="Theo slide Founders’ Meetup #1: Dự thảo Nâng cao năng suất chất lượng.",
    )

    _ensure_program(
        code="DRAFT-NAT-TECH-MARKET-2026",
        name="[Dự thảo] Chương trình Quốc gia Phát triển thị trường KH&CN 2026–2035",
        summary="Dự thảo kết nối cung - cầu công nghệ, phát triển mạng lưới sàn giao dịch và trung gian xúc tiến thương mại hóa KH&CN.",
        program_type="GRANT",
        authority="Bộ Khoa học và Công nghệ (Dự thảo)",
        geography="NATIONAL",
        company_types=["STARTUP", "SCIENCE_TECH_ENTERPRISE", "SPIN_OFF"],
        project_stages=["MVP", "MARKET_VALIDATION", "ACCELERATION"],
        trl_min=4,
        funding_min=100000000.0,
        funding_max=1000000000.0,
        matching_fund_pct=30.0,
        eligible_costs=["MARKETING_PILOT", "CONSULTING"],
        status="DRAFT",
        verification_status="DRAFT_WATCHLIST",
        publish_to_matching=False,
        source_claim="Theo slide Founders’ Meetup #1: Dự thảo phát triển thị trường KH&CN.",
    )

    db.commit()

