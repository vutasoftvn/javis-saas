"""
COSA RACRO Governance & Control Plane Sync Service.
Hiện thực hóa các quy tắc:
1. Control Plane Aggregate Sync (0% PII)
2. Knowledge Pack Precedence: Company Override > Factory Default
3. Phân quyền Admin: Bảo vệ System Prompts và Factory Spec
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class MarketingUsageAggregateSync(BaseModel):
    """Schema đồng bộ số liệu tổng hợp lên Supabase Control Plane (§10.2 Spec)."""
    company_id: str
    project_id: Optional[str] = None
    date: str
    research_runs: int = 0
    campaigns_created: int = 0
    leads_count: int = 0
    qualified_leads_count: int = 0
    customers_count: int = 0
    capability_usage: Dict[str, int] = Field(default_factory=dict)
    project_stage: str = Field(default="Validation")
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class RACROGovernanceService:
    # Danh sách các trường PII cấm xuất hiện trong Control Plane payload
    PII_FORBIDDEN_KEYS = {
        "name", "full_name", "email", "phone", "phone_number",
        "address", "transcript", "conversation", "message", "notes",
        "password", "secret", "bank_account", "tax_id"
    }

    # Danh sách các hành động nhạy cảm yêu cầu quyền Admin
    ADMIN_ONLY_ACTIONS = {
        "edit_core_prompt",
        "edit_system_spec",
        "reset_factory_pack",
        "modify_security_connectors",
        "override_data_locality_policy"
    }

    @classmethod
    def sanitize_and_build_aggregate_payload(
        cls,
        company_id: str,
        project_id: Optional[str],
        research_runs: int,
        campaigns_created: int,
        leads_count: int,
        qualified_leads_count: int,
        customers_count: int,
        capability_usage: Dict[str, int],
        project_stage: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> MarketingUsageAggregateSync:
        """Kiểm tra và xây dựng payload đồng bộ lên Control Plane, đảm bảo 0% PII (§10.2 Spec)."""
        # Kiểm tra nếu extra_data chứa trường PII
        if extra_data:
            for k in extra_data.keys():
                if k.lower() in cls.PII_FORBIDDEN_KEYS:
                    raise ValueError(f"Vi phạm ranh giới dữ liệu: Trường PII '{k}' không được phép gửi lên Control Plane!")

        return MarketingUsageAggregateSync(
            company_id=company_id,
            project_id=project_id,
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            research_runs=research_runs,
            campaigns_created=campaigns_created,
            leads_count=leads_count,
            qualified_leads_count=qualified_leads_count,
            customers_count=customers_count,
            capability_usage=capability_usage,
            project_stage=project_stage,
        )

    @staticmethod
    def resolve_effective_prompt(
        factory_prompt: str,
        company_override: Optional[str] = None,
    ) -> str:
        """Xử lý độ ưu tiên: Company Override > Factory Default (§11.2 Spec)."""
        if company_override and company_override.strip():
            return company_override.strip()
        return factory_prompt.strip()

    @classmethod
    def check_permission(cls, user_role: str, action: str) -> bool:
        """Kiểm tra quyền hạn người dùng đối với các tác vụ cấu hình hệ thống (§11.2 Spec)."""
        role_norm = user_role.lower()
        if action in cls.ADMIN_ONLY_ACTIONS:
            return role_norm in ["admin", "superadmin", "owner"]
        return True
