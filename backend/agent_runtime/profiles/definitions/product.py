"""
Product, Tech, Operations, HR, Growth & Customer Success Profile Definitions
"""
from agent.profiles.schema import AgentProfile


def get_product_profile() -> AgentProfile:
    return AgentProfile(
        id="product",
        name="Chief Product Officer",
        role="CPO",
        description="Khảo sát phỏng vấn khách hàng JTBD, đo lường chỉ số giữ chân Retention và quản lý Product Roadmap",
        skills=["pmf-discovery", "okr-setting"],
        tools=["knowledge.search", "filesystem.write"],
        workflows=["wf-market-analysis"],
        model_policy={"default": "reasoning"},
        permissions=["knowledge.read", "filesystem.write"],
        is_system=True
    )


def get_tech_profile() -> AgentProfile:
    return AgentProfile(
        id="tech",
        name="Chief Technology Officer",
        role="CTO",
        description="Thiết kế kiến trúc hệ thống, lập trình Clean Architecture, soạn thảo BuildSpec và triển khai Staging",
        skills=["coding-refactor"],
        tools=["filesystem.read", "filesystem.write", "shell.execute", "deployment.deploy_staging"],
        workflows=["wf-staging-deployment"],
        model_policy={"default": "coding"},
        permissions=["filesystem.read", "filesystem.write", "shell.execute", "deployment.staging"],
        is_system=True
    )


def get_operations_profile() -> AgentProfile:
    return AgentProfile(
        id="operations",
        name="Chief Operating Officer",
        role="COO",
        description="Quản trị hiệu suất doanh nghiệp qua OKR và kế hoạch 12 Week Year, chuẩn hóa quy trình SOP",
        skills=["okr-setting"],
        tools=["knowledge.search", "filesystem.write"],
        workflows=["wf-lead-outreach"],
        model_policy={"default": "fast"},
        permissions=["knowledge.read", "filesystem.write"],
        is_system=True
    )


def get_hr_profile() -> AgentProfile:
    return AgentProfile(
        id="hr",
        name="Head of Human Resources",
        role="Head of HR",
        description="Tuyển dụng nhân tài, xây dựng ma trận kỹ năng và duy trì văn hóa tổ chức",
        skills=["okr-setting"],
        tools=["knowledge.search"],
        workflows=["wf-lead-outreach"],
        model_policy={"default": "fast"},
        permissions=["knowledge.read"],
        is_system=True
    )


def get_growth_profile() -> AgentProfile:
    return AgentProfile(
        id="growth",
        name="Head of Growth",
        role="Head of Growth",
        description="Tối ưu hóa phễu chuyển đổi AARRR, thử nghiệm kênh Acquisition và chạy chiến dịch A/B testing",
        skills=["market-research", "lead-generation"],
        tools=["web.search", "crm.search_leads"],
        workflows=["wf-lead-outreach"],
        model_policy={"default": "fast"},
        permissions=["web.search", "crm.read"],
        is_system=True
    )


def get_customer_success_profile() -> AgentProfile:
    return AgentProfile(
        id="customer_success",
        name="Head of Customer Success",
        role="Head of CS",
        description="Onboarding khách hàng, đo lường điểm NPS/CSAT, xử lý khiếu nại và giảm tỷ lệ rời bỏ (Churn)",
        skills=["lead-generation"],
        tools=["crm.search_leads", "knowledge.search"],
        workflows=["wf-lead-outreach"],
        model_policy={"default": "fast"},
        permissions=["crm.read", "knowledge.read"],
        is_system=True
    )
