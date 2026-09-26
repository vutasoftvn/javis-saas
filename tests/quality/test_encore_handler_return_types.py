"""Gate: mọi handler Encore (`api(...)`) phải khai báo kiểu trả về tường minh.

Encore dựng schema response lúc biên dịch từ annotation trên chữ ký hàm, không
suy luận từ thân hàm. Handler thiếu `: Promise<...>` vẫn chạy và test gọi
handler trong process vẫn pass, nhưng qua HTTP thật nó trả 200 với body rỗng —
lỗi thật đã xảy ra: toàn bộ panel "Mục tiêu & Ngữ cảnh" (Startup OS) báo
"Unexpected end of input" và E2E test_startup_os_http.py đỏ.

`KNOWN_UNANNOTATED` là nợ kỹ thuật có sẵn khi thêm gate (chưa có consumer
Flutter nào gọi qua HTTP). Không được thêm mục mới; sửa handler thì xoá mục
tương ứng (test fail nếu baseline còn mục đã được sửa, để baseline không mục).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

KNOWN_UNANNOTATED = frozenset(
    {
        ("services/cosa/handlers/document-ingestion.handler.ts", "POST", "/cosa/document-ingestions"),
        ("services/cosa/handlers/document-ingestion.handler.ts", "GET", "/cosa/document-ingestions/:ingestionId"),
        ("services/cosa/handlers/document-ingestion.handler.ts", "POST", "/cosa/document-ingestions/:ingestionId/transition"),
        ("services/cosa/handlers/document-ingestion.handler.ts", "POST", "/cosa/document-ingestions/:ingestionId/review"),
        ("services/cosa/handlers/document-ingestion.handler.ts", "POST", "/cosa/document-ingestions/:ingestionId/complete"),
        ("services/cosa/handlers/control-plane.handler.ts", "GET", "/control-plane/internal/missions/:id"),
        ("services/cosa/handlers/control-plane.handler.ts", "POST", "/control-plane/internal/tasks/:taskId/checkout"),
        ("services/cosa/handlers/workspace-connector.handler.ts", "POST", "/cosa/connectors/revoke"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "GET", "/commercial/engagement/threads/:id"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "GET", "/commercial/engagement/threads"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/status"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/notes"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/messages"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/assign"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/takeover"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/threads/:id/hand-back"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "GET", "/commercial/engagement/contacts/:id/360"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "PUT", "/commercial/engagement/escalation-routes/:routeKey"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-authorities"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-authorities/:authorityKey/grants"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-requests"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-requests/:id/submit"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-requests/:id/review"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-requests/:id/approvals"),
        ("services/company/commercial/handlers/customer-engagement/desk.handler.ts", "POST", "/commercial/engagement/decision-requests/:id/execute"),
        ("services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts", "POST", "/commercial/engagement/channels"),
        ("services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts", "POST", "/commercial/engagement/channels/:id/activate"),
        ("services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts", "POST", "/commercial/engagement/channels/:id/pause"),
        ("services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts", "GET", "/commercial/engagement/channels/:id/deliveries"),
        ("services/company/commercial/handlers/customer-engagement/channel-admin.handler.ts", "POST", "/commercial/engagement/deliveries/:id/retry"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "POST", "/commercial/engagement/automation/rules"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "POST", "/commercial/engagement/automation/rules/:key/enable"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "POST", "/commercial/engagement/automation/rules/:key/disable"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "GET", "/commercial/engagement/automation/rules"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "POST", "/commercial/engagement/threads/:id/automation/dry-run"),
        ("services/company/commercial/handlers/customer-engagement/automation.handler.ts", "GET", "/commercial/engagement/threads/:id/automation/applications"),
        ("services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts", "POST", "/finance-legal/ai-compliance/snapshots"),
        ("services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts", "GET", "/finance-legal/ai-compliance/snapshots"),
        ("services/company/finance-legal/handlers/ai-compliance-snapshot.handler.ts", "POST", "/finance-legal/ai-compliance/snapshots/:id/verify"),
        ("services/company/finance-legal/handlers/ai-incident-response.handler.ts", "POST", "/finance-legal/ai-compliance/incidents"),
        ("services/company/finance-legal/handlers/ai-incident-response.handler.ts", "POST", "/finance-legal/ai-compliance/incidents/:id/resolve"),
        ("services/company/finance-legal/handlers/ai-compliance-governance.handler.ts", "POST", "/finance-legal/ai-compliance/deployments"),
        ("services/company/finance-legal/handlers/ai-compliance-governance.handler.ts", "POST", "/finance-legal/ai-compliance/deployments/:deploymentId/assessments"),
        ("services/company/finance-legal/handlers/ai-compliance-governance.handler.ts", "POST", "/finance-legal/ai-compliance/deployments/:deploymentId/approve"),
        ("services/company/finance-legal/handlers/ai-compliance-governance.handler.ts", "POST", "/finance-legal/ai-compliance/deployments/:deploymentId/suspend"),
        ("services/company/finance-legal/handlers/ai-compliance-governance.handler.ts", "POST", "/finance-legal/ai-compliance/deployments/:deploymentId/resume"),
        ("services/company/finance-legal/handlers/ai-data-governance.handler.ts", "POST", "/finance-legal/ai-compliance/provider-profiles"),
        ("services/company/finance-legal/handlers/ai-data-governance.handler.ts", "POST", "/finance-legal/ai-compliance/data-profiles"),
        ("services/company/finance-legal/handlers/ai-data-governance.handler.ts", "POST", "/finance-legal/ai-compliance/authorizations"),
        ("services/company/finance-legal/handlers/ai-data-governance.handler.ts", "POST", "/finance-legal/ai-compliance/authorizations/:id/withdraw"),
        ("services/company/finance-legal/handlers/ai-data-governance.handler.ts", "POST", "/finance-legal/ai-compliance/data-subject-requests"),
        ("services/company/operations/handlers/twelve-week-year.handler.ts", "GET", "/operations/twelve-week-cycles"),
        ("services/company/operations/handlers/twelve-week-year.handler.ts", "GET", "/operations/twelve-week-plans"),
        ("services/company/operations/handlers/twelve-week-year.handler.ts", "GET", "/operations/twelve-week-commitments"),
        ("services/company/operations/strategy/handlers/experiment.handler.ts", "GET", "/operations/strategy/projects/:projectId/proposed-experiments"),
    }
)

_API_START = re.compile(r"=\s*api\(\s*\{([^}]*)\}\s*,\s*async\s*\(")


def _unannotated_handlers() -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for path in sorted(ROOT.glob("services/*/**/*.ts")):
        rel = path.relative_to(ROOT).as_posix()
        if "node_modules" in rel or "/tests/" in rel or rel.endswith(".test.ts"):
            continue
        source = path.read_text(encoding="utf-8")
        for match in _API_START.finditer(source):
            # Bỏ qua danh sách tham số (cân ngoặc), rồi xem đoạn trước `=>`.
            i, depth = match.end(), 1
            while depth and i < len(source):
                depth += {"(": 1, ")": -1}.get(source[i], 0)
                i += 1
            signature_tail = source[i : source.find("=>", i)]
            if "Promise<" in signature_tail:
                continue
            options = match.group(1)
            method = re.search(r'method:\s*"([^"]+)"', options)
            route = re.search(r'path:\s*"([^"]+)"', options)
            found.add((rel, method.group(1) if method else "?", route.group(1) if route else "?"))
    return found


def test_new_encore_handlers_declare_their_response_type() -> None:
    new_offenders = sorted(_unannotated_handlers() - KNOWN_UNANNOTATED)
    assert not new_offenders, (
        "Handler Encore thiếu kiểu trả về tường minh `: Promise<...>` "
        "(HTTP sẽ trả body rỗng):\n" + "\n".join(" ".join(o) for o in new_offenders)
    )


def test_known_unannotated_baseline_has_no_stale_entries() -> None:
    stale = sorted(KNOWN_UNANNOTATED - _unannotated_handlers())
    assert not stale, "Đã sửa — xoá khỏi KNOWN_UNANNOTATED:\n" + "\n".join(" ".join(o) for o in stale)


def test_startup_os_handlers_behind_flutter_panel_are_annotated() -> None:
    offenders = {
        o
        for o in _unannotated_handlers()
        if o[0].endswith(("goals.handler.ts", "onboard.handler.ts", "okr.handler.ts"))
    }
    assert not offenders
