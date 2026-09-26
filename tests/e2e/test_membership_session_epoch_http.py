"""E2E HTTP proof cho thu hồi membership và session epoch (plan 2026-09-25 core-auth
Task 4 §5) trên process Company thật.

Kịch bản: Founder có local session → Core thu hồi membership (event qua relay ký JWT
worker) → mọi ghi/đọc bằng session cũ bị chặn → replay event active cũ không kích
hoạt lại → Core cấp lại membership nhưng session cấp trước lần thu hồi vẫn bị chặn và
không renew được (phải đồng bộ lại với Core để có session mới).
"""

from __future__ import annotations

import time

import httpx

from tests.e2e.conftest import CompanyServiceHandle, mint_e2e_worker_token


def _event(org_id: str, platform_user_id: str, version: int, status: str, tag: str) -> dict:
    return {
        "event": {
            "eventId": f"e2e-epoch-{tag}-{time.time_ns()}",
            "organizationId": org_id,
            "userId": platform_user_id,
            "membershipVersion": version,
            "status": status,
            "role": "founder",
            "occurredAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        }
    }


def test_revoked_membership_blocks_old_session_even_after_regrant(
    real_company_service: CompanyServiceHandle,
) -> None:
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    platform_user_id = f"core-user-{time.time_ns()}"
    registration = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"epoch-{time.time_ns()}@example.com",
            "displayName": "Epoch Founder",
            "platformUserId": platform_user_id,
        },
    )
    assert registration.status_code == 200, registration.text
    session = registration.json()
    org_id = str(session["workspaceId"])
    old_session = f"Bearer {session['accessToken']}"
    headers = {"Authorization": old_session, "X-Workspace-Id": org_id}
    worker = {"Authorization": f"Bearer {mint_e2e_worker_token('membership-relay')}"}

    def write_goal() -> httpx.Response:
        return client.post(
            "/operations/goals",
            json={"workspaceId": org_id, "title": "Goal", "goalType": "strategic"},
            headers=headers,
        )

    assert write_goal().status_code == 200

    # auth_time có độ phân giải giây: đợi sang giây mới để mốc thu hồi rõ ràng.
    time.sleep(1.1)
    revoked = client.post(
        "/internal/identity/membership-events",
        json=_event(org_id, platform_user_id, 2, "revoked", "revoke"),
        headers=worker,
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["membershipState"] == "revoked"

    assert write_goal().status_code == 403
    me = client.get("/identity/me", headers=headers)
    assert me.status_code == 403, me.text

    stale = client.post(
        "/internal/identity/membership-events",
        json=_event(org_id, platform_user_id, 1, "active", "stale"),
        headers=worker,
    )
    assert stale.status_code == 200, stale.text
    assert stale.json() == {"applied": False, "reason": "stale_version"}
    assert write_goal().status_code == 403

    time.sleep(1.1)
    regranted = client.post(
        "/internal/identity/membership-events",
        json=_event(org_id, platform_user_id, 3, "active", "regrant"),
        headers=worker,
    )
    assert regranted.status_code == 200, regranted.text
    assert regranted.json()["membershipState"] == "active"

    # Membership active trở lại nhưng session cấp trước lần thu hồi không sống lại.
    assert write_goal().status_code == 403
    renew = client.post("/identity/session/renew", headers={"Authorization": old_session})
    assert renew.status_code == 403, renew.text
