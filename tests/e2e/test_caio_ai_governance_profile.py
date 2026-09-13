"""E2E Verification for CAIO AI Governance Profile and Executive Role Activation.

Plan: .superpowers/sdd/2026-09-12-caio-ai-governance-profile-and-executive-activation/task-4-brief.md
Mirrors: tests/e2e/test_cdo_data_profile.py (freshest sibling, hardened body-content
assertions) for the Board activation lifecycle part.

This is the most complex E2E in the 8-role executive-advisory-board portfolio: it is
the ONLY role whose real path crosses THREE planes — `services/cosa` (Control Plane,
signs an AI governance snapshot envelope), `services/company` (Business plane, verifies
that signature independently and stores an AI Governance Dossier reference), and the
Board activation lifecycle (also `services/company`).

Cross-plane part: a real `services/cosa` (Encore/TS) process is booted via
`tests/e2e/stack/subprocess_stack.py::boot_cosa_only` against a disposable Postgres
cluster (`tests/e2e/conftest.py::disposable_cluster`, session-scoped, already used by
`real_cosa_stack` in test_ai_compliance_company_http.py). A real
`COSA_CONTROL_DELEGATION_SECRET`-signed delegation token is minted with the SAME
Python helper the real composition root uses
(`apps.cosa.auth.jwt.mint_control_plane_delegation`) — not a hand-rolled JWT — so this
test exercises the exact signing/verification code path production uses, not a
reimplementation of it. `services/company` is booted via the existing
`real_company_service` fixture (`tests/e2e/conftest.py`, session-scoped).

Both processes fall back to the SAME dev-default secrets
(`COSA_CONTROL_DELEGATION_SECRET`, `COSA_AI_GOVERNANCE_SIGNING_SECRET`) whenever the
env var is unset and ENVIRONMENT/APP_ENV is not staging/production (see
`services/cosa/services/token.service.ts` and `apps/cosa/auth/jwt.py`) — this repo's
`.env` does not override either, so the two independently-booted processes agree on
the same secret without this test needing to inject one explicitly.
"""

from __future__ import annotations

import os
import shutil
import time
from collections.abc import Iterator

import httpx
import pytest

from apps.cosa.auth.jwt import mint_control_plane_delegation
from tests.e2e.stack._process import terminate_all
from tests.e2e.stack.disposable_postgres import DisposableCluster
from tests.e2e.stack.subprocess_stack import boot_cosa_only

_SERVICE_TOKEN = os.environ.get(
    "COSA_WORKER_SERVICE_TOKEN",
    "dev-worker-service-token",
)


@pytest.fixture(scope="session")
def real_cosa_service(disposable_cluster: DisposableCluster) -> Iterator[str]:
    """Boot a real `services/cosa` (Encore/TS) process against the shared
    session-scoped `disposable_cluster` (defined in `tests/e2e/conftest.py`,
    already used by `real_cosa_stack`). Fails clearly (does not silently skip)
    if `encore` CLI is missing — mirrors `control_plane_service` in
    `tests/apps/cosa/worker/conftest.py`, the established precedent for
    booting `services/cosa` alone."""
    if not shutil.which("encore"):
        pytest.fail(
            "`encore` CLI not found on PATH — cannot boot a real services/cosa for this "
            "cross-plane E2E gate. Install via https://encore.dev/install.sh instead of "
            "falling back to a mock/fake signer."
        )

    base_url, proc = boot_cosa_only(disposable_cluster)
    assert proc.popen.poll() is None, (
        f"[cosa] process died right after health check went green:\n{proc.tail()}"
    )
    try:
        yield base_url
    finally:
        terminate_all([proc])


def _mint_ai_governance_snapshot(
    cosa_base_url: str,
    *,
    workspace_id: str,
    project_id: str,
    policy_refs: list[dict[str, str]],
    evaluator_refs: list[dict[str, str]],
    sub: str = "founder-a-platform-id",
    role: str = "member",
) -> httpx.Response:
    """Call the REAL `POST /cosa/ai-governance/snapshot` endpoint (Task 1) with
    a REAL `COSA_CONTROL_DELEGATION_SECRET`-signed delegation token minted by
    the same Python helper `apps/cosa`'s composition root uses
    (`mint_control_plane_delegation`) — not a hand-rolled/forged token."""
    token = mint_control_plane_delegation(sub=sub, workspace_id=workspace_id, role=role)
    client = httpx.Client(base_url=cosa_base_url, timeout=15.0)
    return client.post(
        "/cosa/ai-governance/snapshot",
        json={
            "workspaceId": workspace_id,
            "projectId": project_id,
            "policyRefs": policy_refs,
            "evaluatorRefs": evaluator_refs,
        },
        headers={"Authorization": f"Bearer {token}"},
    )


_VALID_POLICY_REFS = [{"id": "model_policy.default", "version": "1.0.0", "definitionHash": "a" * 64}]
_VALID_EVALUATOR_REFS = [{"id": "eval.safety_bench", "version": "2.1.0", "definitionHash": "b" * 64}]


@pytest.fixture
def caio_test_env(real_company_service):
    """Setup Workspace A with Project A1, and Workspace B for isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Workspace A (Founder A)
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": f"caio-founder-a-{time.time()}@example.com", "displayName": "Founder A"},
    )
    assert reg_a.status_code == 200, reg_a.text
    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Workspace-Id": ws_a}

    # Project A1
    p_a_resp = client.post(
        "/operations/projects",
        json={"title": "CAIO Alpha Project", "description": "AI governance project for CAIO"},
        headers=headers_a,
    )
    assert p_a_resp.status_code == 200, p_a_resp.text
    proj_a_id = str(p_a_resp.json()["id"])

    # 2. Workspace B (Founder B) for cross-tenant isolation
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": f"caio-founder-b-{time.time()}@example.com", "displayName": "Founder B"},
    )
    assert reg_b.status_code == 200, reg_b.text
    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_b}

    return {
        "base_url": base_url,
        "ws_a": ws_a,
        "headers_a": headers_a,
        "token_a": token_a,
        "proj_a_id": proj_a_id,
        "ws_b": ws_b,
        "headers_b": headers_b,
    }


def test_caio_activation_boundary_and_deliberation(caio_test_env):
    """Test negative gates (inactive ai_governance profile, cross-tenant) and
    positive CAIO activation."""
    base_url = caio_test_env["base_url"]
    headers_a = caio_test_env["headers_a"]
    headers_b = caio_test_env["headers_b"]
    proj_a_id = caio_test_env["proj_a_id"]

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # 1. Verify CAIO is initially UNAVAILABLE when AI Governance profile is only TEMPLATE
    board_resp = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp.status_code == 200, board_resp.text
    roles = board_resp.json()["roles"]
    caio_role = next((r for r in roles if r["roleKey"] == "caio"), None)
    assert caio_role is not None
    assert caio_role["displayState"] == "UNAVAILABLE"
    assert caio_role["runtimeReadiness"] == "READY"
    assert caio_role["requiredProfileKey"] == "ai_governance"

    # 2. Attempt to activate CAIO directly before AI Governance profile is ACTIVE -> must FAIL
    early_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/caio/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert early_act.status_code in (400, 412), early_act.text

    # 3. Cross-Tenant Attempt: Workspace B cannot activate or access CAIO on Project A1
    denied_act = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/caio/activate",
        json={"expectedVersion": 1},
        headers=headers_b,
    )
    assert denied_act.status_code in (403, 404), denied_act.text

    # 4. Founder A activates AI Governance profile in Startup Team
    ai_gov_act = client.post(
        f"/operations/projects/{proj_a_id}/startup-team/ai_governance/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert ai_gov_act.status_code == 200, ai_gov_act.text
    ai_gov_data = ai_gov_act.json()
    assert ai_gov_data["displayState"] == "ACTIVE"

    # 5. Check Executive Board: CAIO now transitions to AVAILABLE_NOT_ACTIVATED
    board_resp2 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp2.status_code == 200, board_resp2.text
    caio_role2 = next(r for r in board_resp2.json()["roles"] if r["roleKey"] == "caio")
    assert caio_role2["displayState"] == "AVAILABLE_NOT_ACTIVATED"

    # 6. Founder A explicitly activates CAIO role
    act_caio = client.post(
        f"/operations/projects/{proj_a_id}/executive-roles/caio/activate",
        json={"expectedVersion": 1},
        headers=headers_a,
    )
    assert act_caio.status_code == 200, act_caio.text
    caio_act_data = act_caio.json()
    assert caio_act_data["state"] == "ACTIVE"
    assert caio_act_data["roleKey"] == "caio"

    # 7. Board now reports CAIO as ACTIVE
    board_resp3 = client.get(
        f"/operations/projects/{proj_a_id}/executive-roles",
        headers=headers_a,
    )
    assert board_resp3.status_code == 200, board_resp3.text
    caio_role3 = next(r for r in board_resp3.json()["roles"] if r["roleKey"] == "caio")
    assert caio_role3["displayState"] == "ACTIVE"

    # 8. Create Draft Deliberation and Frame with CAIO selected
    draft_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/draft",
        json={"title": "Should we adopt the new model provider for production traffic?"},
        headers=headers_a,
    )
    assert draft_resp.status_code == 200, draft_resp.text
    delib_id = draft_resp.json()["id"]

    frame_resp = client.post(
        f"/operations/projects/{proj_a_id}/deliberations/{delib_id}/frame",
        json={
            "question": "Do we have enough verified model/evaluator evidence to justify the switch now?",
            "roleKeys": ["caio"],
        },
        headers=headers_a,
    )
    assert frame_resp.status_code == 200, frame_resp.text
    framed_data = frame_resp.json()
    assert framed_data["state"] == "ANALYSIS_QUEUED"
    assert framed_data["activeFrameVersion"] >= 1


def test_signed_snapshot_accepted_into_ai_governance_dossier(caio_test_env, real_cosa_service):
    """Cross-plane happy path (Task 1 -> Task 2): mint a REAL signed AI
    governance snapshot envelope from the real `services/cosa` process, then
    feed it into the real `services/company` AI Governance Dossier create
    endpoint. Asserts the envelope round-trips and Company's independent HMAC
    re-verification accepts it (200)."""
    headers_a = caio_test_env["headers_a"]
    ws_a = caio_test_env["ws_a"]
    proj_a_id = caio_test_env["proj_a_id"]
    base_url = caio_test_env["base_url"]

    snap_resp = _mint_ai_governance_snapshot(
        real_cosa_service,
        workspace_id=ws_a,
        project_id=proj_a_id,
        policy_refs=_VALID_POLICY_REFS,
        evaluator_refs=_VALID_EVALUATOR_REFS,
    )
    assert snap_resp.status_code == 200, snap_resp.text
    envelope = snap_resp.json()
    assert envelope["status"] == "VERIFIED"
    assert envelope["signature"]
    assert envelope["workspaceId"] == ws_a
    assert envelope["projectId"] == proj_a_id

    client = httpx.Client(base_url=base_url, timeout=15.0)
    dossier_resp = client.post(
        "/operations/ai-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "snapshot": envelope,
            "reasonCode": "SNAPSHOT_INGESTED",
        },
        headers=headers_a,
    )
    assert dossier_resp.status_code == 200, dossier_resp.text
    dossier = dossier_resp.json()
    assert dossier["revision"] == 1
    assert dossier["status"] == "DRAFT"
    assert dossier["policy"][0]["id"] == "model_policy.default"
    assert dossier["evaluators"][0]["id"] == "eval.safety_bench"

    # Founder A can read the dossier back on Project A1.
    read_resp = client.get(
        f"/operations/projects/{proj_a_id}/ai-governance-dossier",
        headers=headers_a,
    )
    assert read_resp.status_code == 200, read_resp.text
    assert read_resp.json()["dossierId"] == dossier["dossierId"]


def test_tampered_and_unsigned_snapshot_rejected(caio_test_env, real_cosa_service):
    """Cross-plane negative path: (1) a snapshot whose signature no longer
    matches its content (tampered after minting) must be rejected with
    `failed_precondition` and a body-content marker naming the specific
    unverifiable reason; (2) a snapshot missing the `signature` field entirely
    (never signed) must be rejected with `invalid_argument` and a
    body-content marker. Real HTTP status codes only — no invented string
    error codes."""
    headers_a = caio_test_env["headers_a"]
    ws_a = caio_test_env["ws_a"]
    proj_a_id = caio_test_env["proj_a_id"]
    base_url = caio_test_env["base_url"]

    snap_resp = _mint_ai_governance_snapshot(
        real_cosa_service,
        workspace_id=ws_a,
        project_id=proj_a_id,
        policy_refs=_VALID_POLICY_REFS,
        evaluator_refs=_VALID_EVALUATOR_REFS,
    )
    assert snap_resp.status_code == 200, snap_resp.text
    envelope = snap_resp.json()

    client = httpx.Client(base_url=base_url, timeout=15.0)

    # (1) Tampered: flip the definitionHash after signing — signature no
    # longer matches the envelope content, so Company's independent
    # `verifyAiGovernanceSnapshotSignature` must reject it.
    tampered = dict(envelope)
    tampered["policy"] = [{**envelope["policy"][0], "definitionHash": "c" * 64}]
    tampered_resp = client.post(
        "/operations/ai-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "snapshot": tampered,
            "reasonCode": "SNAPSHOT_INGESTED",
        },
        headers=headers_a,
    )
    assert tampered_resp.status_code in (400, 412), tampered_resp.text
    tampered_body = tampered_resp.json()
    assert tampered_body.get("code") == "failed_precondition", tampered_resp.text
    assert "AI_GOVERNANCE_SNAPSHOT_UNVERIFIABLE" in tampered_body.get("message", ""), tampered_resp.text

    # (2) Unsigned: strip the signature field entirely — never went through
    # the real signing endpoint at all. Note: `signature` is a required
    # (non-optional) field on the Encore-typed `AiGovernanceSnapshotDraft`
    # request body, so Encore's own request decoder rejects a missing field
    # BEFORE the request ever reaches the service's own
    # `AI_GOVERNANCE_DOSSIER_SHAPE_INVALID` validation — this mirrors the
    # documented finding in test_cdo_data_profile.py for the embedding-vector
    # rejection: the typed HTTP contract itself is the first fail-closed gate,
    # a real behavior worth asserting rather than a gap to work around.
    unsigned = dict(envelope)
    del unsigned["signature"]
    unsigned_resp = client.post(
        "/operations/ai-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "snapshot": unsigned,
            "reasonCode": "SNAPSHOT_INGESTED",
        },
        headers=headers_a,
    )
    assert unsigned_resp.status_code == 400, unsigned_resp.text
    unsigned_body = unsigned_resp.json()
    assert unsigned_body.get("code") == "invalid_argument", unsigned_resp.text
    assert "missing field signature" in unsigned_body.get("message", ""), unsigned_resp.text


def test_ai_governance_dossier_is_project_and_workspace_isolated(caio_test_env, real_cosa_service):
    """Founder A creates an AI Governance Dossier on Project A1 using a real
    signed snapshot; Workspace B cannot read it."""
    headers_a = caio_test_env["headers_a"]
    headers_b = caio_test_env["headers_b"]
    ws_a = caio_test_env["ws_a"]
    proj_a_id = caio_test_env["proj_a_id"]
    base_url = caio_test_env["base_url"]

    snap_resp = _mint_ai_governance_snapshot(
        real_cosa_service,
        workspace_id=ws_a,
        project_id=proj_a_id,
        policy_refs=_VALID_POLICY_REFS,
        evaluator_refs=_VALID_EVALUATOR_REFS,
    )
    assert snap_resp.status_code == 200, snap_resp.text
    envelope = snap_resp.json()

    client = httpx.Client(base_url=base_url, timeout=15.0)
    create_resp = client.post(
        "/operations/ai-governance-dossiers",
        json={
            "projectId": proj_a_id,
            "snapshot": envelope,
            "reasonCode": "SNAPSHOT_INGESTED",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 200, create_resp.text
    dossier = create_resp.json()

    # Founder A can read it back on Project A1.
    read_a_resp = client.get(
        f"/operations/projects/{proj_a_id}/ai-governance-dossier",
        headers=headers_a,
    )
    assert read_a_resp.status_code == 200, read_a_resp.text
    assert read_a_resp.json()["dossierId"] == dossier["dossierId"]

    # Workspace B (a different tenant) cannot read the dossier on Project A1.
    read_b_resp = client.get(
        f"/operations/projects/{proj_a_id}/ai-governance-dossier",
        headers=headers_b,
    )
    assert read_b_resp.status_code in (403, 404), read_b_resp.text
    # Không chỉ kiểm tra status code chung chung — xác nhận đúng loại từ chối
    # là "project không thuộc workspace" (permission_denied), không phải một
    # lỗi 4xx bất kỳ khác vô tình khớp status code.
    read_b_body = read_b_resp.json()
    assert read_b_body.get("code") == "permission_denied", read_b_resp.text
    assert "PROJECT_ACCESS_DENIED" in read_b_body.get("message", ""), read_b_resp.text


def test_cosa_snapshot_endpoint_rejects_foreign_workspace_delegation(caio_test_env, real_cosa_service):
    """Task 1's own guarantee, re-verified end-to-end through the real running
    process (not just Task 1's own unit tests): a real
    `COSA_CONTROL_DELEGATION_SECRET`-signed token scoped to workspace B cannot
    mint a snapshot claiming to be for workspace A."""
    ws_a = caio_test_env["ws_a"]
    ws_b = caio_test_env["ws_b"]

    resp = _mint_ai_governance_snapshot(
        real_cosa_service,
        workspace_id=ws_a,
        project_id=caio_test_env["proj_a_id"],
        policy_refs=_VALID_POLICY_REFS,
        evaluator_refs=_VALID_EVALUATOR_REFS,
        sub="founder-b-platform-id",
        role="member",
    )
    # sanity: same-workspace token succeeds (already covered by the happy-path
    # test above) — this test only forges the delegation's own workspace scope
    # to be ws_b while requesting a snapshot for ws_a.
    del resp

    token_resp = httpx.Client(base_url=real_cosa_service, timeout=15.0).post(
        "/cosa/ai-governance/snapshot",
        json={
            "workspaceId": ws_a,
            "projectId": caio_test_env["proj_a_id"],
            "policyRefs": _VALID_POLICY_REFS,
            "evaluatorRefs": _VALID_EVALUATOR_REFS,
        },
        headers={
            "Authorization": f"Bearer {mint_control_plane_delegation(sub='founder-b-platform-id', workspace_id=ws_b, role='member')}"
        },
    )
    assert token_resp.status_code in (401, 403), token_resp.text
    body = token_resp.json()
    assert body.get("code") == "permission_denied", token_resp.text
