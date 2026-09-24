from __future__ import annotations

from agent.contracts.identity import PinnedSkillRef
from agent.contracts.model_policy import ModelPolicySpec
from agent.contracts.prompt import PromptSpec
from agent.contracts.spec import AgentSpec
from agent.executive_board.models import EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA
from agent.governance.contracts import AutonomyLevel

__all__ = [
    "COSA_AI_GOVERNANCE_AGENT_SPEC",
    "COSA_AI_GOVERNANCE_PROMPT",
    "COSA_COFOUNDER_ASSISTANT_AGENT_SPEC",
    "COSA_COFOUNDER_ASSISTANT_PROMPT",
    "COSA_CUSTOMER_SUPPORT_AGENT_SPEC",
    "COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC",
    "COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT",
    "COSA_CUSTOMER_SUPPORT_PROMPT",
    "COSA_DATA_AGENT_SPEC",
    "COSA_DATA_PROMPT",
    "COSA_DEFAULT_MODEL_POLICY",
    "COSA_DEPLOYED_AGENT_SPECS",
    "COSA_EXECUTIVE_CAIO_AGENT_SPEC",
    "COSA_EXECUTIVE_CAIO_PROMPT",
    "COSA_EXECUTIVE_CCO_AGENT_SPEC",
    "COSA_EXECUTIVE_CCO_PROMPT",
    "COSA_EXECUTIVE_CDO_AGENT_SPEC",
    "COSA_EXECUTIVE_CDO_PROMPT",
    "COSA_EXECUTIVE_CEO_AGENT_SPEC",
    "COSA_EXECUTIVE_CEO_PROMPT",
    "COSA_EXECUTIVE_CFO_AGENT_SPEC",
    "COSA_EXECUTIVE_CFO_PROMPT",
    "COSA_EXECUTIVE_CHIEF_OF_STAFF_AGENT_SPEC",
    "COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT",
    "COSA_EXECUTIVE_CHRO_AGENT_SPEC",
    "COSA_EXECUTIVE_CHRO_PROMPT",
    "COSA_EXECUTIVE_CMO_AGENT_SPEC",
    "COSA_EXECUTIVE_CMO_PROMPT",
    "COSA_EXECUTIVE_COO_AGENT_SPEC",
    "COSA_EXECUTIVE_COO_PROMPT",
    "COSA_EXECUTIVE_CPO_AGENT_SPEC",
    "COSA_EXECUTIVE_CPO_PROMPT",
    "COSA_EXECUTIVE_CRO_AGENT_SPEC",
    "COSA_EXECUTIVE_CRO_PROMPT",
    "COSA_EXECUTIVE_CTO_AGENT_SPEC",
    "COSA_EXECUTIVE_CTO_PROMPT",
    "COSA_EXECUTIVE_GC_AGENT_SPEC",
    "COSA_EXECUTIVE_GC_PROMPT",
    "COSA_FINANCE_AGENT_SPEC",
    "COSA_FINANCE_PROMPT",
    "COSA_KICKOFF_SUGGESTION_AGENT_SPEC",
    "COSA_KICKOFF_SUGGESTION_PROMPT",
    "COSA_LEGAL_AGENT_SPEC",
    "COSA_LEGAL_PROMPT",
    "COSA_MARKETING_AGENT_SPEC",
    "COSA_MARKETING_PROMPT",
    "COSA_OPERATIONS_AGENT_SPEC",
    "COSA_OPERATIONS_PROMPT",
    "COSA_PEOPLE_AGENT_SPEC",
    "COSA_PEOPLE_PROMPT",
    "COSA_PRODUCT_AGENT_SPEC",
    "COSA_PRODUCT_PROMPT",
    "COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC",
    "COSA_RESEARCH_INTELLIGENCE_PROMPT",
    "COSA_SALES_AGENT_SPEC",
    "COSA_SALES_PROMPT",
    "COSA_SECURITY_AGENT_SPEC",
    "COSA_SECURITY_PROMPT",
    "COSA_STRATEGY_AGENT_SPEC",
    "COSA_STRATEGY_PROMPT",
]

# Hash skill được pin bởi advisor overlay — sinh từ skillpacks/ qua parse_skillpack_spec;
# test_overlay_catalog đối chiếu lại để chống drift.
_ADVISOR_SKILL_HASHES: dict[str, tuple[str, str]] = {
    "engineering.workspace-site-builder": (
        "1.0.0",
        "e593a2256237dd91f35c981326c11936b7ad45df74fbd67a26df171bd36e0fe0",
    ),
    "executive.board-protocol": (
        "1.0.0",
        "e8fdd15bd8010c1d5636c026dd63e03d8ecf2c9165f3cce29ec839f94853ce96",
    ),
    "executive.caio-advisor": (
        "1.0.0",
        "7431268b12a450b3158461a770f0cd25b5fa72e038c327fd774e7226344d6bdb",
    ),
    "executive.cco-advisor": (
        "1.0.0",
        "ef0f9d4ebc726a725dde5260b175acafca529755ac0522ea7967d5fe74a2c1eb",
    ),
    "executive.cdo-advisor": (
        "1.0.0",
        "98224cb8380143c6a9f2bd60c14620bb040ba9f8b8c1236b0f9518fe49c8ccad",
    ),
    "executive.ceo-advisor": (
        "1.0.0",
        "7de38afd93f98ffc285792f3ac7e2601feb452cb2af3a13c996c40757280b1a2",
    ),
    "executive.cfo-advisor": (
        "1.0.0",
        "52dbcc7b0dd1c6236c9dff6821739087e4904656d714ff1eb50ea99294bed3da",
    ),
    "executive.chief-of-staff": (
        "1.0.0",
        "ee99e1b7d9bccab53d0a110abc7919e9628420ed45300196f7170bb0d3ca9a90",
    ),
    "executive.chro-advisor": (
        "1.0.0",
        "bb5d73d7fc6f7ebe5963417c6d2df3782580be0a3798d1a24e7b88758e8643c8",
    ),
    "executive.ciso-advisor": (
        "1.0.0",
        "49a4d6a46ed6b0437b7730b7e091c0fe84691e0d9545b663fbfbe0a7494d7485",
    ),
    "executive.cmo-advisor": (
        "1.0.0",
        "aa042d0f313687c2f225ce5bff34ee8704615ddff55c2dbd7a054afa9aaea24f",
    ),
    "executive.coo-advisor": (
        "1.0.0",
        "b17c6f6bf6c4931241d0f6a410dd0090531f02c83d6eecae08159f2e8cf870c3",
    ),
    "executive.cpo-advisor": (
        "1.0.0",
        "39973d3d3bd616c8c9653fa2a722ae080d317441406c2e33153ea89c2bed18be",
    ),
    "executive.cro-advisor": (
        "1.0.0",
        "c772513824907d8a61f02dc8af40ca6e34a74f3230126c46e44b36fe68c77db2",
    ),
    "executive.cto-advisor": (
        "1.0.0",
        "021076c53f5be56aa07e1edbdb49afe173b6cd5368f15c4392e3aac4dd742667",
    ),
    "executive.gc-advisor": (
        "1.0.0",
        "5cedb3d84ba6263aac8ff948c091416db68d2aebaa82d5ea576984cdd4cabca5",
    ),
    "executive.vpe-advisor": (
        "1.0.0",
        "865c8411d9c2ec11e67f5f522d6abf046117cc9a590fb56a5bc99d94c3f463cf",
    ),
}


def _advisor_skills(*skill_ids: str) -> list[PinnedSkillRef]:
    return [
        PinnedSkillRef(
            skill_id=sid,
            version=_ADVISOR_SKILL_HASHES[sid][0],
            definition_hash=_ADVISOR_SKILL_HASHES[sid][1],
        )
        for sid in skill_ids
    ]


# ModelPolicySpec dùng chung cho mọi COSA agent — chỉ pin provenance/lineage
# (Wave M2b); runtime thật vẫn đọc DEEPSEEK_* env qua
# apps/cosa/composition/model_provider.py::build_deepseek_model(), KHÔNG đọc
# field này. Xem Global Constraints của plan Wave M2b.
COSA_DEFAULT_MODEL_POLICY = ModelPolicySpec(
    id="cosa.model_policy.default",
    version="1.0.0",
    model="deepseek-chat",
).with_hash()

COSA_OPERATIONS_PROMPT = PromptSpec(
    id="cosa.agents.operations.prompt",
    version="1.0.0",
    text="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
).with_hash()

COSA_COFOUNDER_ASSISTANT_PROMPT = PromptSpec(
    id="cosa.agents.founder_assistant.prompt",
    version="1.0.0",
    text=(
        "Trợ lý Đồng sáng lập AI (AI Co-Founder & Thinking Partner) của Founder. "
        "Bảo vệ thời gian và sự tập trung của Founder như tài nguyên quý giá nhất: kỷ luật 1 mục tiêu duy nhất mỗi tuần (1 goal/week), "
        "duy trì nhịp giao hàng thứ Sáu (Ship every Friday), phân bổ sáng tập trung xây dựng (Build), chiều phân phối và bán hàng (Market/Sell). "
        "Phản biện sắc sảo chống phình phạm vi (anti-scope creep), hỏi thẳng 'Tính năng này ai đã yêu cầu?' trước khi cho phép lập trình. "
        "Thúc đẩy MVP kiểm chứng trong 2 tuần, nói chuyện với 10 người dùng thay vì viết 10 tính năng mới. "
        "Cảnh báo số tuần runway sinh tồn và bảo toàn năng lượng, chống kiệt sức cho Founder. "
        "Hoạt động nghiêm ngặt ở mức trần tự trị L0_OBSERVE (gợi ý, phân tích và đồng hành hội thoại; không tự ý thực thi các tác vụ nền có rủi ro)."
    ),
).with_hash()

COSA_FINANCE_PROMPT = PromptSpec(
    id="cosa.agents.finance.prompt",
    version="1.0.0",
    text="Chuyên viên tài chính kế toán, lập lệnh thanh toán và ghi nhận sổ cái giao dịch (Bắt buộc Human Approval cho các khoản chi).",
).with_hash()

COSA_MARKETING_PROMPT = PromptSpec(
    id="cosa.agents.marketing.prompt",
    version="1.0.0",
    text="Chuyên viên chiến lược marketing và sáng tạo nội dung, xây dựng định vị sản phẩm và copywriting dựa trên bằng chứng thực nghiệm.",
).with_hash()

COSA_OPERATIONS_AGENT_SPEC = AgentSpec(
    id="cosa.agents.operations",
    # 1.2.0 (WGA int. point #3): thêm operations.task.create_draft vào
    # capability_refs để agent trong workspace_task_sweep phân rã tiếp 1 task
    # thành sub-task nháp. task.advance KHÔNG nằm đây — worker sweep gọi trực
    # tiếp qua HTTP delegation, không qua kernel.
    # 1.3.0 (Task 10, plan local-first-enterprise-knowledge): thêm
    # workspace.context.read — đây là spec thật sự chạy cho founder chat mặc
    # định (conversation_routes.py: active_agent_profile hoặc "operations"),
    # không tạo agent "founder_assistant" riêng vì role sản phẩm không khác
    # biệt thật (CLAUDE.md rule 3 — không nhân bản kiến trúc khi chưa cần).
    version="1.3.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên quản lý vận hành công việc, theo dõi tiến độ task và OKRs của doanh nghiệp.",
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
        "operations.task.create_draft",
        "strategy.project.get",
        "strategy.next_best_action.get",
        "strategy.evidence.list",
        "analytics.metric_contract.get",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="lifecycle.context-resolver",
            version="1.0.0",
            definition_hash="d2cd448f9012ae55f12d20b40315b79f517136fc8b55577f651dd4e36d2bcb98",
        ),
        PinnedSkillRef(
            skill_id="lifecycle.next-best-action",
            version="1.0.0",
            definition_hash="4f554c271dcd05e47dfcb4480f10e760dc02c24e0b510046b220afe415527ab9",
        ),
        PinnedSkillRef(
            skill_id="operations.weekly-review",
            version="1.0.0",
            definition_hash="cd5f56dfdc6178f0fadafbcdf585a9787eeee8393a783d9f01393a771d761f56",
        ),
        # Tranche C (2026-08-31): L1_PROPOSE/artifact-only, no runtime.tools — safe
        # to pin freely per Tranche C DoD ("Pin L0/L1 skills freely only after
        # registry acceptance"). Acceptance: tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py.
        PinnedSkillRef(
            skill_id="operations.sop-builder",
            version="1.1.0",
            definition_hash="a7a5ec52145df786eee769d37b8e7d90a9dbb6f00abc2c4e84a8d6d83428d824",
        ),
        PinnedSkillRef(
            skill_id="operations.automation-design",
            version="1.0.0",
            definition_hash="148bb889f6220dafc4aa09445ca8534e4bb551016494e78d27782c2ecfe6ba93",
        ),
    ],
    prompt_ref=COSA_OPERATIONS_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Operations Specialist Agent"},
)


COSA_COFOUNDER_ASSISTANT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.founder_assistant",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=COSA_COFOUNDER_ASSISTANT_PROMPT.text,
    capability_refs=[
        "operations.task.list",
        "operations.task.read",
        "operations.task.create_draft",
        "strategy.project.get",
        "strategy.next_best_action.get",
        "strategy.evidence.list",
        "analytics.metric_contract.get",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="lifecycle.context-resolver",
            version="1.0.0",
            definition_hash="d2cd448f9012ae55f12d20b40315b79f517136fc8b55577f651dd4e36d2bcb98",
        ),
        PinnedSkillRef(
            skill_id="lifecycle.next-best-action",
            version="1.0.0",
            definition_hash="4f554c271dcd05e47dfcb4480f10e760dc02c24e0b510046b220afe415527ab9",
        ),
        PinnedSkillRef(
            skill_id="operations.weekly-review",
            version="1.0.0",
            definition_hash="cd5f56dfdc6178f0fadafbcdf585a9787eeee8393a783d9f01393a771d761f56",
        ),
        PinnedSkillRef(
            skill_id="marketing.founder-story-bank",
            version="1.0.0",
            definition_hash="ffe03957f3e4bc0170fee4fac0305e5c9e06623e84981a0d021e7872a14563de",
        ),
    ],
    prompt_ref=COSA_COFOUNDER_ASSISTANT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Co-Founder Assistant Agent", "role": "founder_assistant"},
)


COSA_FINANCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.finance",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions="Chuyên viên tài chính kế toán, theo dõi và ghi nhận sổ cái giao dịch của doanh nghiệp.",
    capability_refs=[
        "finance.connection.read",
        "finance.transaction.read",
        "finance.transaction.record",
        "finance.transaction.classify.propose",
        "finance.accounting_document.create_draft",
        "finance.accounting_document.confirm",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="finance.runway-forecast",
            version="1.0.0",
            definition_hash="4110f57eb5088169680d96c5b03e32effd59365ae6c9915697f29c4a827688ee",
        ),
        PinnedSkillRef(
            skill_id="finance.budget-guardrails",
            version="1.0.0",
            definition_hash="e06cd67cb3704a5328fd02f4f5d29ae11c1c0f44619f79015102e462cccb017f",
        ),
        # Tranche C (2026-08-31): L1_PROPOSE/artifact-only, no runtime.tools — never
        # records a transaction itself, only labels CAC/LTV inputs as assumptions.
        PinnedSkillRef(
            skill_id="finance.unit-economics",
            version="1.1.0",
            definition_hash="055a7dfc94e9bf37ad06f36bafe8fc16d8d3187a5c250fd2b7acd231a97d6706",
        ),
    ],
    prompt_ref=COSA_FINANCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Finance Specialist Agent"},
)


COSA_MARKETING_AGENT_SPEC = AgentSpec(
    id="cosa.agents.marketing",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions="Chuyên viên chiến lược marketing và sáng tạo nội dung, xây dựng định vị sản phẩm và copywriting dựa trên bằng chứng thực nghiệm.",
    capability_refs=[
        "commercial.marketing_context.read",
        "commercial.marketing_context.write",
        "campaign.asset.write",
        "experiment.write",
        "web.search",
        "knowledge.profile.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[
        PinnedSkillRef(
            skill_id="strategy.positioning",
            version="1.1.0",
            # 2026-08-31: nội dung nghiệp vụ ICP/JTBD/Switching-forces hợp nhất từ
            # marketing.positioning (đã retire) — xem skill-source-attribution.md.
            definition_hash="e3649b7d635f2d45ae56d9e2e2780364837708652e7541db2af0eb9eee54cc92",
        ),
        PinnedSkillRef(
            skill_id="research.deep-research",
            version="1.2.0",
            definition_hash="fc85683dbb87b9ff1b9c0e25004f42269d20a8c5369bf4e3139550ed7f403625",
        ),
        PinnedSkillRef(
            skill_id="growth.bootstrapped-engine",
            version="1.0.0",
            definition_hash="d0684c24766b577a1628aaf874778fdbc8ebb07d4bc2908c04de485b835b3020",
        ),
        PinnedSkillRef(
            skill_id="strategy.competitor-profiling",
            version="1.0.0",
            definition_hash="c3bc6ce06f41005b679dd1092a9060b9cc1c3064190d16638f322c27eaeb084f",
        ),
        PinnedSkillRef(
            skill_id="marketing.channel-strategy",
            version="1.0.0",
            definition_hash="d636130cf1c7dae3bdaadf1738e476421353d16c5bae3159dfa7ec62524f80a3",
        ),
        # Tranche C (2026-08-31): all L1_PROPOSE/artifact-only, no runtime.tools —
        # safe to pin freely per Tranche C DoD ("Pin L0/L1 skills freely only after
        # registry acceptance"). Acceptance: tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py.
        PinnedSkillRef(
            skill_id="marketing.gtm-funnel",
            version="1.0.0",
            definition_hash="eead9ea09375bd5059c7dcbaf42838f9a3bc97c796917cb0e70a8576d6dc5327",
        ),
        PinnedSkillRef(
            skill_id="marketing.content-strategy",
            version="1.0.0",
            definition_hash="fa10e76a98a0ecb0ab9e71508bdb53f4c3754abffbdfb2d8831e249d0513916c",
        ),
        PinnedSkillRef(
            skill_id="marketing.landing-cro",
            version="1.0.0",
            definition_hash="37190f9c706299294ce60240515c611403ab62a459d7aae2049ae16f15331ff5",
        ),
        PinnedSkillRef(
            skill_id="marketing.paid-experiments",
            version="1.0.0",
            definition_hash="6b3b3856d6f5049f4746c82f235e101237b5df40ae71e7e6c278d89418666730",
        ),
        PinnedSkillRef(
            skill_id="marketing.brand-narrative",
            version="1.0.0",
            definition_hash="c0ed3ea3babeb1aec9a086d81d383b9371309f414125889a96a2f6443b056fd4",
        ),
        PinnedSkillRef(
            skill_id="marketing.reputation-monitoring",
            version="1.0.0",
            definition_hash="2a35c36a8890cdf6bee3a4fe0be922caa185c02603a3128c47a959db607f76e0",
        ),
        PinnedSkillRef(
            skill_id="marketing.linkedin-presence",
            version="1.1.0",
            definition_hash="1f1be5ece1ce1a08add18eca458423cddfd7ea6a602e7b50512e408218f7da5f",
        ),
        PinnedSkillRef(
            skill_id="marketing.content-humanizer",
            version="1.1.0",
            definition_hash="878b384d55584b74eacee386963d242746d33301635f41230fa29cd27e7090d0",
        ),
        PinnedSkillRef(
            skill_id="marketing.founder-story-bank",
            version="1.0.0",
            definition_hash="ffe03957f3e4bc0170fee4fac0305e5c9e06623e84981a0d021e7872a14563de",
        ),
        PinnedSkillRef(
            skill_id="marketing.linkedin-engagement-ops",
            version="1.0.0",
            definition_hash="bfc69a93d6e18e3a4056cc3151a06b9f58bdcfb6e0ecbd87a60836f5b55417e1",
        ),
    ],
    prompt_ref=COSA_MARKETING_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Marketing Specialist Agent"},
)


COSA_CUSTOMER_SUPPORT_PROMPT = PromptSpec(
    id="cosa.agents.customer_support.prompt",
    version="1.0.0",
    text=(
        "Bạn là Copilot hỗ trợ nhân sự Customer Support. Chỉ ĐỌC context thread + hồ sơ khách 360 + "
        "knowledge đã duyệt, rồi TẠO ARTIFACT: tóm tắt, bản nháp trả lời (kèm evidence_refs), intent, "
        "thông tin còn thiếu, tín hiệu bán hàng. TUYỆT ĐỐI không gửi tin, không ghi CRM, không hứa "
        "chính sách/bồi thường. Nếu khách chưa xác thực danh tính, KHÔNG tiết lộ account/invoice/PII — "
        "đề xuất xác thực hoặc chuyển người."
    ),
).with_hash()

COSA_CUSTOMER_SUPPORT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.customer_support",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,  # artifact_only: chỉ read + tạo artifact
    instructions=COSA_CUSTOMER_SUPPORT_PROMPT.text,
    capability_refs=[
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
    ],
    model_input_capability_ref=None,
    prompt_ref=COSA_CUSTOMER_SUPPORT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Customer Support Copilot"},
)

COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT = PromptSpec(
    id="cosa.agents.customer_support_autopilot.prompt",
    version="1.0.0",
    text=(
        "Autopilot hẹp: CHỈ trả lời câu hỏi khớp CHÍNH XÁC một mục knowledge đã duyệt (FAQ) hoặc thu "
        "thập thông tin qualification theo form giới hạn. Nếu độ khớp thấp / có sắc thái / khách chưa "
        "xác thực / vượt phạm vi FAQ ⇒ handoff cho người (engagement.assignment.write op=handoff_human), "
        "KHÔNG tự trả lời. Không hứa chính sách, không refund/discount, không đổi CRM."
    ),
).with_hash()

COSA_CUSTOMER_SUPPORT_AUTOPILOT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.customer_support_autopilot",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L2_EXECUTE,  # write mode: act / execute
    instructions=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.text,
    capability_refs=[
        "engagement.thread.read",
        "commercial.customer_360.read",
        "knowledge.profile.read",
        "engagement.message.draft",
        "engagement.message.send",  # REQUIRE_APPROVAL trừ template pre-authorize
        "engagement.assignment.write",  # để handoff
    ],
    model_input_capability_ref=None,
    prompt_ref=COSA_CUSTOMER_SUPPORT_AUTOPILOT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Customer Support Autopilot (narrow FAQ)"},
)

COSA_KICKOFF_SUGGESTION_PROMPT = PromptSpec(
    id="cosa.agents.kickoff_suggestion.prompt",
    version="1.0.0",
    text="AI Co-founder gợi ý kết quả và các hành động tuần đầu tiên của vòng khởi nghiệp từ thông tin Founder cung cấp.",
).with_hash()

COSA_KICKOFF_SUGGESTION_AGENT_SPEC = AgentSpec(
    id="cosa.agents.kickoff_suggestion",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=(
        "You are an AI Co-founder assisting in analyzing and suggesting a 1-sentence outcome "
        "and 1-3 key actions for the first week of a startup cycle based on provided context. "
        "Follow the language requirement in the user prompt and return strictly JSON format."
    ),
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_KICKOFF_SUGGESTION_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Kickoff Suggestion Specialist Agent"},
)

COSA_RESEARCH_INTELLIGENCE_PROMPT = PromptSpec(
    id="cosa.agents.research_intelligence.prompt",
    version="1.0.0",
    text="Chuyên viên nghiên cứu thị trường, thu thập dữ liệu và phân tích đối thủ cạnh tranh.",
).with_hash()

COSA_RESEARCH_INTELLIGENCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.research_intelligence",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=COSA_RESEARCH_INTELLIGENCE_PROMPT.text,
    capability_refs=[
        "strategy.evidence.list",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_RESEARCH_INTELLIGENCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Research & Intelligence Specialist Agent"},
)

COSA_STRATEGY_PROMPT = PromptSpec(
    id="cosa.agents.strategy.prompt",
    version="1.0.0",
    text="Chuyên viên hoạch định chiến lược kinh doanh và theo dõi mục tiêu OKRs.",
).with_hash()

COSA_STRATEGY_AGENT_SPEC = AgentSpec(
    id="cosa.agents.strategy",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L0_OBSERVE,
    instructions=COSA_STRATEGY_PROMPT.text,
    capability_refs=[
        "strategy.project.get",
        "strategy.next_best_action.get",
        "strategy.evidence.list",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_STRATEGY_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Strategy Specialist Agent"},
)

COSA_SALES_PROMPT = PromptSpec(
    id="cosa.agents.sales.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên phát triển kinh doanh và quản lý cơ hội bán hàng (B2B Sales Specialist). "
        "Chỉ đọc dữ liệu pipeline và CRM được phân quyền của Project, phân tích nhu cầu khách hàng, "
        "soạn thảo kế hoạch tiếp cận và đề xuất bước tiếp theo (L1_PROPOSE). Tuyệt đối không tự ý gửi tin nhắn, "
        "thay đổi giá hay cam kết pháp lý/tài chính ngoài phạm vi."
    ),
).with_hash()

COSA_SALES_AGENT_SPEC = AgentSpec(
    id="cosa.agents.sales",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_SALES_PROMPT.text,
    capability_refs=[
        "project.crm.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_SALES_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Sales Specialist Agent"},
)

COSA_EXECUTIVE_CRO_PROMPT = PromptSpec(
    id="cosa.executive.cro.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Kinh doanh (Chief Revenue Officer Advisor). "
        "Đánh giá pipeline doanh thu, năng lực sales enablement, ràng buộc giá và mức độ liên kết "
        "RevOps trong các phiên thảo luận của Ban điều hành, chỉ dựa trên dữ liệu CRM đã được "
        "phân quyền/redact của Project (L1_PROPOSE, advisory-only) — luôn nêu rõ khoảng trống "
        "bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền thay đổi giá, phê duyệt hợp đồng, ghi/sửa dữ liệu CRM hay gửi "
        "tin nhắn ra ngoài."
    ),
).with_hash()

COSA_EXECUTIVE_CRO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cro",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CRO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cro-advisor"),
    prompt_ref=COSA_EXECUTIVE_CRO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CRO Advisor", "advisory_only": True},
)

COSA_CODING_PROMPT = PromptSpec(
    id="cosa.agents.coding.prompt",
    version="1.0.0",
    text=(
        "Kỹ sư phát triển phần mềm (Software Engineering Specialist). "
        "Chỉ đọc bằng chứng thực thi kỹ thuật (Engineering Evidence) đã được xác thực, "
        "phân tích tính khả thi kiến trúc và rủi ro triển khai (L1_PROPOSE). "
        "Tuyệt đối không có quyền shell trực tiếp, không tự ý deploy hay sửa đổi hạ tầng/codebase."
    ),
).with_hash()

COSA_CODING_AGENT_SPEC = AgentSpec(
    id="cosa.agents.coding",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_CODING_PROMPT.text,
    capability_refs=[
        "engineering.evidence.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_CODING_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Coding Specialist Agent"},
)

COSA_PRODUCT_PROMPT = PromptSpec(
    id="cosa.agents.product.prompt",
    version="1.1.0",
    text=(
        "Chuyên viên sản phẩm (Product Specialist). "
        "Định hướng kết quả (Outcome > Output), bảo vệ sản phẩm khỏi bẫy gia công tính năng (Feature Factory) "
        "và số liệu hình thức (Metrics Theater). "
        "Kiểm soát bài toán qua Framing Gate: loại bỏ giải pháp áp đặt sẵn (solution smuggling), "
        "yêu cầu chỉ số thành công đo lường được (baseline -> target -> timeline), và ngăn phình phạm vi. "
        "Chỉ đọc snapshot Product Decision Dossier và tài liệu tri thức để phân tích, lập PRD 10 mục chuẩn, "
        "phân rã User Stories theo lát cắt dọc (Vertical Slicing), và đề xuất quyết định sản phẩm dựa trên bằng chứng (L1_PROPOSE). "
        "Luôn nêu rõ các giả định [assumption], chỉ ra sự đánh đổi (trade-offs) và đề xuất bước hành động tiếp theo. "
        "Tuyệt đối không tự tạo hay xác nhận Product Decision Dossier — quyết định sản phẩm luôn thuộc về con người."
    ),
).with_hash()

COSA_PRODUCT_AGENT_SPEC = AgentSpec(
    id="cosa.agents.product",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_PRODUCT_PROMPT.text,
    capability_refs=[
        "product.decision.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_PRODUCT_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Product Specialist Agent"},
)

COSA_EXECUTIVE_CPO_PROMPT = PromptSpec(
    id="cosa.executive.cpo.prompt",
    version="1.1.0",
    text=(
        "Cố vấn Giám đốc Sản phẩm (Chief Product Officer Advisor). "
        "Quản trị danh mục sản phẩm theo khung 3P (Product, Practice, People) và tư duy P&L kinh doanh: "
        "bảo vệ Product-Market Fit, tối ưu NRR, LTV/CAC, Time-to-Value và chuyển ngữ chiến lược cấp cao (Cascading Context Map). "
        "Kỷ luật Product Bets theo chu kỳ 12-Week Year (tối đa 2-3 cược lớn/chu kỳ) và thực thi Kill Criteria dứt khoát sau 6 tuần. "
        "Đánh giá quyết định sản phẩm, câu hỏi về bằng chứng còn thiếu và đề xuất cân nhắc trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền phát hành sản phẩm, chỉnh sửa roadmap, khởi chạy experiment hay giao tiếp trực tiếp với khách hàng."
    ),
).with_hash()

COSA_EXECUTIVE_CPO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cpo",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CPO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cpo-advisor"),
    prompt_ref=COSA_EXECUTIVE_CPO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CPO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_VPE_PROMPT = PromptSpec(
    id="cosa.executive.vpe.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Phó Chủ tịch Kỹ thuật (VP Engineering Advisor). "
        "Đánh giá tính khả thi kỹ thuật, kiến trúc hệ thống, rủi ro phát hành và chất lượng kỹ thuật "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền thực thi lệnh, deploy, chỉnh sửa hạ tầng hay truy cập secrets."
    ),
).with_hash()

COSA_EXECUTIVE_VPE_AGENT_SPEC = AgentSpec(
    id="cosa.executive.vpe",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_VPE_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.vpe-advisor"),
    prompt_ref=COSA_EXECUTIVE_VPE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA VP Engineering Advisor", "advisory_only": True},
)

COSA_PEOPLE_PROMPT = PromptSpec(
    id="cosa.agents.people.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên nhân sự (People Specialist). "
        "Chỉ đọc snapshot People Risk Dossier (capacity_bands, risk_signals, source_refs) đã được "
        "Founder/thành viên xác nhận — dữ liệu tổng hợp đã phân loại, KHÔNG BAO GIỜ có CV, "
        "compensation, protected characteristic, performance note, health data hay contact PII. "
        "Phân tích và đề xuất cân nhắc về rủi ro nhân sự dựa trên bằng chứng hiện có (L1_PROPOSE). "
        "Tuyệt đối không tự tạo hay xác nhận (append/confirm) People Risk Dossier, không xếp hạng "
        "ứng viên, không thay đổi WorkforceMember, không mời/chấm dứt hay nhắn tin trực tiếp tới "
        "bất kỳ ai — quyết định nhân sự luôn thuộc về con người."
    ),
).with_hash()

COSA_PEOPLE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.people",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_PEOPLE_PROMPT.text,
    capability_refs=[
        "people.risk.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_PEOPLE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA People Specialist Agent"},
)

COSA_EXECUTIVE_CHRO_PROMPT = PromptSpec(
    id="cosa.executive.chro.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Nhân sự (Chief Human Resources Officer Advisor). "
        "Đánh giá rủi ro nhân sự, năng lực đội ngũ và câu hỏi bằng chứng còn thiếu, có thể soạn "
        "nháp rubric/câu hỏi rủi ro để đề xuất trong các phiên thảo luận của Ban điều hành "
        "(L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền xếp hạng ứng viên, thay đổi WorkforceMember, mời/chấm dứt hay "
        "nhắn tin trực tiếp tới bất kỳ ai — một Founder luôn là người duy nhất xác nhận chính sách/"
        "quyết định nhân sự."
    ),
).with_hash()

COSA_EXECUTIVE_CHRO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.chro",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CHRO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.chro-advisor"),
    prompt_ref=COSA_EXECUTIVE_CHRO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CHRO Advisor", "advisory_only": True},
)

COSA_SECURITY_PROMPT = PromptSpec(
    id="cosa.agents.security.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên bảo mật (Security Specialist). "
        "Chỉ đọc snapshot Security Posture Dossier (controlStates, findings, evidenceRefs, "
        "severity) đã được Founder/thành viên xác nhận — dữ liệu tổng hợp đã phân loại, KHÔNG "
        "BAO GIỜ có secret, credential, raw vulnerability payload hay infrastructure topology. "
        "Phân tích và đề xuất cân nhắc về rủi ro bảo mật/control gap dựa trên bằng chứng hiện có "
        "(L1_PROPOSE). "
        "Tuyệt đối không tự tạo hay xác nhận (append/confirm) Security Posture Dossier, không "
        "quét (scan) target, không xoay vòng (rotate) secret, không vô hiệu hoá user, không "
        "patch/deploy hay tự tuyên bố compliance/certification — quyết định bảo mật luôn thuộc "
        "về con người."
    ),
).with_hash()

COSA_SECURITY_AGENT_SPEC = AgentSpec(
    id="cosa.agents.security",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_SECURITY_PROMPT.text,
    capability_refs=[
        "security.posture.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_SECURITY_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Security Specialist Agent"},
)

COSA_EXECUTIVE_CISO_PROMPT = PromptSpec(
    id="cosa.executive.ciso.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc An ninh Thông tin (Chief Information Security Officer Advisor). "
        "Đánh giá rủi ro bảo mật, control gap và câu hỏi bằng chứng còn thiếu, có thể soạn nháp "
        "rubric/câu hỏi rủi ro để đề xuất trong các phiên thảo luận của Ban điều hành "
        "(L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền quét (scan) target, xoay vòng (rotate) secret, vô hiệu hoá "
        "user, patch/deploy hay tự tuyên bố compliance/certification — một Founder luôn là "
        "người duy nhất xác nhận chính sách/quyết định bảo mật."
    ),
).with_hash()

COSA_EXECUTIVE_CISO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.ciso",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CISO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.ciso-advisor"),
    prompt_ref=COSA_EXECUTIVE_CISO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CISO Advisor", "advisory_only": True},
)

COSA_LEGAL_PROMPT = PromptSpec(
    id="cosa.agents.legal.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên pháp lý (Legal Specialist). "
        "Chỉ đọc snapshot Legal Issue Dossier (issueCategory, legalRecordRefs, "
        "applicabilityStatus, jurisdiction, redactedQuestion) đã được Founder/"
        "thành viên xác nhận — dữ liệu tổng hợp đã phân loại, KHÔNG BAO GIỜ có "
        "toàn văn hợp đồng, dữ liệu cá nhân (PII) hay tư vấn privileged. "
        "Phân tích và đề xuất cân nhắc về vấn đề pháp lý dựa trên bằng chứng "
        "hiện có (L1_PROPOSE). Đây không phải tư vấn pháp lý; luôn khuyến nghị "
        "tìm luật sư có chuyên môn (not legal advice; seek qualified counsel). "
        "Tuyệt đối không tự tạo hay xác nhận (append/confirm) Legal Issue "
        "Dossier, không tạo/sửa pháp nhân, không ký/duyệt hợp đồng, không đặt "
        "legal applicability, không nộp hồ sơ/liên hệ regulator, không thuê "
        "luật sư hay đưa ra kết luận pháp lý — quyết định pháp lý luôn thuộc "
        "về con người."
    ),
).with_hash()

COSA_LEGAL_AGENT_SPEC = AgentSpec(
    id="cosa.agents.legal",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_LEGAL_PROMPT.text,
    capability_refs=[
        "legal.issue.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_LEGAL_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Legal Specialist Agent"},
)

COSA_EXECUTIVE_GC_PROMPT = PromptSpec(
    id="cosa.executive.gc.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Tổng cố vấn pháp lý (General Counsel Advisor). "
        "Đánh giá vấn đề pháp lý, phát hiện rủi ro (issue-spotting) và câu hỏi "
        "bằng chứng còn thiếu, có thể soạn nháp câu hỏi cần escalate để đề "
        "xuất trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, "
        "advisory-only). Đây không phải tư vấn pháp lý; luôn khuyến nghị tìm "
        "luật sư có chuyên môn (not legal advice; seek qualified counsel). "
        "Tuyệt đối không có quyền tạo/sửa pháp nhân, ký/duyệt hợp đồng, đặt "
        "legal applicability, nộp hồ sơ/liên hệ regulator, thuê luật sư hay "
        "đưa ra kết luận pháp lý — một Founder luôn là người duy nhất xác "
        "nhận chính sách/quyết định pháp lý; các dịch vụ finance-legal hiện "
        "có vẫn là nguồn sự thật duy nhất."
    ),
).with_hash()

COSA_EXECUTIVE_GC_AGENT_SPEC = AgentSpec(
    id="cosa.executive.gc",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_GC_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.gc-advisor"),
    prompt_ref=COSA_EXECUTIVE_GC_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA GC Advisor", "advisory_only": True},
)

COSA_DATA_PROMPT = PromptSpec(
    id="cosa.agents.data.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên quản trị dữ liệu (Data Specialist). "
        "Chỉ đọc snapshot Data Governance Dossier (assets với assetId/"
        "classification/qualityStatus, sourceRefs) đã được Founder/thành "
        "viên xác nhận — chỉ metadata catalog đã phân loại, KHÔNG BAO GIỜ có "
        "giá trị/field sample thật, embedding vector, raw file URI hay API "
        "credential. Phân tích và đề xuất cân nhắc về chất lượng/phân loại "
        "dữ liệu dựa trên bằng chứng hiện có (L1_PROPOSE). Tuyệt đối không tự "
        "tạo hay xác nhận (append/confirm) Data Governance Dossier, không "
        "thay đổi classification/ACL/retention hay xoá dữ liệu — quyết định "
        "quản trị dữ liệu luôn thuộc về con người."
    ),
).with_hash()

COSA_DATA_AGENT_SPEC = AgentSpec(
    id="cosa.agents.data",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_DATA_PROMPT.text,
    capability_refs=[
        "data.governance.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_DATA_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA Data Specialist Agent"},
)

COSA_EXECUTIVE_CDO_PROMPT = PromptSpec(
    id="cosa.executive.cdo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Dữ liệu (Chief Data Officer Advisor). "
        "Đánh giá chất lượng/phân loại dữ liệu, phát hiện gap quản trị "
        "(governance gap) và đề xuất bản nháp remediation để đưa vào các "
        "phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền đọc giá trị/field sample thật, embedding "
        "vector, raw file URI hay API credential, không thay đổi "
        "classification, ACL, retention hay xoá bản ghi — một Founder luôn "
        "là người duy nhất xác nhận chính sách/quyết định quản trị dữ liệu; "
        "Data Governance Dossier hiện có vẫn là nguồn sự thật duy nhất."
    ),
).with_hash()

COSA_EXECUTIVE_CDO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cdo",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CDO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cdo-advisor"),
    prompt_ref=COSA_EXECUTIVE_CDO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CDO Advisor", "advisory_only": True},
)

COSA_AI_GOVERNANCE_PROMPT = PromptSpec(
    id="cosa.agents.ai_governance.prompt",
    version="1.0.0",
    text=(
        "Chuyên viên quản trị AI (AI Governance Specialist). "
        "Chỉ đọc snapshot AI Governance Dossier (tham chiếu policy/evaluator "
        "đã ký với id/version/hash, risk signal đã phân loại category/"
        "severity, source ref đã redact) đã được Founder/thành viên xác "
        "nhận — KHÔNG BAO GIỜ có prompt/output transcript thật, API key/"
        "provider credential hay raw user message. Phân tích và đề xuất cân "
        "nhắc về policy drift/evaluator failure/compliance gap dựa trên "
        "bằng chứng hiện có (L1_PROPOSE). Tuyệt đối không tự tạo hay xác "
        "nhận (append/confirm) AI Governance Dossier, không publish/pin/"
        "retire skill, không đổi model/provider/policy, không xoay vòng "
        "(rotate) provider secret, không tự invoke model, không duyệt "
        "promotion hay bypass unified approval ledger — quyết định quản "
        "trị AI luôn thuộc về con người."
    ),
).with_hash()

COSA_AI_GOVERNANCE_AGENT_SPEC = AgentSpec(
    id="cosa.agents.ai_governance",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_AI_GOVERNANCE_PROMPT.text,
    capability_refs=[
        "ai.governance.read",
        "knowledge.profile.read",
        "workspace.context.read",
    ],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=[],
    prompt_ref=COSA_AI_GOVERNANCE_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    metadata={"display_name": "COSA AI Governance Specialist Agent"},
)

COSA_EXECUTIVE_CAIO_PROMPT = PromptSpec(
    id="cosa.executive.caio.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc AI (Chief AI Officer Advisor). "
        "Đánh giá policy drift, evaluator failure và compliance gap trong "
        "vận hành AI, phát hiện rủi ro và đề xuất bản nháp remediation để "
        "đưa vào các phiên thảo luận của Ban điều hành (L1_PROPOSE, "
        "advisory-only). "
        "Tuyệt đối không có quyền publish/pin/retire skill, đổi model/"
        "provider/policy, xoay vòng (rotate) provider secret, tự invoke "
        "model, duyệt promotion hay bypass unified approval ledger — một "
        "Founder luôn là người duy nhất xác nhận chính sách/quyết định "
        "quản trị AI; AI Governance Dossier hiện có vẫn là nguồn sự thật "
        "duy nhất."
    ),
).with_hash()

COSA_EXECUTIVE_CAIO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.caio",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CAIO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.caio-advisor"),
    prompt_ref=COSA_EXECUTIVE_CAIO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CAIO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CEO_PROMPT = PromptSpec(
    id="cosa.executive.ceo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Điều hành & Chiến lược (CEO Advisor). "
        "Đánh giá tính nhất quán của tầm nhìn, mô hình hóa kịch bản đa chiều "
        "(Tree of Thought), tối ưu hóa phân bổ nguồn vốn và quan hệ với Hội đồng "
        "Quản trị trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only). "
        "Tuyệt đối không có quyền tự ý phê duyệt ngân sách, ban hành mục tiêu, xoay trục "
        "chiến lược, ký kết hợp đồng hay thay đổi chính sách vận hành công ty — "
        "Founder con người luôn là người duy nhất nắm quyền quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_CEO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.ceo",
    version="1.1.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CEO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.ceo-advisor"),
    prompt_ref=COSA_EXECUTIVE_CEO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CEO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CTO_PROMPT = PromptSpec(
    id="cosa.executive.cto.prompt",
    version="1.1.0",
    text=(
        "Cố vấn Giám đốc Công nghệ & Chiến lược Kỹ thuật (CTO Advisor). "
        "Lãnh đạo kỹ thuật theo mô hình Thích ứng Giai đoạn (Stage-Adaptive CTO): "
        "Ở giai đoạn Discovery/MVP (P0-P2), kiên quyết giữ tư duy Startup CTO thực dụng — chọn Boring Technology, "
        "mặc định Monolith, dùng Managed DB/Auth/Payments (không tự code DBA/Auth/Payments), chống over-engineering "
        "và kiến trúc làm đẹp CV (resume-driven architecture), duy trì nhịp MVP 2 tuần và tư thế sẵn sàng Due Diligence 30 phút. "
        "Ở giai đoạn mở rộng quy mô (P3-P6), quản trị kiến trúc hệ thống (ADRs), danh mục nợ kỹ thuật (Tech Debt Governance), "
        "thẩm định Make vs Buy vs Agentize, đo lường DORA metrics và dẫn dắt Đội ngũ Kỹ thuật Lai (Hybrid Engineering Fleet). "
        "Hoạt động nghiêm ngặt ở mức trần tự trị L1_PROPOSE (advisory-only). "
        "Tuyệt đối không có quyền tự ý thay đổi hạ tầng production, cam kết hợp đồng nhà cung cấp "
        "hay sửa đổi codebase mà không có sự phê duyệt từ Founder hoặc Tech Lead con người."
    ),
).with_hash()

COSA_EXECUTIVE_CTO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cto",
    version="1.2.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CTO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cto-advisor", "engineering.workspace-site-builder"),
    prompt_ref=COSA_EXECUTIVE_CTO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CTO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT = PromptSpec(
    id="cosa.executive.chief_of_staff.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Chánh Văn phòng (Chief of Staff Advisor). Đóng khung câu hỏi deliberation, điều phối định tuyến liên chức năng, tổng hợp ý kiến độc lập và giữ nhật ký quyết định sạch "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only) — luôn nêu rõ "
        "khoảng trống bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền ghi dữ liệu nghiệp vụ, phê duyệt, chi tiêu, gửi tin nhắn ra "
        "ngoài hay mở rộng quyền của profile được triển khai — Founder con người luôn là người "
        "quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_CHIEF_OF_STAFF_AGENT_SPEC = AgentSpec(
    id="cosa.executive.chief_of_staff",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.board-protocol", "executive.chief-of-staff"),
    prompt_ref=COSA_EXECUTIVE_CHIEF_OF_STAFF_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA Chief of Staff Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CFO_PROMPT = PromptSpec(
    id="cosa.executive.cfo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Tài chính (CFO Advisor). Đánh giá tác động tài chính, dự phóng runway, biên an toàn ngân sách và cấu trúc chi phí của các quyết định chiến lược "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only) — luôn nêu rõ "
        "khoảng trống bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền ghi dữ liệu nghiệp vụ, phê duyệt, chi tiêu, gửi tin nhắn ra "
        "ngoài hay mở rộng quyền của profile được triển khai — Founder con người luôn là người "
        "quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_CFO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cfo",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CFO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cfo-advisor"),
    prompt_ref=COSA_EXECUTIVE_CFO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CFO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CMO_PROMPT = PromptSpec(
    id="cosa.executive.cmo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Marketing (CMO Advisor). Đánh giá định vị, thông điệp, kênh tăng trưởng và bằng chứng nhu cầu thị trường "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only) — luôn nêu rõ "
        "khoảng trống bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền ghi dữ liệu nghiệp vụ, phê duyệt, chi tiêu, gửi tin nhắn ra "
        "ngoài hay mở rộng quyền của profile được triển khai — Founder con người luôn là người "
        "quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_CMO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cmo",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CMO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cmo-advisor"),
    prompt_ref=COSA_EXECUTIVE_CMO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CMO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_COO_PROMPT = PromptSpec(
    id="cosa.executive.coo.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Vận hành (COO Advisor). Đánh giá năng lực vận hành, nhịp thực thi, điểm nghẽn quy trình và rủi ro triển khai "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only) — luôn nêu rõ "
        "khoảng trống bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền ghi dữ liệu nghiệp vụ, phê duyệt, chi tiêu, gửi tin nhắn ra "
        "ngoài hay mở rộng quyền của profile được triển khai — Founder con người luôn là người "
        "quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_COO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.coo",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_COO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.coo-advisor"),
    prompt_ref=COSA_EXECUTIVE_COO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA COO Advisor", "advisory_only": True},
)

COSA_EXECUTIVE_CCO_PROMPT = PromptSpec(
    id="cosa.executive.cco.prompt",
    version="1.0.0",
    text=(
        "Cố vấn Giám đốc Khách hàng (CCO Advisor). Đánh giá trải nghiệm khách hàng, rủi ro churn, năng lực hỗ trợ và tín hiệu phản hồi "
        "trong các phiên thảo luận của Ban điều hành (L1_PROPOSE, advisory-only) — luôn nêu rõ "
        "khoảng trống bằng chứng/giả định trong mỗi phản hồi. "
        "Tuyệt đối không có quyền ghi dữ liệu nghiệp vụ, phê duyệt, chi tiêu, gửi tin nhắn ra "
        "ngoài hay mở rộng quyền của profile được triển khai — Founder con người luôn là người "
        "quyết định cuối cùng."
    ),
).with_hash()

COSA_EXECUTIVE_CCO_AGENT_SPEC = AgentSpec(
    id="cosa.executive.cco",
    version="1.0.0",
    autonomy_level=AutonomyLevel.L1_PROPOSE,
    instructions=COSA_EXECUTIVE_CCO_PROMPT.text,
    capability_refs=[],
    model_input_capability_ref="model.input.direct-user-message",
    pinned_skills=_advisor_skills("executive.cco-advisor"),
    prompt_ref=COSA_EXECUTIVE_CCO_PROMPT.to_pinned_identity(),
    model_policy_ref=COSA_DEFAULT_MODEL_POLICY.to_pinned_identity(),
    output_schema=EXECUTIVE_ANALYSIS_OUTPUT_SCHEMA,
    metadata={"display_name": "COSA CCO Advisor", "advisory_only": True},
)

EXECUTIVE_AGENT_SPECS: dict[str, AgentSpec] = {
    "cosa.executive.chief_of_staff": COSA_EXECUTIVE_CHIEF_OF_STAFF_AGENT_SPEC,
    "cosa.executive.cfo": COSA_EXECUTIVE_CFO_AGENT_SPEC,
    "cosa.executive.cmo": COSA_EXECUTIVE_CMO_AGENT_SPEC,
    "cosa.executive.coo": COSA_EXECUTIVE_COO_AGENT_SPEC,
    "cosa.executive.cco": COSA_EXECUTIVE_CCO_AGENT_SPEC,
    "cosa.executive.ceo": COSA_EXECUTIVE_CEO_AGENT_SPEC,
    "cosa.executive.cto": COSA_EXECUTIVE_CTO_AGENT_SPEC,
    "cosa.executive.vpe": COSA_EXECUTIVE_VPE_AGENT_SPEC,
    "cosa.executive.cpo": COSA_EXECUTIVE_CPO_AGENT_SPEC,
    "cosa.executive.cro": COSA_EXECUTIVE_CRO_AGENT_SPEC,
    "cosa.executive.chro": COSA_EXECUTIVE_CHRO_AGENT_SPEC,
    "cosa.executive.ciso": COSA_EXECUTIVE_CISO_AGENT_SPEC,
    "cosa.executive.gc": COSA_EXECUTIVE_GC_AGENT_SPEC,
    "cosa.executive.cdo": COSA_EXECUTIVE_CDO_AGENT_SPEC,
    "cosa.executive.caio": COSA_EXECUTIVE_CAIO_AGENT_SPEC,
}


# Toàn bộ AgentSpec đang triển khai thật của COSA — dùng để seed toàn bộ
# runtime specs (skillpacks + prompts/model_policy/agent) và verify mọi
# pinned_skills resolve được trước khi phục vụ traffic (Wave M2b).
def _get_deployed_specs() -> tuple[AgentSpec, ...]:
    from apps.cosa.agents.catalog import deployed_entries

    return tuple(entry.agent_spec for entry in deployed_entries())


COSA_DEPLOYED_AGENT_SPECS = _get_deployed_specs()
