"""Task 13 (plan 2026-09-28-stage-adaptive-ai-operating-system) — proves the
first scaled Initiative through a real four-plane path: Company transition ->
durable outbox -> dedicated ai-initiative relay -> COSA's
`/internal/ai-initiatives/snapshots` -> Postgres-durable snapshot store.

Uses the same `real_cosa_stack`/`disposable_cluster` fixtures and direct-SQL
seed convention (`tests/e2e/seed/identity.py`) as the other cross-plane
smoke/recovery tests — 4 real planes + disposable Postgres, no mocks/skips.

Evidence recording (value contract / data readiness assessment / budget
policy) has no HTTP surface yet (Task 3 only shipped service-level functions,
see services/company/operations/services/ai-initiative-evidence.service.ts) —
seeded directly via SQL against `strategy.ai_initiative_*` tables
(migration 037), the same way `tests/e2e/seed/identity.py` seeds
`core.workforce_members` directly where no HTTP endpoint exists either.
"""

from __future__ import annotations

import secrets
import time
from typing import Any

import pytest

from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane

_TIMEOUT_S = 60.0


def _snowflake() -> int:
    """Monotonic-enough bigint id for hand-seeded rows — same shape as
    `tests/e2e/seed/identity.py::_snowflake`, kept local to avoid reaching
    into that module's private helper."""
    return (int(time.time() * 1000) << 15) | secrets.randbits(15)


def _seed_objective_and_key_result(cluster, workspace_id: str, project_id: str) -> str:
    import psycopg2

    objective_id = _snowflake()
    key_result_id = _snowflake()
    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title, status)
                VALUES (%s, %s, %s, 'Ship the AI Initiative operating system', 'draft')
                """,
                (objective_id, int(workspace_id), int(project_id)),
            )
            cur.execute(
                """
                INSERT INTO strategy.key_results (id, workspace_id, objective_id, title, status)
                VALUES (%s, %s, %s, 'Reconciliation cycle time', 'draft')
                """,
                (key_result_id, int(workspace_id), objective_id),
            )
    finally:
        conn.close()
    return str(key_result_id)


def _seed_evidence(
    cluster,
    workspace_id: str,
    project_id: str,
    initiative_id: str,
    measurement_owner_member_id: str,
    *,
    data_readiness_status: str = "READY",
    retrieval_mode: str = "lexical",
) -> None:
    """Seeds one revision each of value contract, data readiness assessment
    and budget policy — the minimum evidence set `evaluateAiInitiativePromotionGates`
    requires for PILOT->VALIDATE->SCALE_CANDIDATE (see
    ai-initiative-promotion-policy.ts)."""
    import psycopg2

    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy.ai_initiative_value_contracts (
                    id, workspace_id, project_id, initiative_id, revision, metric_contract_id,
                    baseline_value, baseline_observed_at, baseline_source_ref, target_value, target_by,
                    measurement_window, unit, expected_value_method, measurement_owner_member_id
                ) VALUES (
                    %s, %s, %s, %s, 1, 'reconciliation-time',
                    120.0, now(), 'audit-report-q1.pdf', 15.0, now() + interval '30 days',
                    'MONTHLY', 'HOURS', 'BENCHMARK', %s
                )
                """,
                (
                    _snowflake(),
                    int(workspace_id),
                    int(project_id),
                    int(initiative_id),
                    int(measurement_owner_member_id),
                ),
            )
            cur.execute(
                """
                INSERT INTO strategy.ai_initiative_data_readiness_assessments (
                    id, workspace_id, project_id, initiative_id, revision, classification,
                    access_authority_ref, freshness_slo, metadata_owner_member_id, retrieval_mode,
                    assessment_status
                ) VALUES (
                    %s, %s, %s, %s, 1, 'INTERNAL', 'authority-ref-1', 'P1D', %s, %s, %s
                )
                """,
                (
                    _snowflake(),
                    int(workspace_id),
                    int(project_id),
                    int(initiative_id),
                    int(measurement_owner_member_id),
                    retrieval_mode,
                    data_readiness_status,
                ),
            )
            cur.execute(
                """
                INSERT INTO strategy.ai_initiative_budget_policies (
                    id, workspace_id, project_id, initiative_id, revision, period, currency,
                    soft_cost_threshold, hard_cost_threshold, action_on_breach
                ) VALUES (
                    %s, %s, %s, %s, 1, 'MONTHLY', 'USD', 100.0, 500.0, 'WARN'
                )
                """,
                (
                    _snowflake(),
                    int(workspace_id),
                    int(project_id),
                    int(initiative_id),
                ),
            )
    finally:
        conn.close()


def _query_snapshot(cluster, workspace_id: str, initiative_id: str) -> dict[str, Any] | None:
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=10)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM models.ai_initiative_promotion_snapshots
                WHERE workspace_id = %s AND initiative_id = %s
                ORDER BY initiative_revision DESC
                LIMIT 1
                """,
                (workspace_id, initiative_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def _create_and_approve_initiative(
    company, token: str, workspace_id: str, project_id: str, key_result_id: str, owner_member_id: str
) -> dict[str, Any]:
    r = company.post(
        f"/operations/projects/{project_id}/ai-initiatives",
        json={
            "title": "Automated reconciliation copilot",
            "businessProblem": "Manual month-end reconciliation is slow and error-prone",
            "intendedOutcome": "Cut reconciliation cycle time with an auditable AI workflow",
            "businessOwnerMemberId": owner_member_id,
            "keyResultIds": [key_result_id],
            "riskTier": "LOW",
            "autonomyTier": "A1",
        },
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, f"create ai initiative failed: {r.status_code} {r.text}"
    initiative = r.json()

    r = company.post(
        f"/operations/initiatives/{initiative['id']}/approve",
        json={"reason": "E2E scaled-initiative proof"},
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, f"approve initiative failed: {r.status_code} {r.text}"
    # approveInitiativeService bumps `revision` (existing.revision + 1) — the
    # caller must transition using THIS revision, not the pre-approval one.
    return r.json()


def _transition(
    company,
    token: str,
    workspace_id: str,
    project_id: str,
    initiative_id: str,
    *,
    target_state: str,
    expected_revision: int,
    reason_code: str,
    human_escalation_route: str | None = None,
    rollback_pause_procedure: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "targetState": target_state,
        "expectedRevision": expected_revision,
        "reasonCode": reason_code,
    }
    if human_escalation_route is not None:
        body["humanEscalationRoute"] = human_escalation_route
    if rollback_pause_procedure is not None:
        body["rollbackPauseProcedure"] = rollback_pause_procedure
    r = company.post(
        f"/operations/projects/{project_id}/ai-initiatives/{initiative_id}/transition",
        json=body,
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, f"transition to {target_state} failed: {r.status_code} {r.text}"
    return r.json()


def _promote_to_scale_candidate(real_cosa_stack, disposable_cluster) -> tuple[dict[str, Any], Any]:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company
    token, workspace_id = seeded.owner_token, seeded.workspace_id
    project_id = seeded.default_project_id

    owner_member_id = identity.seed_workforce_founder(disposable_cluster, workspace_id, seeded.owner_user_id)
    key_result_id = _seed_objective_and_key_result(disposable_cluster, workspace_id, project_id)

    initiative = _create_and_approve_initiative(
        company, token, workspace_id, project_id, key_result_id, owner_member_id
    )

    pilot = _transition(
        company, token, workspace_id, project_id, initiative["id"],
        target_state="PILOT", expected_revision=initiative["revision"], reason_code="PILOT_START",
    )

    _seed_evidence(disposable_cluster, workspace_id, project_id, initiative["id"], owner_member_id)

    validate = _transition(
        company, token, workspace_id, project_id, initiative["id"],
        target_state="VALIDATE", expected_revision=pilot["decision"]["revision"],
        reason_code="VALIDATE_START",
    )

    scale_candidate = _transition(
        company, token, workspace_id, project_id, initiative["id"],
        target_state="SCALE_CANDIDATE",
        expected_revision=validate["decision"]["revision"],
        reason_code="SCALE_READY",
    )

    return {
        "initiative_id": initiative["id"],
        "workspace_id": workspace_id,
        "project_id": project_id,
        "owner_token": token,
        "revision_after_scale_candidate": scale_candidate["decision"]["revision"],
    }, seeded


def test_scaled_initiative_promotion_reaches_cosa_via_real_outbox_relay(
    real_cosa_stack, disposable_cluster
) -> None:
    ctx, _seeded = _promote_to_scale_candidate(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company

    # Drive the durable relay for real — this is the exact endpoint the
    # `outbox-relay` cron calls every minute in production (Task 6/13).
    r = company.post("/events/relay/tick")
    assert r.status_code == 200, r.text

    deadline = time.monotonic() + _TIMEOUT_S
    snapshot = None
    while time.monotonic() < deadline:
        snapshot = _query_snapshot(disposable_cluster, ctx["workspace_id"], ctx["initiative_id"])
        if snapshot is not None:
            break
        time.sleep(1.0)

    if snapshot is None:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(disposable_cluster.workspace_app_url, connect_timeout=10)
        with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT event_id, status, attempt_count, last_error FROM integration.event_outbox "
                "WHERE aggregate_type = 'ai_initiative' AND aggregate_id = %s",
                (ctx["initiative_id"],),
            )
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        pytest.fail(f"COSA never durably stored the promotion snapshot; outbox rows: {rows}")
    assert snapshot["lifecycle_state"] == "SCALE_CANDIDATE"
    assert snapshot["project_id"] == ctx["project_id"]
    assert snapshot["initiative_revision"] == ctx["revision_after_scale_candidate"]

    # Restart the COSA API + worker processes and confirm the durably-stored
    # snapshot survives — this is the actual "process restart/recovery"
    # proof the plan's Task 13 requires (spec §15 acceptance #9).
    if hasattr(real_cosa_stack, "restart_api_and_worker"):
        real_cosa_stack.restart_api_and_worker(disposable_cluster)

    snapshot_after_restart = _query_snapshot(disposable_cluster, ctx["workspace_id"], ctx["initiative_id"])
    assert snapshot_after_restart is not None, "promotion snapshot lost after restart"
    assert snapshot_after_restart["lifecycle_state"] == "SCALE_CANDIDATE"
    assert snapshot_after_restart["decision_hash"] == snapshot["decision_hash"]


def test_transition_denies_stale_revision_and_cross_workspace_token(
    real_cosa_stack, disposable_cluster
) -> None:
    company = real_cosa_stack.company

    seeded_a = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    seeded_b = identity.seed_workspace(real_cosa_stack, disposable_cluster)

    owner_member_id = identity.seed_workforce_founder(
        disposable_cluster, seeded_a.workspace_id, seeded_a.owner_user_id
    )
    key_result_id = _seed_objective_and_key_result(
        disposable_cluster, seeded_a.workspace_id, seeded_a.default_project_id
    )
    initiative = _create_and_approve_initiative(
        company, seeded_a.owner_token, seeded_a.workspace_id, seeded_a.default_project_id,
        key_result_id, owner_member_id,
    )

    # Workspace B's token can never see or transition workspace A's initiative.
    r = company.post(
        f"/operations/projects/{seeded_a.default_project_id}/ai-initiatives/{initiative['id']}/transition",
        json={"targetState": "PILOT", "expectedRevision": initiative["revision"], "reasonCode": "PILOT_START"},
        token=seeded_b.owner_token,
        workspace_id=seeded_b.workspace_id,
    )
    assert r.status_code >= 400, "cross-workspace transition must be denied"

    # A stale expectedRevision must be rejected as a revision conflict, not
    # silently coerced to the current one.
    r = company.post(
        f"/operations/projects/{seeded_a.default_project_id}/ai-initiatives/{initiative['id']}/transition",
        json={
            "targetState": "PILOT",
            "expectedRevision": initiative["revision"] + 99,
            "reasonCode": "PILOT_START",
        },
        token=seeded_a.owner_token,
        workspace_id=seeded_a.workspace_id,
    )
    assert r.status_code == 409, f"expected 409 revision conflict, got {r.status_code}: {r.text}"
