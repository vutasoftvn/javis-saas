"""
Marketing, Sales, Finance, Legal & Research Profile Definitions
"""
from agent.profiles.schema import AgentProfile


def get_marketing_profile() -> AgentProfile:
    return AgentProfile(
        id="marketing",
        name="Chief Marketing Officer",
        role="CMO",
        description="Nghiên cứu thị trường, định vị thương hiệu, xây dựng chiến dịch và sáng tạo nội dung",
        skills=["market-research", "pmf-discovery"],
        tools=["web.search", "web.fetch", "filesystem.write"],
        workflows=["wf-market-analysis"],
        model_policy={"default": "reasoning"},
        permissions=["web.search", "web.read", "filesystem.write"],
        is_system=True
    )


def get_sales_profile() -> AgentProfile:
    return AgentProfile(
        id="sales",
        name="Head of Sales",
        role="Head of Sales",
        description="Quản lý phễu bán hàng (Pipeline), chấm điểm lead ICP và soạn thảo kịch bản Cold Outreach",
        skills=["lead-generation"],
        tools=["crm.search_leads", "crm.create_lead"],
        workflows=["wf-lead-outreach"],
        model_policy={"default": "fast"},
        permissions=["crm.read", "crm.write"],
        is_system=True
    )


def get_finance_profile() -> AgentProfile:
    return AgentProfile(
        id="finance",
        name="Chief Financial Officer",
        role="CFO",
        description="Báo cáo P&L theo Thông tư 58, tính toán Cash Runway, phân bổ chi phí và lập mô hình tài chính",
        skills=["tt58-audit"],
        tools=["finance.query_pnl", "finance.calculate_runway"],
        workflows=["wf-financial-health"],
        model_policy={"default": "reasoning"},
        permissions=["finance.read"],
        is_system=True
    )


def get_legal_profile() -> AgentProfile:
    return AgentProfile(
        id="legal",
        name="General Counsel",
        role="Legal Officer",
        description="Rà soát hợp đồng kinh tế, tư vấn tuân thủ pháp lý doanh nghiệp và bảo hộ sở hữu trí tuệ",
        skills=["tt58-audit"],
        tools=["knowledge.search", "filesystem.read"],
        workflows=["wf-financial-health"],
        model_policy={"default": "reasoning"},
        permissions=["knowledge.read", "filesystem.read"],
        is_system=True
    )


def get_research_profile() -> AgentProfile:
    return AgentProfile(
        id="research",
        name="Head of Research",
        role="Head of Research",
        description="Thu thập dữ liệu chuyên sâu thị trường, phân tích xu hướng công nghệ và đối thủ cạnh tranh",
        skills=["market-research"],
        tools=["web.search", "web.fetch", "knowledge.search"],
        workflows=["wf-market-analysis"],
        model_policy={"default": "reasoning"},
        permissions=["web.search", "web.read", "knowledge.read"],
        is_system=True
    )
