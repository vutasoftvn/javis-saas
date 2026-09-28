"""Bảng bậc hành động cho mọi capability của agent (spec 2026-09-27-chat-business-actions).

T0 đọc | T1 nháp/hoàn tác được, không tác động ngoài | T2 ghi thật vào dữ liệu nội bộ
(chat buộc founder duyệt) | T3 ra ngoài/không hoàn tác (không mở cho agent chat).

`company_agent_cap` là id trong services/company/shared/auth/agent-capabilities.ts mà endpoint
company chấp nhận qua delegation token; None = capability không gọi company bằng token agent.
Ba test parity (tests/apps/cosa/test_access_matrix_parity.py) đối chiếu bảng này với spec agent,
registry capability và file AGENT_CAP của company để lệch pha bị CI bắt thay vì lộ ở runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from apps.cosa.capabilities.domain_draft import DOMAIN_DRAFT_SPECS

__all__ = ["CHAT_T2_CAPABILITIES", "MATRIX", "AccessEntry", "Tier"]


class Tier(StrEnum):
    T0_READ = "T0"
    T1_DRAFT = "T1"
    T2_COMMIT = "T2"
    T3_EXTERNAL = "T3"


@dataclass(frozen=True)
class AccessEntry:
    tier: Tier
    domain: str
    company_agent_cap: str | None = None


def _r(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T0_READ, domain, cap)


def _d(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T1_DRAFT, domain, cap)


def _c(domain: str, cap: str | None = None) -> AccessEntry:
    return AccessEntry(Tier.T2_COMMIT, domain, cap)


def _x(domain: str) -> AccessEntry:
    return AccessEntry(Tier.T3_EXTERNAL, domain)


MATRIX: dict[str, AccessEntry] = {
    # --- operations
    "operations.task.list": _r("operations", "operations.task.list"),
    "operations.task.read": _r("operations", "operations.task.read"),
    "operations.execution_plan.read": _r("operations", "operations.execution_plan.read"),
    "operations.task.create_draft": _d("operations", "operations.task.create_draft"),
    "operations.task.advance": _c("operations", "operations.task.advance"),
    # --- strategy / lifecycle
    "strategy.project.get": _r("strategy", "strategy.project.get"),
    "strategy.next_best_action.get": _r("strategy", "strategy.next_best_action.get"),
    "strategy.evidence.list": _r("strategy", "strategy.evidence.list"),
    "strategy.evidence.create": _d("strategy", "strategy.evidence.create"),
    "strategy.pilot.get": _r("strategy", "strategy.pilot.get"),
    "strategy.pilot.create_draft": _d("strategy", "strategy.pilot.create_draft"),
    "analytics.metric_contract.get": _r("strategy", "analytics.metric_contract.get"),
    # --- goals / OKR
    "startup_os.goal.tree_read": _r("goals", "startup_os.goal.tree_read"),
    "startup_os.goal.needing_review": _r("goals", "startup_os.goal.needing_review"),
    "startup_os.goal.advisory": _r("goals", "startup_os.goal.advisory"),
    "startup_os.goal.create": _c("goals", "startup_os.goal.create"),
    "startup_os.project.triage": _c("goals", "startup_os.project.triage"),
    "okr.objective.list": _r("okr", "okr.objective.list"),
    "okr.key_result.create": _c("okr", "okr.key_result.create"),
    "okr.key_result.checkin": _c("okr", "okr.key_result.checkin"),
    "okr.key_result.update": _c("okr", "okr.key_result.update"),
    # --- onboarding
    "startup_os.onboard.context_read": _r("onboard", "startup_os.onboard.context_read"),
    "startup_os.onboard.cadence_status": _r("onboard", "startup_os.onboard.cadence_status"),
    "startup_os.onboard.cadence_advisory": _r("onboard", "startup_os.onboard.cadence_advisory"),
    "startup_os.onboard.interview_plan": _r("onboard"),
    "startup_os.onboard.session_start": _d("onboard", "startup_os.onboard.session_start"),
    "startup_os.onboard.dimension_update": _d("onboard", "startup_os.onboard.dimension_update"),
    "startup_os.onboard.snapshot_create": _d("onboard", "startup_os.onboard.snapshot_create"),
    # --- finance
    "finance.connection.read": _r("finance", "finance.connection.read"),
    "finance.transaction.read": _r("finance", "finance.transaction.read"),
    "finance.transaction.classify_propose": _d("finance", "finance.transaction.classify_propose"),
    "finance.accounting_document.create_draft": _d(
        "finance", "finance.accounting_document.create_draft"
    ),
    # Câu hỏi mở §8.3 của spec (hạn mức) chưa chốt: T2 nhưng CHƯA đưa vào spec chat.
    "finance.transaction.record": _c("finance", "finance.transaction.record"),
    "finance.accounting_document.confirm": _x("finance"),
    # --- commercial / CRM / customer
    "project.crm.read": _r("crm", "project.crm.read"),
    "commercial.customer_360.read": _r("customer", "commercial.customer_360.read"),
    "commercial.marketing_context.read": _r("marketing", "commercial.marketing_context.read"),
    "commercial.marketing_context.write": _c("marketing"),
    "commercial.campaign_asset.write": _d("marketing"),
    "commercial.experiment.write": _c("marketing"),
    "engagement.thread.read": _r("customer", "engagement.thread.read"),
    "engagement.message.draft": _d("customer"),
    "engagement.assignment.write": _c("customer"),
    "engagement.message.send": _x("customer"),
    # --- thông báo cho chính founder (ADR-FOUNDER-CHANNEL-001): T2-self, KHÔNG phải mở T3 —
    # không có tham số người nhận, đích luôn là kênh founder tự cấu hình và đã xác minh.
    "founder.notify.send": _c("founder", "founder.notify.send"),
    # --- email của founder (plan hub đợt 2 B3): T0 đọc metadata qua grant connector `email-read`;
    # gọi Gmail bằng token của grant, không gọi company bằng token agent ⇒ không có AGENT_CAP.
    "email.digest.read": _r("email"),
    # --- tự động hoá (plan hub đợt 2 B4): T1 chứ không T2 như plan ghi — chỉ lưu NHÁP kế hoạch ở
    # company (không tạo lịch, không gọi ra ngoài); founder duyệt ở thẻ kế hoạch (B6) rồi B5 mới
    # tạo lịch. Để T2 thì chat bắt founder duyệt hai lần (thẻ duyệt T2 rồi thẻ kế hoạch).
    "automation.plan.propose": _d("automation", "automation.plan.propose"),
    # --- legal / people / product / security / data / ai governance
    "legal.issue.read": _r("legal", "legal.issue.read"),
    "legal.applicability.assess": _r("legal"),
    "legal.obligation.create_draft": _d("legal", "legal.obligation.create_draft"),
    "people.risk.read": _r("people", "people.risk.read"),
    "product.decision.read": _r("product", "product.decision.read"),
    "security.posture.read": _r("security", "security.posture.read"),
    "data.governance.read": _r("data", "data.governance.read"),
    "ai.governance.read": _r("ai_governance", "ai.governance.read"),
    "engineering.evidence.read": _r("engineering"),
    # --- venture / knowledge / web / workspace
    "venture.profile.read": _r("venture", "venture.profile.read"),
    # Tên "propose" nhưng PUT ghi đè hồ sơ thật ⇒ T2 (founder duyệt trong chat).
    "venture.profile.propose_update": _c("venture", "venture.profile.propose_update"),
    "knowledge.profile.read": _r("knowledge"),
    "knowledge.enterprise.read": _r("knowledge"),
    "web.search": _r("web"),
    "workspace.context.read": _r("workspace"),
    # --- capability nội bộ của apps/cosa (đăng ký động, không gọi company bằng token agent)
    "agent.consult": _r("agents"),
    "memory.fact.propose": _d("memory"),
    # --- đọc mọi domain qua một cửa (spec 2026-09-27 §4.2)
    "business.read": _r("business"),
    # --- nháp theo domain (G-5): không side-effect, không gọi company
    **{spec.id: _d(spec.id.split(".", 1)[0]) for spec in DOMAIN_DRAFT_SPECS},
}

# T2 buộc founder duyệt trong chat run (worker/handlers.py gắn vào metadata run).
CHAT_T2_CAPABILITIES: frozenset[str] = frozenset(
    cap for cap, entry in MATRIX.items() if entry.tier is Tier.T2_COMMIT
)
