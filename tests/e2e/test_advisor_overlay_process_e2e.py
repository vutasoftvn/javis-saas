"""Advisor overlay process E2E (plan 2026-09-20-governed-advisor-overlay-and-truthful-hub, Task 13).

Company (frame + outbox) -> signed relay -> apps/cosa intake -> control-plane scheduler ->
worker (overlay run qua compliance + model routing, model fake) -> Company callback, trên stack
4 plane thật + PostgreSQL disposable. Không mock transport, không skip.
"""

from __future__ import annotations

import json

import httpx
import pytest

from tests.e2e.advisor_board import (
    FAKE_ANALYSIS,
    FAKE_TEXT,
    Board,
    fetch_one,
    fetch_row,
    pin_hashes,
    worker_headers,
)

pytestmark = pytest.mark.cross_plane


def test_frame_persists_both_pins_and_worker_records_the_same_identities(
    advisor_stack, advisor_cluster
):
    board = Board(advisor_stack, advisor_cluster)
    delib_id, framed = board.frame()
    assert framed["state"] == "ANALYSIS_QUEUED"

    details = board.wait_for_analyses(delib_id)
    assert details.get("analyses"), board.diagnostics(delib_id)

    frame_pin = details["activeFrame"]["selectedRoles"][0]
    assert frame_pin["deployment"]["projectAgentDeploymentId"] == board.deployment_id
    assert frame_pin["deployment"]["specId"] == "cosa.agents.finance"
    assert frame_pin["overlay"]["overlaySpecId"] == "cosa.executive.cfo"
    assert frame_pin["overlay"]["skillPins"], "overlay pin must carry exact skill identities"

    analyses = details["analyses"]
    assert len(analyses) == 1, details
    analysis = analyses[0]
    assert analysis["status"] == "COMPLETED", (analysis, board.latest_run())
    descriptor = analysis["descriptor"]
    assert descriptor["conclusion"] == FAKE_ANALYSIS["conclusion"]
    assert descriptor["execution_pin"]["overlay"]["overlay_spec_hash"] == (
        frame_pin["overlay"]["overlaySpecHash"]
    )
    assert descriptor["execution_pin"]["deployment"]["spec_hash"] == (
        frame_pin["deployment"]["specHash"]
    )
    assert details["state"] == "AWAITING_FOUNDER"

    # Run durable ghi đúng overlay đã chạy (root) và cả 2 pin trong input_payload.
    run_id = descriptor["run_id"]
    root_id, root_hash, payload = fetch_row(
        advisor_cluster.agent_app_url,
        "SELECT root_executable_id, root_definition_hash, input_payload FROM agent.runs "
        "WHERE run_id = %s",
        (run_id,),
    )
    assert root_id == "cosa.executive.cfo"
    assert root_hash == frame_pin["overlay"]["overlaySpecHash"]
    recorded = payload if isinstance(payload, dict) else json.loads(payload)
    assert recorded["advisor_execution"]["project_id"] == board.project_id
    assert recorded["advisor_execution"]["deployment"]["project_agent_deployment_id"] == (
        board.deployment_id
    )


def test_callback_replay_is_idempotent_and_drift_or_conflict_never_overwrites(
    advisor_stack, advisor_cluster
):
    board = Board(advisor_stack, advisor_cluster)
    delib_id, _ = board.frame()
    details = board.wait_for_analyses(delib_id)
    assert details.get("analyses"), board.diagnostics(delib_id)
    analysis = details["analyses"][0]
    assert analysis["status"] == "COMPLETED", (analysis, board.latest_run())
    frame_pin = details["activeFrame"]["selectedRoles"][0]

    url = (
        f"{board.company.base_url}/internal/operations/projects/{board.project_id}"
        f"/deliberations/{delib_id}/callback"
    )
    valid = {
        "kind": "executive.analysis.completed.v1",
        "deliberation_id": delib_id,
        "frame_version": 1,
        "role_key": "cfo",
        "descriptor": analysis["descriptor"],
        **pin_hashes(frame_pin),
    }

    def post(body: dict) -> httpx.Response:
        return httpx.post(url, json=body, headers=worker_headers(board.ws, advisor_cluster.run_id), timeout=20.0)

    # Replay giống hệt: idempotent, trả lại đúng bản ghi cũ.
    replay = post(valid)
    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == analysis["id"]

    # Stale frame / overlay drift / deployment drift đều bị chặn trước idempotency.
    assert post({**valid, "frame_version": 2}).status_code in (400, 409, 412)
    drift_overlay = post({**valid, "overlay_pin_hash": "0" * 64})
    assert drift_overlay.status_code in (400, 412), drift_overlay.text
    assert "OVERLAY_PIN_MISMATCH" in drift_overlay.text
    drift_deployment = post({**valid, "deployment_pin_hash": "1" * 64})
    assert drift_deployment.status_code in (400, 412), drift_deployment.text
    assert "DEPLOYMENT_PIN_MISMATCH" in drift_deployment.text

    # Nội dung khác cho cùng role/frame: từ chối, không ghi đè phân tích đã có.
    conflict = post({**valid, "descriptor": {**analysis["descriptor"], "conclusion": "khác"}})
    assert conflict.status_code in (409, 412), conflict.text
    after = board.deliberation(delib_id)
    assert len(after["analyses"]) == 1
    assert after["analyses"][0]["descriptor"]["conclusion"] == FAKE_ANALYSIS["conclusion"]


def test_project_without_the_deployment_cannot_frame_even_with_an_active_office(
    advisor_stack, advisor_cluster
):
    board = Board(advisor_stack, advisor_cluster)
    other = board.call(
        "post",
        "/operations/projects",
        json={
            "title": "Project without deployment",
            "creationMode": "ONBOARD_EXISTING",
            "initialLifecycleStage": "P0_DISCOVERY",
            "initializationRationale": "E2E: project deliberately has no agent deployment",
        },
    )
    assert other.status_code == 200, other.text
    other_id = str(other.json()["id"])

    draft = board.call(
        "post",
        f"/operations/projects/{other_id}/deliberations/draft",
        json={"title": "No deployment here"},
    )
    assert draft.status_code == 200, draft.text
    frame = board.call(
        "post",
        f"/operations/projects/{other_id}/deliberations/{draft.json()['id']}/frame",
        json={"question": "Can I advise?", "roleKeys": ["cfo"], "expectedVersion": 1},
    )
    assert frame.status_code in (400, 409, 412), frame.text
    assert "EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE" in frame.text


def test_deployment_paused_after_frame_blocks_execution_before_any_model_call(
    advisor_stack, advisor_cluster
):
    board = Board(advisor_stack, advisor_cluster)
    delib_id, _ = board.frame()

    # Founder tạm dừng deployment sau khi frame, trước khi worker kịp chạy. (Chưa có route
    # public pause cho deployment nên đổi trạng thái trực tiếp ở DB Company — cùng cơ chế seed
    # SQL của identity kit, không phải mock.)
    import psycopg2

    conn = psycopg2.connect(advisor_cluster.workspace_migrator_url, connect_timeout=5)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE operating.project_agent_deployments SET state = 'PAUSED' WHERE id = %s",
                (int(board.deployment_id),),
            )
            assert cur.rowcount == 1
    finally:
        conn.close()

    details = board.wait_for_analyses(delib_id)
    assert details.get("analyses"), board.diagnostics(delib_id)
    analysis = details["analyses"][0]
    assert analysis["status"] == "FAILED", analysis
    assert "AUTHORITY_DENIED" in analysis["descriptor"]["error"], analysis

    runs = fetch_one(
        advisor_cluster.agent_app_url,
        "SELECT count(*) FROM agent.runs WHERE workspace_id = %s",
        (board.ws,),
    )
    assert runs == 0, "a paused deployment must never reach the model"


def test_worker_restart_between_frame_and_execution_still_yields_one_pinned_analysis(
    advisor_stack, advisor_cluster
):
    from tests.e2e.stack.subprocess_stack import restart_api_and_worker

    board = Board(advisor_stack, advisor_cluster)
    delib_id, _ = board.frame()

    # Kill THẬT rồi respawn api + worker (Postgres/scheduler giữ nguyên): frame + outbox +
    # task đã durable nên analysis vẫn phải đến, đúng 1 bản, cùng pin.
    advisor_stack.handles = restart_api_and_worker(
        advisor_stack.handles,
        advisor_cluster,
        extra_py_env={"COSA_FAKE_MODEL_TEXT": FAKE_TEXT},
    )

    details = board.wait_for_analyses(delib_id)
    assert details.get("analyses"), board.diagnostics(delib_id)
    assert len(details["analyses"]) == 1
    analysis = details["analyses"][0]
    assert analysis["status"] == "COMPLETED", (analysis, board.latest_run())
    frame_pin = details["activeFrame"]["selectedRoles"][0]
    assert analysis["descriptor"]["execution_pin"]["overlay"]["overlay_spec_hash"] == (
        frame_pin["overlay"]["overlaySpecHash"]
    )
