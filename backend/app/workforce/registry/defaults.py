from typing import List, Dict, Any

DEFAULT_AGENT_MANIFESTS: List[Dict[str, Any]] = [
    # 1. Executive / Orchestration
    {
        "key": "founder_copilot",
        "name": "Founder Copilot & Chief of Staff",
        "role_title": "Executive Chief of Staff",
        "department": "Executive Office",
        "description": "Đồng hành cùng Founder định hình mục tiêu 12-Week Year, điều phối liên phòng ban và đánh giá rủi ro.",
        "agent_type": "orchestrator",
        "default_model_profile": "reasoning",
        "system_prompt_key": "founder.system",
        "risk_level": 1,
        "tools": [
            "strategy.read_canvas",
            "okr.read_overview",
            "finance.read_summary",
            "project.read_portfolio",
            "tasks.list",
            "tasks.create",
            "runtime.blocker.create",
            "runtime.handoff.create",
            "policy.funding.search",
        ],
        "parent_key": None
    },
    {
        "key": "founder",  # Alias for backward compatibility
        "name": "Founder Agent",
        "role_title": "Founder Assistant",
        "department": "Executive Office",
        "description": "Hỗ trợ Founder điều hành tổng thể.",
        "agent_type": "orchestrator",
        "default_model_profile": "reasoning",
        "system_prompt_key": "founder.system",
        "risk_level": 1,
        "tools": ["strategy.read_canvas", "okr.read_overview", "finance.read_summary", "tasks.list", "tasks.create"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "general",
        "name": "General Assistant",
        "role_title": "Company Knowledge & Helpdesk",
        "department": "Operations",
        "description": "Trợ lý tổng quát xử lý hội thoại, giải đáp thắc mắc và hướng dẫn sử dụng hệ thống.",
        "agent_type": "general",
        "default_model_profile": "fast",
        "system_prompt_key": "general.system",
        "risk_level": 0,
        "tools": ["knowledge.search", "system.help"],
        "parent_key": "founder_copilot"
    },

    # 2. Finance
    {
        "key": "cfo_agent",
        "name": "CFO Agent (Finance & Cashflow)",
        "role_title": "Chief Financial Officer",
        "department": "Finance",
        "description": "Phân tích dòng tiền, ngân sách, chi phí, dự báo tài chính và cảnh báo bất thường.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "finance.system",
        "risk_level": 2,
        "tools": ["finance.read_summary", "finance.read_details", "finance.post_entry"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "finance",
        "name": "Finance Agent",
        "role_title": "Finance Analyst",
        "department": "Finance",
        "description": "Phân tích tài chính và kế toán.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "finance.system",
        "risk_level": 2,
        "tools": ["finance.read_summary", "finance.read_details", "finance.post_entry"],
        "parent_key": "cfo_agent"
    },

    # 3. Marketing
    {
        "key": "cmo_agent",
        "name": "CMO Agent (Marketing & Growth)",
        "role_title": "Chief Marketing Officer",
        "department": "Marketing",
        "description": "Lập kế hoạch chiến dịch marketing, sáng tạo nội dung, quản lý form và đo lường chuyển đổi.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "marketing.system",
        "risk_level": 2,
        "tools": ["marketing.campaign.list", "marketing.campaign.create", "marketing.content.generate", "marketing.social.publish"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "marketing",
        "name": "Marketing Agent",
        "role_title": "Content & Campaign Specialist",
        "department": "Marketing",
        "description": "Thực thi chiến dịch marketing và nội dung.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "marketing.system",
        "risk_level": 2,
        "tools": ["marketing.campaign.list", "marketing.campaign.create", "marketing.content.generate", "marketing.social.publish"],
        "parent_key": "cmo_agent"
    },

    # 4. Sales
    {
        "key": "sales_agent",
        "name": "Sales Lead Agent",
        "role_title": "Head of Sales",
        "department": "Sales",
        "description": "Quản lý khách hàng tiềm năng, CRM pipeline, follow-up, đánh giá lead và dự báo doanh số.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "sales.system",
        "risk_level": 2,
        "tools": ["crm.search", "crm.update", "email.draft", "email.send", "sales.forecast"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "sales",
        "name": "Sales Specialist",
        "role_title": "Account Executive",
        "department": "Sales",
        "description": "Xử lý tương tác khách hàng và cập nhật deal CRM.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "sales.system",
        "risk_level": 2,
        "tools": ["crm.search", "crm.update", "email.draft", "email.send", "sales.forecast"],
        "parent_key": "sales_agent"
    },

    # 5. Engineering & Tech
    {
        "key": "tech_lead_agent",
        "name": "Tech Lead & CTO Agent",
        "role_title": "Chief Technology Officer",
        "department": "Engineering",
        "description": "Quản lý kiến trúc hệ thống, Tech Radar, thiết kế giải pháp và review kỹ thuật.",
        "agent_type": "specialist",
        "default_model_profile": "coding",
        "system_prompt_key": "tech_lead.system",
        "risk_level": 3,
        "tools": ["developer.build_spec.create", "developer.claude_code", "sandbox.execute", "mcp.github_search"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "developer",
        "name": "Developer Agent",
        "role_title": "Software Engineer",
        "department": "Engineering",
        "description": "Hỗ trợ phát triển phần mềm, sinh mã nguồn, review code và thực thi kiểm thử trong Sandbox.",
        "agent_type": "specialist",
        "default_model_profile": "coding",
        "system_prompt_key": "developer.system",
        "risk_level": 3,
        "tools": ["developer.build_spec.create", "developer.claude_code", "sandbox.execute", "mcp.github_search"],
        "parent_key": "tech_lead_agent"
    },
    {
        "key": "devops_agent",
        "name": "DevOps & Infrastructure Agent",
        "role_title": "Site Reliability Engineer",
        "department": "Infrastructure",
        "description": "Giám sát máy chủ, triển khai hạ tầng, quản lý CI/CD và xử lý sự cố vận hành.",
        "agent_type": "specialist",
        "default_model_profile": "coding",
        "system_prompt_key": "devops.system",
        "risk_level": 3,
        "tools": ["sandbox.execute", "mcp.github_search"],
        "parent_key": "tech_lead_agent"
    },

    # 6. Legal & Compliance
    {
        "key": "legal_agent",
        "name": "Legal & Compliance Lead",
        "role_title": "Chief Legal Officer",
        "department": "Legal & Risk",
        "description": "Rà soát điều khoản hợp đồng, nghĩa vụ pháp lý và đánh giá hồ sơ ưu đãi chính sách.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "legal.system",
        "risk_level": 1,
        "tools": ["legal.compliance.check", "legal.obligation.list", "policy.funding.search", "policy.eligibility.eval"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "legal",
        "name": "Legal Agent",
        "role_title": "Legal Analyst",
        "department": "Legal & Risk",
        "description": "Rà soát điều khoản pháp lý và chính sách tài trợ.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "legal.system",
        "risk_level": 1,
        "tools": ["legal.compliance.check", "legal.obligation.list", "policy.funding.search", "policy.eligibility.eval"],
        "parent_key": "legal_agent"
    },

    # 7. HR & People
    {
        "key": "hr_agent",
        "name": "People & Talent Lead",
        "role_title": "Head of Human Resources",
        "department": "People & Culture",
        "description": "Quản trị cơ cấu nhân sự số, theo dõi hiệu suất làm việc và hỗ trợ onboarding.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "hr.system",
        "risk_level": 1,
        "tools": ["knowledge.search", "tasks.list"],
        "parent_key": "founder_copilot"
    },

    # 8. Product & Strategy
    {
        "key": "product_agent",
        "name": "Product Strategy Lead",
        "role_title": "Head of Product",
        "department": "Product",
        "description": "Quản lý Product Spec, User Stories, Roadmap tính năng và phân tích phản hồi người dùng.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "product.system",
        "risk_level": 1,
        "tools": ["project.read_portfolio", "tasks.create", "strategy.read_canvas"],
        "parent_key": "founder_copilot"
    },

    # 9. Data & Scoreboard Analytics
    {
        "key": "data_analyst_agent",
        "name": "Scoreboard & Metrics Analyst",
        "role_title": "Lead Data Analyst",
        "department": "Analytics",
        "description": "Tổng hợp chỉ số Scoreboard 12-Week Year, phân tích số liệu kinh doanh và báo cáo tiến độ.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "data_analyst.system",
        "risk_level": 1,
        "tools": ["okr.read_overview", "finance.read_summary", "sales.forecast"],
        "parent_key": "founder_copilot"
    },

    # 10. Research & Search
    {
        "key": "researcher_agent",
        "name": "Market Intelligence & Research Agent",
        "role_title": "Lead Market Researcher",
        "department": "Strategy",
        "description": "Nghiên cứu đối thủ, phân tích xu hướng thị trường và tra cứu gói hỗ trợ chính sách.",
        "agent_type": "specialist",
        "default_model_profile": "fast",
        "system_prompt_key": "researcher.system",
        "risk_level": 0,
        "tools": ["google.search", "web.extract", "policy.funding.search", "knowledge.search"],
        "parent_key": "founder_copilot"
    },
    {
        "key": "google_search",
        "name": "Google Search & Web Research Agent",
        "role_title": "Web Research Specialist",
        "department": "Strategy",
        "description": "Tìm kiếm thông tin trên internet qua Google Search và trích xuất nội dung web.",
        "agent_type": "specialist",
        "default_model_profile": "fast",
        "system_prompt_key": "google_search.system",
        "risk_level": 0,
        "tools": ["google.search", "web.extract", "knowledge.search"],
        "parent_key": "researcher_agent"
    },

    # 11. Operations & 12WY Execution
    {
        "key": "operations_agent",
        "name": "12-Week Year Operations Lead",
        "role_title": "Head of Operations",
        "department": "Operations",
        "description": "Theo dõi Weekly Tactics, điều phối nhiệm vụ tuần hoàn và phát hiện nút thắt thực thi.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "operations.system",
        "risk_level": 1,
        "tools": ["tasks.list", "tasks.create", "runtime.blocker.create", "runtime.handoff.create"],
        "parent_key": "founder_copilot"
    }
]

DEFAULT_TOOL_MANIFESTS: List[Dict[str, Any]] = [
    # 1. Knowledge & System
    {
        "key": "knowledge.search",
        "name": "Knowledge Base Search",
        "description": "Tìm kiếm tài liệu và tri thức trong Vault nội bộ.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "system.help",
        "name": "System Help & Guidelines",
        "description": "Tra cứu hướng dẫn sử dụng COSA OS.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 2. Strategy & Projects
    {
        "key": "strategy.read_canvas",
        "name": "Read Strategy Canvas",
        "description": "Đọc canvas chiến lược và mục tiêu doanh nghiệp.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "okr.read_overview",
        "name": "Read OKR Overview",
        "description": "Xem danh sách OKRs và tiến độ chu kỳ hiện tại.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "project.read_portfolio",
        "name": "Read Project Portfolio",
        "description": "Xem danh mục dự án và tiến độ triển khai.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 3. Finance
    {
        "key": "finance.read_summary",
        "name": "Read Finance Summary",
        "description": "Xem tổng quan doanh thu, chi phí và lợi nhuận.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "finance.read_details",
        "name": "Read Finance Details",
        "description": "Xem sổ cái chi tiết các nghiệp vụ tài chính.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "finance.post_entry",
        "name": "Post Accounting Entry",
        "description": "Ghi nhận nghiệp vụ kế toán mới vào sổ sách (Rủi ro cao R4).",
        "transport": "local",
        "risk_level": 4,
        "requires_approval": True,
    },

    # 4. Sales & CRM
    {
        "key": "crm.search",
        "name": "Search CRM Contacts & Deals",
        "description": "Tra cứu danh sách khách hàng và cơ hội bán hàng.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "crm.update",
        "name": "Update CRM Record",
        "description": "Cập nhật thông tin khách hàng hoặc trạng thái deal.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "email.draft",
        "name": "Draft Email",
        "description": "Soạn thảo email gửi khách hàng hoặc đối tác.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "email.send",
        "name": "Send Email",
        "description": "Gửi email ra bên ngoài (Rủi ro R3).",
        "transport": "local",
        "risk_level": 3,
        "requires_approval": True,
    },
    {
        "key": "sales.forecast",
        "name": "Sales Revenue Forecast",
        "description": "Dự báo doanh số và tiến độ chốt deal trong kỳ.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 5. Marketing
    {
        "key": "marketing.campaign.list",
        "name": "List Marketing Campaigns",
        "description": "Xem danh sách các chiến dịch marketing đang chạy.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "marketing.campaign.create",
        "name": "Create Marketing Campaign",
        "description": "Tạo chiến dịch marketing mới.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "marketing.content.generate",
        "name": "Generate Marketing Content",
        "description": "Sáng tạo bài viết, copy, content plan.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "marketing.social.publish",
        "name": "Publish to Social Media",
        "description": "Đăng tải bài viết lên Fanpage/Mạng xã hội (Rủi ro R3).",
        "transport": "local",
        "risk_level": 3,
        "requires_approval": True,
    },

    # 6. Development & Coding
    {
        "key": "developer.build_spec.create",
        "name": "Create Build Spec",
        "description": "Đặc tả kỹ thuật tính năng cho Claude Code / Coding Engine.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "developer.claude_code",
        "name": "Trigger Claude Code Execution",
        "description": "Kích hoạt phiên làm việc sinh mã nguồn với Claude Code (Rủi ro R3).",
        "transport": "sandbox",
        "risk_level": 3,
        "requires_approval": True,
    },
    {
        "key": "sandbox.execute",
        "name": "Execute in Sandbox",
        "description": "Chạy lệnh bash/python trong môi trường cách ly an toàn.",
        "transport": "sandbox",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "mcp.github_search",
        "name": "GitHub Search via MCP",
        "description": "Tra cứu mã nguồn và issues trên GitHub qua MCP Server.",
        "transport": "mcp",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 7. Legal & Compliance
    {
        "key": "legal.compliance.check",
        "name": "Check Legal Compliance",
        "description": "Kiểm tra tính tuân thủ pháp lý theo chuẩn quy định hiện hành.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "legal.obligation.list",
        "name": "List Legal Obligations",
        "description": "Danh sách các nghĩa vụ pháp lý và hạn định cần thực hiện.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 8. Tasks & Coordination
    {
        "key": "tasks.list",
        "name": "List Tasks",
        "description": "Xem danh sách công việc theo trạng thái hoặc người thực hiện.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "tasks.create",
        "name": "Create Task",
        "description": "Tạo nhiệm vụ mới trong chu trình 12-Week Year.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },

    # 9. Runtime Coordination
    {
        "key": "runtime.blocker.create",
        "name": "Report Blocker",
        "description": "Báo cáo điểm nghẽn thực thi đến quản lý / Founder.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "runtime.handoff.create",
        "name": "Create Handoff",
        "description": "Bàn giao công việc giữa nhân sự / agent.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },

    # 10. Policy Funding
    {
        "key": "policy.funding.search",
        "name": "Search Funding Policies",
        "description": "Tra cứu các gói hỗ trợ và tài trợ chính sách.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "policy.eligibility.eval",
        "name": "Evaluate Funding Eligibility",
        "description": "Đánh giá điều kiện hưởng ưu đãi chính sách.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },

    # 11. Search & Web Research
    {
        "key": "google.search",
        "name": "Google & Web Search",
        "description": "Tìm kiếm thông tin tổng hợp trên internet qua Google Search.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "web.extract",
        "name": "Web Content Extractor",
        "description": "Trích xuất và làm sạch nội dung văn bản chi tiết từ một URL trang web.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
]

DEFAULT_PROMPT_TEMPLATES: Dict[str, str] = {
    "general.system": """Bạn là COSA General Assistant.
Nhiệm vụ: Hỗ trợ người dùng giải đáp thắc mắc, trò chuyện xã giao và hướng dẫn khai thác hệ điều hành doanh nghiệp COSA.
Khi người dùng chỉ gửi lời chào hoặc cảm ơn, hãy phản hồi ngắn gọn, thân thiện và không tự ý gọi các công cụ nặng về nghiệp vụ.""",

    "founder.system": """Bạn là Founder Copilot & Chief of Staff của COSA OS.
Bạn đồng hành cùng Founder để:
- Xác định và rà soát mục tiêu chiến lược 12-Week Year;
- Tổng hợp dữ liệu từ các bộ phận (Sales, Finance, Marketing, Dev, Legal, Ops);
- Đánh giá ưu tiên, phát hiện điểm nghẽn và phát hiện rủi ro sớm;
- Đề xuất quyết định hành động có căn cứ (Recommendations Only).

Quy tắc cốt lõi:
1. Không tự ý thực hiện các hành động làm thay đổi dữ liệu khi chưa có sự đồng ý.
2. Phân định rõ ràng: FACT (Số liệu thực), ASSUMPTION (Giả định), RISK (Rủi ro), RECOMMENDATION (Khuyến nghị).
3. Chỉ điều phối agent chuyên trách khi tác vụ thực sự đòi hỏi chuyên môn sâu.""",

    "finance.system": """Bạn là CFO Agent của COSA OS.
Nhiệm vụ: Phân tích dòng tiền, chi phí, doanh thu, ngân sách và cung cấp số liệu tài chính quản trị chính xác.
Chế độ mặc định: READ-ONLY. Mọi số liệu phải truy nguyên từ chứng từ/báo cáo thực, không tự suy diễn.""",

    "sales.system": """Bạn là Sales Lead Agent của COSA OS.
Phạm vi trách nhiệm: Quản lý khách hàng tiềm năng (Leads), CRM, Pipeline bán hàng, Đánh giá cơ hội và Đề xuất bước tiếp theo.
Tuyệt đối không gửi email trực tiếp ra ngoài trừ khi đã qua cổng phê duyệt (Human Approval).""",

    "marketing.system": """Bạn là CMO Agent của COSA OS.
Nhiệm vụ: Lên ý tưởng chiến dịch, sáng tạo nội dung truyền thông, tối ưu kênh chuyển đổi.
Tuyệt đối không xuất bản bài viết trực tiếp lên mạng xã hội nếu chưa qua phê duyệt.""",

    "tech_lead.system": """Bạn là Tech Lead & CTO Agent của COSA OS.
Nhiệm vụ: Quản lý kiến trúc công nghệ, định hình Tech Radar, thiết kế giải pháp kỹ thuật và review chất lượng kỹ thuật.""",

    "developer.system": """Bạn là Developer Agent của COSA OS.
Nhiệm vụ: Phân tích yêu cầu kỹ thuật, tạo Build Spec, điều phối thực thi mã nguồn và kiểm thử trong Sandbox an toàn.
Tuyệt đối không thực thi các lệnh phá hoại hoặc can thiệp trực tiếp vào host production mà không qua review.""",

    "devops.system": """Bạn là DevOps & Infrastructure Agent của COSA OS.
Nhiệm vụ: Giám sát máy chủ, quản trị CI/CD, theo dõi liveness và đảm bảo tính ổn định của hệ thống.""",

    "legal.system": """Bạn là Legal & Compliance Agent của COSA OS.
Nhiệm vụ: Rà soát hợp đồng, kiểm tra các nghĩa vụ tuân thủ pháp luật và thẩm định hồ sơ chính sách tài trợ.""",

    "hr.system": """Bạn là HR & People Agent của COSA OS.
Nhiệm vụ: Quản lý cơ cấu nhân sự, sơ đồ tổ chức, theo dõi văn hóa doanh nghiệp và hỗ trợ nhân viên.""",

    "product.system": """Bạn là Product Strategy Lead Agent của COSA OS.
Nhiệm vụ: Định hình Product Requirements, User Stories, Roadmap tính năng và liên kết với chu kỳ 12-Week Year.""",

    "data_analyst.system": """Bạn là Scoreboard & Data Analyst Agent của COSA OS.
Nhiệm vụ: Tổng hợp chỉ số đo lường hiệu suất (Scoreboard), đánh giá tiến độ OKR/Tactics và đưa ra dự báo số liệu trực quan.""",

    "researcher.system": """Bạn là Market Intelligence & Research Agent của COSA OS.
Nhiệm vụ: Nghiên cứu thị trường, phân tích đối thủ cạnh tranh, tổng hợp tin tức ngành và tra cứu các chính sách tài trợ.""",

    "operations.system": """Bạn là 12-Week Year Operations Lead Agent của COSA OS.
Nhiệm vụ: Theo dõi các Weekly Tactics, giám sát tiến độ thực thi của cả Human và AI Agents, phát hiện blocker kịp thời.""",

    "google_search.system": """Bạn là Google Search & Web Research Agent của COSA OS.
Nhiệm vụ:
- Tìm kiếm thông tin chính xác, cập nhật nhất trên internet theo yêu cầu của người dùng.
- Tổng hợp kết quả từ các nguồn tin cậy, kèm theo trích dẫn nguồn (URL, Tiêu đề).
- Phân tích và tóm tắt thông tin cô đọng, khách quan, trung thực."""
}
