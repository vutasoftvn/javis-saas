from typing import List, Dict, Any

DEFAULT_AGENT_MANIFESTS: List[Dict[str, Any]] = [
    {
        "key": "general",
        "name": "General Assistant",
        "description": "Trợ lý tổng quát xử lý hội thoại, giải đáp thắc mắc và hướng dẫn sử dụng hệ thống.",
        "agent_type": "general",
        "default_model_profile": "fast",
        "system_prompt_key": "general.system",
        "risk_level": 0,
        "tools": [
            "knowledge.search",
            "system.help",
        ]
    },
    {
        "key": "founder",
        "name": "Founder Agent",
        "description": "Hỗ trợ Founder định hình mục tiêu, tổng hợp dữ liệu liên phòng ban, đánh giá ưu tiên và điều phối.",
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
        ]
    },
    {
        "key": "sales",
        "name": "Sales Agent",
        "description": "Quản lý khách hàng tiềm năng, CRM pipeline, follow-up, đánh giá lead và dự báo doanh số.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "sales.system",
        "risk_level": 2,
        "tools": [
            "crm.search",
            "crm.update",
            "email.draft",
            "email.send",  # requires approval
            "sales.forecast",
        ]
    },
    {
        "key": "finance",
        "name": "Finance Agent",
        "description": "Phân tích dòng tiền, ngân sách, chi phí, dự báo tài chính và cảnh báo bất thường.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "finance.system",
        "risk_level": 2,
        "tools": [
            "finance.read_summary",
            "finance.read_details",
            "finance.post_entry",  # requires approval (R4)
        ]
    },
    {
        "key": "marketing",
        "name": "Marketing Agent",
        "description": "Lập kế hoạch chiến dịch marketing, sáng tạo nội dung, quản lý form và đo lường chuyển đổi.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "marketing.system",
        "risk_level": 2,
        "tools": [
            "marketing.campaign.list",
            "marketing.campaign.create",
            "marketing.content.generate",
            "marketing.social.publish",  # requires approval (R3)
        ]
    },
    {
        "key": "developer",
        "name": "Developer Agent",
        "description": "Hỗ trợ phát triển phần mềm, sinh mã nguồn, review code và thực thi kiểm thử qua Sandbox.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "developer.system",
        "risk_level": 3,
        "tools": [
            "developer.build_spec.create",
            "developer.claude_code",  # requires approval (R3)
            "sandbox.execute",
            "mcp.github_search",
        ]
    },
    {
        "key": "legal",
        "name": "Legal & Compliance Agent",
        "description": "Rà soát điều khoản, tính tuân thủ pháp lý và đánh giá hồ sơ ưu đãi chính sách.",
        "agent_type": "specialist",
        "default_model_profile": "reasoning",
        "system_prompt_key": "legal.system",
        "risk_level": 1,
        "tools": [
            "legal.compliance.check",
            "legal.obligation.list",
            "policy.funding.search",
            "policy.eligibility.eval",
        ]
    },
    {
        "key": "google_search",
        "name": "Google Search & Web Research Agent",
        "description": "Chuyên trách tìm kiếm thông tin trên internet, tra cứu dữ liệu web, tin tức và trích xuất nội dung bài viết.",
        "agent_type": "specialist",
        "default_model_profile": "fast",
        "system_prompt_key": "google_search.system",
        "risk_level": 0,
        "tools": [
            "google.search",
            "web.extract",
            "knowledge.search",
        ]
    },
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
        "name": "Search CRM Leads",
        "description": "Tìm kiếm thông tin khách hàng và cơ hội bán hàng.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "crm.update",
        "name": "Update CRM Lead",
        "description": "Cập nhật trạng thái lead hoặc ghi chú liên hệ.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "email.draft",
        "name": "Draft Email",
        "description": "Soạn thảo bản nháp email cho khách hàng.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "email.send",
        "name": "Send Email",
        "description": "Gửi email trực tiếp ra ngoài khách hàng (R3).",
        "transport": "local",
        "risk_level": 3,
        "requires_approval": True,
    },

    # 5. Marketing
    {
        "key": "marketing.campaign.list",
        "name": "List Marketing Campaigns",
        "description": "Xem danh sách các chiến dịch marketing.",
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
        "description": "Sinh bài viết quảng cáo hoặc kịch bản truyền thông.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "marketing.social.publish",
        "name": "Publish Social Post",
        "description": "Đăng bài viết lên mạng xã hội (R3).",
        "transport": "local",
        "risk_level": 3,
        "requires_approval": True,
    },

    # 6. Developer & Sandboxes
    {
        "key": "developer.build_spec.create",
        "name": "Create Build Spec",
        "description": "Tạo đặc tả kỹ thuật Build Spec cho Claude Code.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "developer.claude_code",
        "name": "Claude Code Executor",
        "description": "Ủy quyền cho Claude Code thực thi thay đổi mã nguồn trong sandbox.",
        "transport": "sandbox",
        "risk_level": 3,
        "requires_approval": True,
    },
    {
        "key": "sandbox.execute",
        "name": "Execute in Sandbox",
        "description": "Chạy lệnh bash/test trong môi trường Sandbox cô lập.",
        "transport": "sandbox",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "mcp.github_search",
        "name": "MCP GitHub Search",
        "description": "Tìm kiếm repositories và PRs thông qua GitHub MCP Server.",
        "transport": "mcp",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 7. Tasks & Operations
    {
        "key": "tasks.list",
        "name": "List Tasks",
        "description": "Xem danh sách công việc theo trạng thái.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },
    {
        "key": "tasks.create",
        "name": "Create Task",
        "description": "Tạo công việc mới trong workspace.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },
    {
        "key": "tasks.update_status",
        "name": "Update Task Status",
        "description": "Cập nhật tiến độ hoàn thành công việc.",
        "transport": "local",
        "risk_level": 2,
        "requires_approval": False,
    },

    # 8. Legal & Compliance
    {
        "key": "legal.compliance.check",
        "name": "Check Legal Compliance",
        "description": "Rà soát tính tuân thủ pháp lý doanh nghiệp.",
        "transport": "local",
        "risk_level": 1,
        "requires_approval": False,
    },
    {
        "key": "legal.obligation.list",
        "name": "List Legal Obligations",
        "description": "Xem danh mục nghĩa vụ pháp lý và thời hạn.",
        "transport": "local",
        "risk_level": 0,
        "requires_approval": False,
    },

    # 9. Company Runtime
    {
        "key": "runtime.blocker.create",
        "name": "Create Blocker",
        "description": "Báo cáo điểm nghẽn trong vận hành.",
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

    # 11. n8n Automation
    {
        "key": "n8n.schedule_timer",
        "name": "n8n Schedule Timer",
        "description": "Thiết lập timer hẹn giờ tự động qua n8n webhook.",
        "transport": "n8n",
        "risk_level": 2,
        "requires_approval": False,
    },

    # 12. Search & Web Research
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
Nhiệm vụ của bạn là hỗ trợ người dùng giải đáp thắc mắc, trò chuyện xã giao và hướng dẫn khai thác hệ điều hành doanh nghiệp COSA.
Khi người dùng chỉ gửi lời chào hoặc cảm ơn, hãy phản hồi ngắn gọn, thân thiện và không tự ý gọi các công cụ nặng về nghiệp vụ.""",

    "founder.system": """Bạn là Founder Agent của COSA OS.
Bạn đồng hành cùng Founder để:
- Xác định và rà soát mục tiêu chiến lược;
- Tổng hợp dữ liệu từ các bộ phận (Sales, Finance, Marketing, Dev, Legal);
- Đánh giá ưu tiên và phát hiện rủi ro sớm;
- Đề xuất quyết định hành động có căn cứ.

Quy tắc cốt lõi:
1. Không tự ý thực hiện các hành động làm thay đổi dữ liệu khi chưa có sự đồng ý.
2. Phân định rõ ràng: FACT (Số liệu thực), ASSUMPTION (Giả định), RISK (Rủi ro), RECOMMENDATION (Khuyến nghị).
3. Chỉ điều phối agent chuyên trách khi tác vụ thực sự đòi hỏi chuyên môn sâu.""",

    "sales.system": """Bạn là Sales Agent của COSA OS.
Phạm vi trách nhiệm: Quản lý khách hàng tiềm năng (Leads), CRM, Pipeline bán hàng, Đánh giá cơ hội và Đề xuất bước tiếp theo (Next Best Action).
Tuyệt đối không gửi email trực tiếp ra ngoài trừ khi đã qua cổng phê duyệt (Human Approval).""",

    "finance.system": """Bạn là Finance Agent của COSA OS.
Nhiệm vụ: Phân tích dòng tiền, chi phí, doanh thu, ngân sách và cung cấp số liệu tài chính quản trị chính xác.
Chế độ mặc định: READ-ONLY.
Mọi số liệu phải truy nguyên từ chứng từ/báo cáo thực, không được tự suy diễn hoặc tạo số liệu giả.""",

    "marketing.system": """Bạn là Marketing Agent của COSA OS.
Nhiệm vụ: Lên ý tưởng chiến dịch, sáng tạo nội dung truyền thông, tối ưu kênh chuyển đổi.
Tuyệt đối không xuất bản bài viết trực tiếp lên mạng xã hội nếu chưa qua phê duyệt.""",

    "developer.system": """Bạn là Developer Agent của COSA OS.
Nhiệm vụ: Phân tích yêu cầu kỹ thuật, tạo Build Spec, điều phối thực thi mã nguồn và kiểm thử trong Sandbox an toàn.
Tuyệt đối không thực thi các lệnh phá hoại hoặc can thiệp trực tiếp vào host production mà không qua review.""",

    "legal.system": """Bạn là Legal & Compliance Agent của COSA OS.
Nhiệm vụ: Rà soát hợp đồng, kiểm tra các nghĩa vụ tuân thủ pháp luật và thẩm định hồ sơ chính sách tài trợ.""",

    "google_search.system": """Bạn là Google Search & Web Research Agent của COSA OS.
Nhiệm vụ:
- Tìm kiếm thông tin chính xác, cập nhật nhất trên internet theo yêu cầu của người dùng.
- Tổng hợp kết quả từ các nguồn tin cậy, kèm theo trích dẫn nguồn (URL, Tiêu đề).
- Phân tích và tóm tắt thông tin cô đọng, khách quan, trung thực và loại bỏ các thông tin rác / không chính xác.
- Khi cần thêm chi tiết từ một bài viết cụ thể, sử dụng công cụ 'web.extract' để đọc toàn bộ nội dung."""
}
