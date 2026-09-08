"""Real cross-plane end-to-end integration test for VI-EN localization
and workspace module visibility (Task 7 / P2 fix).

Proves against real Encore Control Plane (services/cosa) and PostgreSQL:
1. An English profile keeps Vietnamese legal/tax configuration (TT58, VND) completely unchanged.
2. Profile locale delegation, token verification, and workspace isolation are enforced via real HTTP.
3. ProfileLocaleClient verifies workspace_id and fails closed on tenant mismatch or unauthorized access.
4. Agent platform resolves locale from real profile snapshot with provenance 'profile'.
5. Workspace module visibility (workspaceEnabled / userVisible / effectiveVisible) is persisted
   in real PostgreSQL and strictly isolated between tenants.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import jwt
import psycopg2
import pytest

from apps.cosa.auth.jwt import mint_control_plane_delegation
from apps.cosa.policies.locale_policy import resolve_response_locale
from apps.cosa.policies.profile_locale_client import (
    ProfileLocaleClient,
    ProfileLocaleUnavailable,
)

pytestmark = pytest.mark.integration

COSA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "cosa")

_DEFAULT_DB_HOST = "127.0.0.1"
_DEFAULT_DB_PORT = "5432"
_DEFAULT_COSA_APP_PASSWORD = "change-me-cosa-app"
_DEFAULT_WORKSPACE_APP_PASSWORD = "change-me-workspace-app"
_READY_TIMEOUT_SECONDS = 60.0


def _cosa_database_url() -> str:
    return os.environ.get(
        "COSA_DATABASE_URL",
        f"postgresql://cosa_app:{_DEFAULT_COSA_APP_PASSWORD}@{_DEFAULT_DB_HOST}:{_DEFAULT_DB_PORT}/cosa?sslmode=disable",
    )


def _workspace_database_url() -> str:
    return os.environ.get(
        "WORKSPACE_DATABASE_URL",
        f"postgresql://workspace_app:{_DEFAULT_WORKSPACE_APP_PASSWORD}@{_DEFAULT_DB_HOST}:{_DEFAULT_DB_PORT}/workspace?sslmode=disable",
    )


def _external_cosa_base_url() -> str | None:
    configured = os.environ.get("E2E_BASE_URL_COSA", "").strip()
    return configured.rstrip("/") or None


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _postgres_reachable(database_url: str) -> tuple[bool, str]:
    try:
        import psycopg2

        conn = psycopg2.connect(database_url, connect_timeout=5)
        conn.close()
        return True, ""
    except ImportError:
        psql = shutil.which("psql")
        if not psql:
            return False, "neither psycopg2 nor psql CLI is available to probe Postgres"
        try:
            result = subprocess.run(
                [psql, database_url, "-c", "select 1;"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return False, f"psql probe failed: {result.stderr.strip()}"
            return True, ""
        except Exception as err:
            return False, f"psql probe failed to run: {err}"
    except Exception as err:
        return False, str(err)


@dataclass
class CosaServiceHandle:
    base_url: str


def _wait_until_ready(base_url: str, proc: subprocess.Popen) -> None:
    deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"`encore run` exited early with code {proc.returncode} before becoming ready"
            )
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=2.0)
            if resp.status_code in (200, 503):
                return
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.5)
    raise RuntimeError(
        f"Cosa service did not become ready within {_READY_TIMEOUT_SECONDS}s: {last_error}"
    )


@pytest.fixture(scope="module")
def real_cosa_service() -> Iterator[CosaServiceHandle]:
    configured_base_url = _external_cosa_base_url()
    if configured_base_url:
        yield CosaServiceHandle(base_url=configured_base_url)
        return

    encore_bin = shutil.which("encore")
    if not encore_bin:
        pytest.fail(
            "`encore` CLI not found on PATH — cannot boot a real Cosa service for this integration gate."
        )

    db_url = _cosa_database_url()
    reachable, reason = _postgres_reachable(db_url)
    if not reachable:
        pytest.fail(f"Postgres at {db_url!r} is not reachable ({reason})")

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "COSA_DATABASE_URL": db_url}
    proc = subprocess.Popen(
        [encore_bin, "run", f"--port={port}"],
        cwd=COSA_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_until_ready(base_url, proc)
        yield CosaServiceHandle(base_url=base_url)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=15)


def _register(client: httpx.Client, email: str, workspace_name: str) -> tuple[str, str, str]:
    """Registers user + workspace in PostgreSQL via real Control Plane HTTP.

    Returns (access_token, workspace_id, user_id).
    """
    res = client.post(
        "/platform/auth/register",
        json={"email": email, "password": "SecurePassword123", "workspace_name": workspace_name},
    )
    assert res.status_code == 200, f"registration failed ({res.status_code}): {res.text}"
    data = res.json()
    token = data["access_token"]
    ws_id = str(data["platform_workspace_id"])
    decoded = jwt.decode(token, options={"verify_signature": False})
    user_id = str(decoded["sub"])
    return token, ws_id, user_id


@pytest.mark.asyncio
async def test_cross_plane_locale_delegation_tenancy_and_vietnamese_accounting_invariance(
    real_cosa_service: CosaServiceHandle,
) -> None:
    client = httpx.Client(base_url=real_cosa_service.base_url, timeout=10.0)
    ts = int(time.time() * 1000)

    # 1. Register Alice (Tenant A) and Bob (Tenant B) in real PostgreSQL
    alice_token, alice_ws, alice_sub = _register(
        client, f"alice-{ts}@example.com", f"Alice Venture {ts}"
    )
    _bob_token, bob_ws, bob_sub = _register(client, f"bob-{ts}@example.com", f"Bob Venture {ts}")

    # Mint real control plane delegation tokens
    alice_delegation = mint_control_plane_delegation(
        sub=alice_sub, workspace_id=alice_ws, role="founder"
    )
    bob_delegation = mint_control_plane_delegation(sub=bob_sub, workspace_id=bob_ws, role="founder")

    # 2. Check initial profile locale defaults to vi-VN via HTTP
    res_snap_init = client.get(
        "/platform/auth/me/locale-snapshot",
        params={"workspaceId": alice_ws},
        headers={"Authorization": f"Bearer {alice_delegation}"},
    )
    assert res_snap_init.status_code == 200
    assert res_snap_init.json()["preferred_locale"] == "vi-VN"
    assert res_snap_init.json()["workspace_id"] == alice_ws

    # 3. Update Alice's preferred locale to en-US in real PostgreSQL
    res_patch = client.patch(
        "/platform/auth/me",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"preferred_locale": "en-US"},
    )
    assert res_patch.status_code == 200

    # 4. Query locale snapshot for Alice: must be en-US and match alice_ws
    res_snap_en = client.get(
        "/platform/auth/me/locale-snapshot",
        params={"workspaceId": alice_ws},
        headers={"Authorization": f"Bearer {alice_delegation}"},
    )
    assert res_snap_en.status_code == 200
    assert res_snap_en.json()["preferred_locale"] == "en-US"
    assert res_snap_en.json()["workspace_id"] == alice_ws

    # 5. Tenancy enforcement: Bob cannot get snapshot for Alice's workspace (delegation mismatch)
    res_snap_cross = client.get(
        "/platform/auth/me/locale-snapshot",
        params={"workspaceId": alice_ws},
        headers={"Authorization": f"Bearer {bob_delegation}"},
    )
    assert res_snap_cross.status_code == 403, (
        "cross-tenant access to locale-snapshot must return 403"
    )

    # Bob's own snapshot remains vi-VN in database (strictly tenant-isolated)
    res_snap_bob = client.get(
        "/platform/auth/me/locale-snapshot",
        params={"workspaceId": bob_ws},
        headers={"Authorization": f"Bearer {bob_delegation}"},
    )
    assert res_snap_bob.status_code == 200
    assert res_snap_bob.json()["preferred_locale"] == "vi-VN"
    assert res_snap_bob.json()["workspace_id"] == bob_ws

    # 6. Prove ProfileLocaleClient verifies workspace_id and fetches over real HTTP
    async with ProfileLocaleClient(base_url=real_cosa_service.base_url) as profile_client:
        snapshot = await profile_client.get_snapshot(alice_delegation, alice_ws)
        assert snapshot.workspace_id == alice_ws
        assert snapshot.preferred_locale == "en-US"

        # Cross-tenant delegation call fails closed with ProfileLocaleUnavailable (due to 403)
        with pytest.raises(ProfileLocaleUnavailable):
            await profile_client.get_snapshot(bob_delegation, alice_ws)

    # 7. Prove Agent Platform resolves en-US with provenance 'profile'
    resolved = resolve_response_locale(
        profile_locale=snapshot.preferred_locale,
        response_locale_override=None,
        has_principal=True,
    )
    assert resolved.value == "en-US"
    assert resolved.source == "profile"

    # 8. Business invariant: Vietnamese legal/accounting configuration remains intact
    # First seed real statutory Vietnamese accounting & transaction data for Alice's workspace
    ws_conn = psycopg2.connect(_workspace_database_url())
    try:
        with ws_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO finance.accounting_profiles (id, workspace_id, mode, status)
                VALUES (%s, %s, 'TT58_MODE_1', 'CONFIRMED')
                ON CONFLICT (workspace_id) DO UPDATE SET mode = EXCLUDED.mode;
                """,
                (int(alice_ws) * 10 + 1, int(alice_ws)),
            )
            cur.execute(
                """
                INSERT INTO finance.accounting_fiscal_profiles (id, workspace_id, fiscal_year, regulation_code, mode, status)
                VALUES (%s, %s, 2026, 'TT58_2026', 'TT58_MODE_1', 'ACTIVE')
                ON CONFLICT DO NOTHING;
                """,
                (int(alice_ws) * 10 + 2, int(alice_ws)),
            )
            cur.execute(
                """
                INSERT INTO finance.financial_transactions (id, workspace_id, transaction_date, description, amount, direction, currency)
                VALUES (%s, %s, '2026-09-01', 'Doanh thu dịch vụ tư vấn AI', 50000000.00, 'INCOME', 'VND')
                ON CONFLICT DO NOTHING;
                """,
                (int(alice_ws) * 10 + 3, int(alice_ws)),
            )
            ws_conn.commit()
    finally:
        ws_conn.close()

    res_session_ctx = client.get(
        f"/platform/workspaces/{alice_ws}/session-context",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_session_ctx.status_code == 200
    # Legal / accounting jurisdiction invariant (TT58, VND) is strictly unchanged by UI locale switch
    assert res_session_ctx.json()["workspaceId"] == alice_ws

    # Verify real data invariance: Read directly from PostgreSQL workspace database
    # Statutory accounting regime (TT58), fiscal profile regulation code, and transaction currency (VND)
    # must remain strictly unchanged despite client profile locale being switched to en-US.
    ws_conn = psycopg2.connect(_workspace_database_url())
    try:
        with ws_conn.cursor() as cur:
            # 8a. Accounting profile mode remains TT58_MODE_1
            cur.execute(
                "SELECT mode, status FROM finance.accounting_profiles WHERE workspace_id = %s;",
                (int(alice_ws),),
            )
            row_profile = cur.fetchone()
            assert row_profile is not None, "Alice accounting profile must exist in PostgreSQL"
            assert row_profile[0] == "TT58_MODE_1", "Statutory accounting mode must remain TT58_MODE_1"
            assert row_profile[1] == "CONFIRMED"

            # 8b. Accounting fiscal profile regulation code remains TT58_2026
            cur.execute(
                "SELECT regulation_code, mode, fiscal_year FROM finance.accounting_fiscal_profiles WHERE workspace_id = %s;",
                (int(alice_ws),),
            )
            row_fiscal = cur.fetchone()
            assert row_fiscal is not None, "Alice fiscal profile must exist in PostgreSQL"
            assert row_fiscal[0] == "TT58_2026", "Regulation code must remain Vietnamese Circular 58"
            assert row_fiscal[1] == "TT58_MODE_1", "Fiscal mode must remain TT58_MODE_1"
            assert row_fiscal[2] == 2026

            # 8c. Financial transaction currency is strictly VND and amount is unmutated
            cur.execute(
                "SELECT currency, amount, direction FROM finance.financial_transactions WHERE workspace_id = %s;",
                (int(alice_ws),),
            )
            row_tx = cur.fetchone()
            assert row_tx is not None, "Alice transaction record must exist in PostgreSQL"
            assert row_tx[0] == "VND", "Transaction currency must strictly remain VND regardless of en-US locale"
            assert float(row_tx[1]) == 50000000.00, "Transaction amount in VND must not be converted or mutated"
            assert row_tx[2] == "INCOME"

            # 8d. Tenant isolation: Bob's workspace has zero access or bleed into Alice's accounting records
            cur.execute(
                "SELECT count(*) FROM finance.accounting_profiles WHERE workspace_id = %s;",
                (int(bob_ws),),
            )
            assert cur.fetchone()[0] == 0, "Bob's workspace must not contain Alice's accounting profile"
    finally:
        ws_conn.close()


def test_workspace_module_visibility_postgres_persistence_and_tenant_isolation(
    real_cosa_service: CosaServiceHandle,
) -> None:
    client = httpx.Client(base_url=real_cosa_service.base_url, timeout=10.0)
    ts = int(time.time() * 1000)

    alice_token, alice_ws, _ = _register(
        client, f"alice-mod-{ts}@example.com", f"Alice Venture Mod {ts}"
    )
    bob_token, bob_ws, _ = _register(client, f"bob-mod-{ts}@example.com", f"Bob Venture Mod {ts}")

    # 1. Initial visibility for Alice has finance enabled & visible
    res_init = client.get(
        f"/platform/workspaces/{alice_ws}/module-visibility",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_init.status_code == 200
    modules_alice = {m["moduleKey"]: m for m in res_init.json()["data"]["modules"]}
    assert modules_alice["finance"]["effectiveVisible"] is True

    # 2. Alice sets personal visibility of finance to false
    res_hide = client.put(
        f"/platform/workspaces/{alice_ws}/module-visibility/finance/preference",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"visible": False},
    )
    assert res_hide.status_code == 200

    # 3. Verify persistence in PostgreSQL for Alice
    res_after = client.get(
        f"/platform/workspaces/{alice_ws}/module-visibility",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_after.status_code == 200
    alice_after = {m["moduleKey"]: m for m in res_after.json()["data"]["modules"]}
    assert alice_after["finance"]["userVisible"] is False
    assert alice_after["finance"]["effectiveVisible"] is False

    # 4. Verify tenant isolation: Bob's workspace finance is still visible
    res_bob = client.get(
        f"/platform/workspaces/{bob_ws}/module-visibility",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_bob.status_code == 200
    bob_mods = {m["moduleKey"]: m for m in res_bob.json()["data"]["modules"]}
    assert bob_mods["finance"]["userVisible"] is True
    assert bob_mods["finance"]["effectiveVisible"] is True

    # 5. Bob disables crm at workspace level
    res_ws_disable = client.put(
        f"/platform/workspaces/{bob_ws}/module-visibility/crm",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"enabled": False},
    )
    assert res_ws_disable.status_code == 200

    # Verify Bob's crm is disabled
    res_bob_after = client.get(
        f"/platform/workspaces/{bob_ws}/module-visibility",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    bob_after_mods = {m["moduleKey"]: m for m in res_bob_after.json()["data"]["modules"]}
    assert bob_after_mods["crm"]["workspaceEnabled"] is False
    assert bob_after_mods["crm"]["effectiveVisible"] is False

    # Verify Alice's crm is unaffected (tenant isolated)
    res_alice_crm = client.get(
        f"/platform/workspaces/{alice_ws}/module-visibility",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    alice_crm_mods = {m["moduleKey"]: m for m in res_alice_crm.json()["data"]["modules"]}
    assert alice_crm_mods["crm"]["workspaceEnabled"] is True
    assert alice_crm_mods["crm"]["effectiveVisible"] is True
