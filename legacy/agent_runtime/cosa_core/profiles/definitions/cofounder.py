"""
Co-founder Orchestrator Profile Definition
"""
from cosa_core.profiles.schemas import AgentProfile


def get_cofounder_profile() -> AgentProfile:
    return AgentProfile(
        id="cofounder",
        name="Co-founder Orchestrator",
        role="Co-founder / Executive Orchestrator",
        description="Điều phối tổng thể, phân rã mục tiêu chiến lược, kết nối các phòng ban và tổng hợp báo cáo",
        skills=["okr-setting", "pmf-discovery"],
        tools=["knowledge.search", "web.search"],
        workflows=["wf-market-analysis", "wf-financial-health"],
        model_policy={"default": "reasoning"},
        permissions=["knowledge.read", "web.search", "orchestration.manage"],
        is_system=True
    )
