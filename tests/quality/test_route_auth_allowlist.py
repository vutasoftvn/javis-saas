import re
from pathlib import Path
from scripts.route_inventory import collect_handlers

ROOT = Path(__file__).resolve().parents[2]

# Danh sách cho phép (allowlist) 9 endpoint expose:true && auth:false đã được audit:
# 1. /healthz (company): Probe kiểm tra sức khỏe hệ thống (load balancer / k8s probe)
# 2. /healthz (cosa): Probe kiểm tra sức khỏe hệ thống (load balancer / k8s probe)
# 3. /platform/auth/sessions (cosa): Đăng nhập platform (trước khi có token)
# 4. /platform/auth/register (cosa): Đăng ký tài khoản platform mới (trước khi có token)
# 5. /identity/session/renew (company): Gia hạn phiên làm việc local bằng token hiện có
# 6. /identity/sync-from-platform (company): Đồng bộ dữ liệu workspace ban đầu từ platform
# 7. /platform/internal/list-workspace-memberships (cosa): RPC nội bộ giữa các service (xác thực token/signature thủ công)
# 8. /platform/internal/validate-workspace-membership (cosa): RPC nội bộ giữa các service (xác thực token/signature thủ công)
# 9. /platform/internal/mark-workspace-synced (cosa): RPC nội bộ giữa các service (xác thực token/signature thủ công)
EXPLICIT_UNAUTHENTICATED_ALLOWLIST = {
    ("company", "GET", "/healthz"),
    ("cosa", "GET", "/healthz"),
    ("company", "POST", "/identity/session/renew"),
    ("company", "POST", "/identity/sync-from-platform"),
    ("cosa", "POST", "/platform/internal/list-workspace-memberships"),
    ("cosa", "POST", "/platform/internal/validate-workspace-membership"),
    ("cosa", "POST", "/platform/internal/mark-workspace-synced"),
    # Cutover COSA sang backend/core: services/company (app Encore riêng) hỏi danh tính của người giữ token
    # (JWT platform cũ hoặc access token OIDC của core). Handler tự xác thực token trong body
    # (resolveCallerIdentity -> introspect với core), giống validate-workspace-membership.
    ("cosa", "POST", "/platform/internal/resolve-identity"),
    # B5 (ADR-COSA-DELEGATION-002): Encore auth handler chỉ nhận access token của core,
    # nhưng caller (apps/cosa) mang control-plane delegation token ký bởi
    # COSA_CONTROL_DELEGATION_SECRET — 2 secret khác nhau nên auth built-in
    # luôn 403. Handler tự verify thủ công qua resolveCallerAuthorizedForWorkspace
    # (control-plane delegation, fallback platform token + verifyWorkspaceMembership)
    # rồi mới build snapshot. auth:false có chủ đích, đã kiểm tra.
    ("cosa", "GET", "/platform/auth/me/agent-policy-snapshot"),
    # Task 1 (vi-en-localization): Caller (apps/cosa) mang control-plane delegation
    # token để lấy preferred_locale snapshot. Handler tự verify qua
    # resolveCallerAuthorizedForWorkspace. auth:false có chủ đích, đã kiểm tra.
    ("cosa", "GET", "/platform/auth/me/locale-snapshot"),
    # Task 1 (caio-ai-governance-profile-and-executive-activation): Caller
    # (apps/cosa, Python, ngoài Encore) mang control-plane delegation token để
    # ký ai-governance-snapshot envelope. Handler tự verify token thủ công qua
    # verifyControlDelegationToken (ai-governance-snapshot.service.ts) — cùng
    # pattern B5 ở trên, khác secret (Gateway chỉ hiểu access token của core, không hiểu
    # được token này). auth:false có chủ đích, đã kiểm tra.
    ("cosa", "POST", "/cosa/ai-governance/snapshot"),
    # Advisor overlay lookup (2026-09-20): services/company là Encore app riêng nên gọi qua
    # HTTP thật, không dùng được `expose:false`. Handler tự verify service token
    # (COSA_ADVISOR_OVERLAY_SERVICE_SECRET — Company ký, COSA verify, một chiều) qua
    # verifyAdvisorOverlayServiceToken; endpoint chỉ đọc catalog overlay đã publish, không
    # mutate. auth:false ở Gateway có chủ đích, đã kiểm tra.
    ("cosa", "GET", "/platform/internal/executive-advisor-overlay"),
}


def test_every_unauthenticated_expose_endpoint_is_allowlisted() -> None:
    handlers = collect_handlers()
    unauthenticated_exposed = {
        (h["service"], h["method"], h["path"])
        for h in handlers
        if h["expose"] and h.get("explicit_auth_false")
    }

    unexpected = unauthenticated_exposed - EXPLICIT_UNAUTHENTICATED_ALLOWLIST
    assert not unexpected, (
        f"New unauthenticated exposed endpoint(s) detected without audit approval: {unexpected}. "
        "Every endpoint with expose:true && auth:false must be audited and added to EXPLICIT_UNAUTHENTICATED_ALLOWLIST with rationale."
    )

    stale = EXPLICIT_UNAUTHENTICATED_ALLOWLIST - unauthenticated_exposed
    assert not stale, (
        f"Stale entry in EXPLICIT_UNAUTHENTICATED_ALLOWLIST: {stale}. "
        "Remove entries that are no longer unauthenticated exposed routes."
    )


def test_allowlist_gate_rejects_unauthorized_route() -> None:
    fake_handlers = [
        {"service": "company", "method": "POST", "path": "/commercial/evil-open-route", "expose": True, "explicit_auth_false": True}
    ]
    unauthenticated_exposed = {
        (h["service"], h["method"], h["path"])
        for h in fake_handlers
        if h["expose"] and h.get("explicit_auth_false")
    }
    unexpected = unauthenticated_exposed - EXPLICIT_UNAUTHENTICATED_ALLOWLIST
    assert unexpected == {("company", "POST", "/commercial/evil-open-route")}


# ---------------------------------------------------------------------------
# Gate thứ hai: endpoint `expose: true` KHÔNG khai báo `auth` (Encore mặc định
# auth:false) nhưng handler quên gọi guard. Gate ở trên chỉ bắt `auth: false`
# tường minh nên từng lọt các endpoint Startup OS (goals/OKR/onboard) và
# GET /operations/workspaces/:workspaceId/cycles — ai cũng đọc/ghi được dữ
# liệu workspace bất kỳ.
#
# Quy tắc: thân handler phải nhắc tới Authorization/serviceToken hoặc một
# hàm guard. Handler chuyển nguyên params (đã có authorization trong
# interface) sang service tự guard thì không nhìn thấy được bằng quét tĩnh —
# các endpoint đó đã được soát tay (2026-09-25) và liệt kê bên dưới.
# ---------------------------------------------------------------------------

_GUARD_PATTERN = re.compile(
    r"authorization|serviceToken|requireWorker|verify\w*\(|resolveCosaTaskContext|"
    r"requireWorkspace|requireOrganization|workspaceContext\(|signature|webhook|hmac|"
    r"timingSafeEqual|requireInternal|requireFounder|getAuthData|resolveCaller|"
    r"extractAuthContext|requireService|requireAgent|assertService|internalToken|authHeader",
    re.IGNORECASE,
)
_API_BLOCK = re.compile(r"api(?:\.raw)?\(\s*\{([^}]*)\}", re.DOTALL)

# (service, method, path) -> nơi guard thực sự nằm.
SERVICE_GUARDED_ALLOWLIST = {
    # Service tự requireWorkspaceAccess(params.authorization, ...).
    ("company", "DELETE", "/operations/key-results/:id"): "okr.service deleteKeyResultService",
    ("company", "PUT", "/operations/key-results/:id"): "okr.service updateKeyResultService",
    ("company", "PUT", "/operations/objectives/:id"): "okr.service updateObjectiveService",
    ("company", "POST", "/operations/objectives"): "okr.service createObjectiveService",
    ("company", "POST", "/operations/objectives/:objectiveId/key-results"): "okr.service addKeyResultService",
    ("company", "POST", "/operations/okr-cycles"): "okr.service createOkrCycleService",
    ("company", "GET", "/events/metrics"): "event-metrics.service getEventMetrics",
    ("company", "GET", "/events/outbox"): "event-operations.service listOutbox",
    ("company", "POST", "/events/outbox/:eventId/retry"): "event-operations.service retryOutbox",
    ("company", "GET", "/operations/automation/invocations/:invocationId/inspector"): "automation-inspector.service",
    ("company", "GET", "/operations/automation/needs-you"): "automation-inspector.service",
    ("company", "POST", "/finance-legal/transactions"): "financial-transaction.service requireFinancialTransactionWrite",
    ("company", "POST", "/identity/workforce-members"): "workforce.service hireWorkforceMemberRecord",
    ("company", "POST", "/operations/cycles"): "twelve-week-year.service createCycleService",
    ("company", "POST", "/operations/weekly-commitments"): "twelve-week-year.service createWeeklyCommitmentService",
    ("company", "POST", "/operations/weekly-plans"): "twelve-week-year.service createWeeklyPlanService",
    # Endpoint nội bộ worker: service gọi requireWorkerServiceAuth.
    ("company", "POST", "/events/internal/agent-runtime-signal"): "agent-runtime-signal.service requireWorkerServiceAuth",
    ("company", "POST", "/operations/automation/internal/outcome"): "automation-outcome.service requireWorkerServiceAuth",
    # Webhook: channel-inbound.service xác minh chữ ký của adapter.
    ("company", "POST", "/commercial/engagement/channels/zalo/webhook"): "channel-inbound.service verifyInbound",
    # Catalog pháp lý dùng chung toàn hệ thống, chỉ đọc, không chứa dữ liệu tenant.
    ("company", "GET", "/finance-legal/regulation-sources"): "public read-only global catalog",
    ("company", "GET", "/finance-legal/obligation-templates"): "public read-only global catalog",
    # Stub DEPRECATED luôn trả invalidArgument, không chạm dữ liệu.
    ("company", "POST", "/operations/projects/:projectId/executive-preset"): "deprecated stub",
    ("company", "POST", "/operations/projects/:projectId/executive-roles/:roleKey/activate"): "deprecated stub",
    ("company", "POST", "/operations/projects/:projectId/executive-roles/:roleKey/disable"): "deprecated stub",
}


def _collect_unguarded_exposed_endpoints() -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for base in ("services/company", "services/cosa"):
        service = base.split("/")[1]
        for path in (ROOT / base).rglob("*.ts"):
            rel = path.relative_to(ROOT).as_posix()
            if "node_modules" in path.parts or "/tests/" in rel or rel.endswith(".test.ts"):
                continue
            text = path.read_text(encoding="utf-8")
            for match in _API_BLOCK.finditer(text):
                block = match.group(1)
                route = re.search(r"path:\s*[\"'](/[^\"']+)", block)
                if not route or not re.search(r"expose:\s*true", block):
                    continue
                if re.search(r"auth:\s*true", block):
                    continue
                end = text.find("\n);", match.end())
                body = text[match.end() : end if end != -1 else match.end() + 3000]
                if _GUARD_PATTERN.search(body):
                    continue
                method = re.search(r"method:\s*[\"'](\w+)", block)
                found.add((service, method.group(1) if method else "GET", route.group(1)))
    return found


def test_every_exposed_endpoint_without_auth_calls_a_guard() -> None:
    unguarded = _collect_unguarded_exposed_endpoints()
    reviewed = set(SERVICE_GUARDED_ALLOWLIST) | EXPLICIT_UNAUTHENTICATED_ALLOWLIST

    unexpected = unguarded - reviewed
    assert not unexpected, (
        f"Exposed endpoint(s) without a visible auth guard: {sorted(unexpected)}. "
        "Call requireWorkspaceAccess/verifyCosaDelegation/requireWorkerServiceAuth in the handler, "
        "or — if the service guards it — review it and add it to SERVICE_GUARDED_ALLOWLIST."
    )

    stale = set(SERVICE_GUARDED_ALLOWLIST) - unguarded
    assert not stale, f"Stale entries in SERVICE_GUARDED_ALLOWLIST: {sorted(stale)}"


def test_guard_scan_flags_handler_without_guard(tmp_path: Path) -> None:
    source = (
        'export const leak = api(\n'
        '  { expose: true, method: "GET", path: "/operations/leak/:workspaceId" },\n'
        '  async (params: { workspaceId: string }) => {\n'
        '    return readEverything(params.workspaceId);\n'
        '  }\n'
        ');\n'
    )
    match = _API_BLOCK.search(source)
    assert match is not None
    end = source.find("\n);", match.end())
    assert not _GUARD_PATTERN.search(source[match.end() : end])
