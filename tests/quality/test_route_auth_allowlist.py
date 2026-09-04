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
    ("cosa", "POST", "/platform/auth/sessions"),
    ("cosa", "POST", "/platform/auth/register"),
    ("company", "POST", "/identity/session/renew"),
    ("company", "POST", "/identity/sync-from-platform"),
    ("cosa", "POST", "/platform/internal/list-workspace-memberships"),
    ("cosa", "POST", "/platform/internal/validate-workspace-membership"),
    ("cosa", "POST", "/platform/internal/mark-workspace-synced"),
    # B5 (ADR-COSA-DELEGATION-002): Encore auth handler dùng PLATFORM_JWT_SECRET,
    # nhưng caller (apps/cosa) mang control-plane delegation token ký bởi
    # COSA_CONTROL_DELEGATION_SECRET — 2 secret khác nhau nên auth built-in
    # luôn 403. Handler tự verify thủ công qua resolveCallerAuthorizedForWorkspace
    # (control-plane delegation, fallback platform token + verifyWorkspaceMembership)
    # rồi mới build snapshot. auth:false có chủ đích, đã kiểm tra.
    ("cosa", "GET", "/platform/auth/me/agent-policy-snapshot"),
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
