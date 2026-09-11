"""S9: Founder-Controlled Workforce Authorization E2E Scenario.

Proves:
1. Workspace transitions SHADOW -> ENFORCED only via founder-audited command.
2. Non-founder (member) cannot transition mode or grant agent capabilities.
3. Agent without grant is denied before effect.
4. Revoked grant after dispatch is denied before effect.
5. High-risk live authorization ticket is issued only with human founder approval and bound to checkpoint.
6. Cross-tenant capability and authority access fails closed.
"""

from __future__ import annotations

from typing import Any

import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> dict[str, Any]:
    company = stack.company
    workspace_id = seeded.workspace_id
    founder_token = seeded.owner_token
    member_token = seeded.member_token

    result: dict[str, Any] = {}

    # 1. Seed an AI agent workforce member for this workspace
    agent_wf_id = identity.seed_workforce_agent(
        cluster,
        workspace_id,
        agent_spec_id="operations",
        role_title="Operations Agent",
    )

    # 2. Non-founder (member) cannot transition authorization mode
    if member_token:
        r_member_mode = company.post(
            "/identity/authorization/mode",
            json={"targetMode": "ENFORCED", "reason": "Unauthorized attempt"},
            token=member_token,
            workspace_id=workspace_id,
        )
        assert r_member_mode.status_code == 403, (
            f"Non-founder must be rejected from mode transition (got {r_member_mode.status_code}): {r_member_mode.text}"
        )

        r_member_grant = company.post(
            "/identity/agent-capability-grants",
            json={
                "agentWorkforceMemberId": agent_wf_id,
                "capabilityId": "operations.task.list",
            },
            token=member_token,
            workspace_id=workspace_id,
        )
        assert r_member_grant.status_code == 403, (
            f"Non-founder must be rejected from granting capabilities (got {r_member_grant.status_code}): {r_member_grant.text}"
        )

    # 3. Founder transitions workspace from SHADOW to ENFORCED
    r_founder_mode = company.post(
        "/identity/authorization/mode",
        json={"targetMode": "ENFORCED", "reason": "S9 founder cutover"},
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_founder_mode.status_code == 200, (
        f"Founder mode transition failed ({r_founder_mode.status_code}): {r_founder_mode.text}"
    )
    mode_body = r_founder_mode.json()
    assert mode_body["mode"] == "ENFORCED"
    assert mode_body["epoch"] >= 2

    # Verify transition audit event recorded in database
    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT event_type, reason, authorization_epoch
                FROM core.authorization_events
                WHERE workspace_id = %s AND event_type = 'AUTHORIZATION_MODE_TRANSITIONED'
                ORDER BY created_at DESC LIMIT 1
                """,
                (int(workspace_id),),
            )
            event_row = cur.fetchone()
            assert event_row is not None, (
                "Missing AUTHORIZATION_MODE_TRANSITIONED event in audit table"
            )
            assert event_row[1] == "S9 founder cutover"
    finally:
        conn.close()

    # -----------------------------------------------------------------------
    # Branch 1: Agent without grant -> denied
    # -----------------------------------------------------------------------
    r_sim_no_grant = company.post(
        "/identity/authorization/simulate",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_sim_no_grant.status_code == 200, r_sim_no_grant.text
    assert r_sim_no_grant.json().get("decision") == "DENY", (
        f"Expected DENY for agent without grant: {r_sim_no_grant.text}"
    )

    r_ticket_no_grant = company.post(
        "/identity/agent-authorization/tickets",
        json={
            "runId": "run-no-grant",
            "toolCallId": "call-no-grant",
            "checkpointRef": "chk-no-grant",
            "capabilityId": "operations.task.list",
            "agentWorkforceMemberId": agent_wf_id,
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_ticket_no_grant.status_code == 403, (
        f"Ticket issuance without grant must return 403: {r_ticket_no_grant.text}"
    )
    result["agent_without_grant"] = "denied"

    # -----------------------------------------------------------------------
    # Branch 2: Revoked grant after dispatch -> denied before effect
    # -----------------------------------------------------------------------
    # Founder creates grant
    r_create_grant = company.post(
        "/identity/agent-capability-grants",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_create_grant.status_code == 200, (
        f"Create grant failed ({r_create_grant.status_code}): {r_create_grant.text}"
    )
    grant_body = r_create_grant.json()
    grant_id = grant_body.get("grantId") or grant_body.get("id")
    assert grant_id, f"Missing grantId in response: {grant_body}"

    # Verify simulate allows with active grant
    r_sim_granted = company.post(
        "/identity/authorization/simulate",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_sim_granted.json().get("decision") == "ALLOW", r_sim_granted.text

    # Founder revokes grant before side effect
    r_revoke = company.post(
        f"/identity/agent-capability-grants/{grant_id}/revoke",
        json={"grantId": grant_id, "reason": "Founder revoked after dispatch"},
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_revoke.status_code == 200, f"Revoke failed ({r_revoke.status_code}): {r_revoke.text}"

    # Now simulate must DENY
    r_sim_revoked = company.post(
        "/identity/authorization/simulate",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_sim_revoked.json().get("decision") == "DENY", (
        f"Expected DENY after revocation: {r_sim_revoked.text}"
    )

    # And live ticket issuance must be rejected with 403
    r_ticket_revoked = company.post(
        "/identity/agent-authorization/tickets",
        json={
            "runId": "run-revoked-dispatch",
            "toolCallId": "call-revoked-dispatch",
            "checkpointRef": "chk-revoked-dispatch",
            "capabilityId": "operations.task.list",
            "agentWorkforceMemberId": agent_wf_id,
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_ticket_revoked.status_code == 403, (
        f"Ticket issuance after revoke must be 403 (denied before effect): {r_ticket_revoked.text}"
    )
    result["revoked_after_dispatch"] = "denied_before_effect"

    # -----------------------------------------------------------------------
    # Branch 3: Approval bound to checkpoint
    # -----------------------------------------------------------------------
    # Founder creates fresh active grant
    r_create_grant2 = company.post(
        "/identity/agent-capability-grants",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_create_grant2.status_code == 200, r_create_grant2.text

    checkpoint_ref = "chk-s9-approved-checkpoint-01"
    r_ticket_valid = company.post(
        "/identity/agent-authorization/tickets",
        json={
            "runId": "run-s9-approved",
            "toolCallId": "tool-s9-call-01",
            "checkpointRef": checkpoint_ref,
            "capabilityId": "operations.task.list",
            "agentWorkforceMemberId": agent_wf_id,
        },
        token=founder_token,
        workspace_id=workspace_id,
    )
    assert r_ticket_valid.status_code == 200, (
        f"Valid ticket issuance failed ({r_ticket_valid.status_code}): {r_ticket_valid.text}"
    )
    ticket_body = r_ticket_valid.json()
    assert ticket_body.get("ticketId")
    assert ticket_body.get("authorizationEpoch") is not None

    # Verify DB has ticket bound to checkpoint
    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT checkpoint_ref, consumed_at, capability_id
                FROM core.agent_authorization_tickets
                WHERE ticket_id = %s
                """,
                (ticket_body["ticketId"],),
            )
            ticket_row = cur.fetchone()
            assert ticket_row is not None, "Ticket not found in core.agent_authorization_tickets"
            assert ticket_row[0] == checkpoint_ref, f"Ticket checkpoint_ref mismatch: {ticket_row[0]}"
            assert ticket_row[1] is None, "Ticket should not be consumed yet"
            assert ticket_row[2] == "operations.task.list"
    finally:
        conn.close()

    result["approval_bound_to_checkpoint"] = True

    # -----------------------------------------------------------------------
    # Branch 4: Cross-tenant negative isolation -> denied
    # -----------------------------------------------------------------------
    # Create foreign workspace
    foreign_workspace = identity.seed_workspace(stack, cluster, with_member=False)
    foreign_ws_id = foreign_workspace.workspace_id

    # Try to access foreign workspace with seeded owner_token
    r_cross_grant = company.post(
        "/identity/agent-capability-grants",
        json={
            "agentWorkforceMemberId": agent_wf_id,
            "capabilityId": "operations.task.list",
        },
        token=founder_token,
        workspace_id=foreign_ws_id,
    )
    assert r_cross_grant.status_code in (403, 502), (
        f"Cross-tenant grant must be denied: {r_cross_grant.status_code}"
    )

    r_cross_mode = company.post(
        "/identity/authorization/mode",
        json={"targetMode": "ENFORCED", "reason": "Cross-tenant attack"},
        token=founder_token,
        workspace_id=foreign_ws_id,
    )
    assert r_cross_mode.status_code in (403, 502), (
        f"Cross-tenant mode change must be denied: {r_cross_mode.status_code}"
    )

    result["cross_tenant"] = "denied"

    return result
