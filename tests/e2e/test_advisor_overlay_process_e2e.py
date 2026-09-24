"""Advisor overlay process E2E (plan 2026-09-20-governed-advisor-overlay-and-truthful-hub, Task 13).

Company (frame + outbox) -> signed relay -> apps/cosa intake -> control-plane scheduler ->
worker (overlay run qua compliance + model routing, model fake) -> Company callback, trên stack
4 plane thật + PostgreSQL disposable. Không mock transport, không skip.
"""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
import pytest

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.stack.subprocess_stack import boot_subprocess_stack, teardown_subprocess_stack

pytestmark = pytest.mark.cross_plane

FAKE_ANALYSIS = {
    "conclusion": "Runway 10 tháng nếu giữ nguyên burn rate.",
    "options": [{"title": "Giữ nguyên chi tiêu", "trade_off": "Không cần huy động thêm ngay"}],
    "evidence_claims": [{"claim": "Cash hiện tại", "source_ref": "object://finance/cash"}],
    "confidence": 0.8,
}
_WAIT_S = 60.0


@pytest.fixture(scope="module")
def advisor_stack(disposable_cluster):
    """Stack riêng: worker chạy model fake trả JSON hợp lệ (COSA_FAKE_MODEL_TEXT)."""
    handles = boot_subprocess_stack(
        disposable_cluster, extra_py_env={"COSA_FAKE_MODEL_TEXT": json.dumps(FAKE_ANALYSIS)}
    )
    stack = MvpStack.from_base_urls(
        company=handles.company_url,
        platform=handles.cosa_url,
        agent=handles.apps_cosa_url,
        apps_cosa=handles.apps_cosa_url,
        worker_health_url=handles.worker_health_url,
    )
    stack.handles = handles
    try:
        yield stack
    finally:
        teardown_subprocess_stack(handles)


def _fetch_one(cluster_url: str, sql: str, params: tuple) -> Any:
    import psycopg2

    conn = psycopg2.connect(cluster_url, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


class Board:
    """Workspace + Project đã có finance Workspace Agent được deploy, CFO office ACTIVE và
    compliance APPROVED cho system `cosa.agents.finance` — đường thật, không seed pin tay."""

    def __init__(self, stack: MvpStack, cluster, *, project_id: str | None = None) -> None:
        self.stack = stack
        self.cluster = cluster
        self.company = stack.company
        seeded = identity.seed_workspace(stack, cluster)
        self.token = seeded.owner_token
        self.ws = seeded.workspace_id
        self.owner_user_id = seeded.owner_user_id
        self.project_id = project_id or str(seeded.default_project_id)
        self._prepare()

    def _call(self, method: str, path: str, **kw):
        r = getattr(self.company, method)(path, token=self.token, workspace_id=self.ws, **kw)
        return r

    def _prepare(self) -> None:
        r = self._call(
            "post",
            f"/operations/projects/{self.project_id}/startup-team/finance/activate",
            json={"expectedVersion": 1},
        )
        assert r.status_code == 200, r.text
        agent_id = _fetch_one(
            self.cluster.workspace_app_url,
            "SELECT id FROM operating.workspace_agents WHERE workspace_id = %s AND agent_asset_id = %s",
            (int(self.ws), "cosa.agents.finance"),
        )
        assert agent_id is not None, "activating the finance profile must create a Workspace Agent"
        r = self._call(
            "post",
            f"/operations/projects/{self.project_id}/agent-deployments",
            json={"workspaceAgentId": str(agent_id), "idempotencyKey": f"e2e-deploy-{self.ws}"},
        )
        assert r.status_code == 200, r.text
        self.deployment_id = str(r.json()["id"])
        r = self._call(
            "post",
            f"/operations/workspaces/{self.ws}/executive-roles/cfo/activate",
            json={"expectedVersion": 1},
        )
        assert r.status_code == 200, r.text
        # Compliance APPROVED cho đúng system_key mà worker gửi lên (spec Project deployment).
        seed = httpx.post(
            f"{self.company.base_url}/finance-legal/ai-compliance/_e2e/seed",
            json={
                "scenario": "approved",
                "systemKey": "cosa.agents.finance",
                "workspaceId": self.ws,
                "founderMemberId": self.owner_user_id,
            },
            timeout=30.0,
        )
        assert seed.status_code == 200, seed.text

    def frame(self, question: str = "Runway còn bao lâu?", roles=("cfo",)) -> tuple[str, dict]:
        r = self._call(
            "post",
            f"/operations/projects/{self.project_id}/deliberations/draft",
            json={"title": "Advisor overlay E2E"},
        )
        assert r.status_code == 200, r.text
        delib_id = r.json()["id"]
        r = self._call(
            "post",
            f"/operations/projects/{self.project_id}/deliberations/{delib_id}/frame",
            json={"question": question, "roleKeys": list(roles), "expectedVersion": 1},
        )
        assert r.status_code == 200, r.text
        return delib_id, r.json()

    def deliberation(self, delib_id: str) -> dict:
        r = self._call("get", f"/operations/projects/{self.project_id}/deliberations/{delib_id}")
        assert r.status_code == 200, r.text
        return r.json()

    def wait_for_analyses(self, delib_id: str, *, count: int = 1) -> dict:
        deadline = time.monotonic() + _WAIT_S
        details: dict = {}
        while time.monotonic() < deadline:
            self.company.post("/events/relay/tick")
            details = self.deliberation(delib_id)
            if len(details.get("analyses") or []) >= count:
                return details
            time.sleep(2.0)
        return details

    def latest_run(self) -> tuple:
        return _row(
            self.cluster.agent_app_url,
            "SELECT run_id, status, error_details::text, final_output::text FROM agent.runs "
            "WHERE workspace_id = %s ORDER BY created_at DESC LIMIT 1",
            (self.ws,),
        )

    def diagnostics(self, delib_id: str) -> str:
        """Ngữ cảnh khi timeout: trạng thái outbox + đuôi log các process Python/Company."""
        outbox = _row(
            self.cluster.workspace_app_url,
            "SELECT status FROM integration.event_outbox WHERE aggregate_id = %s "
            "AND event_type = 'executive.deliberation.framed.v1'",
            (delib_id,),
        )
        tails = {
            p.name: p.tail(40)
            for p in (self.stack.handles.procs if self.stack.handles else [])
            if p.name in ("apps_cosa_api", "apps_cosa_worker")
        }
        return f"outbox={outbox}\n" + "\n".join(f"--- {k} ---\n{v}" for k, v in tails.items())


def test_frame_persists_both_pins_and_worker_records_the_same_identities(
    advisor_stack, disposable_cluster
):
    board = Board(advisor_stack, disposable_cluster)
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
    root_id, root_hash, payload = _row(
        disposable_cluster.agent_app_url,
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


def _row(cluster_url: str, sql: str, params: tuple) -> tuple:
    import psycopg2

    conn = psycopg2.connect(cluster_url, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            assert row is not None, "expected a durable row"
            return row
    finally:
        conn.close()


def _pin_hashes(frame_pin: dict) -> dict[str, str]:
    from apps.cosa.worker.executive_board_handler import parse_selected_advisor_pin

    pin = parse_selected_advisor_pin(frame_pin)
    return {
        "deployment_pin_hash": pin.deployment.identity_hash(),
        "overlay_pin_hash": pin.overlay.identity_hash(),
    }


def _worker_headers(ws: str, run_id: str) -> dict[str, str]:
    # Cùng loại JWT `worker_service` mà stack cấp cho worker thật (Company verify bằng
    # WORKER_SERVICE_JWT_SECRET), không phải token dev mặc định.
    from tests.e2e.stack.subprocess_stack import _mint_worker_token

    token = _mint_worker_token(run_id)
    return {
        "X-Workspace-Id": ws,
        "X-Service-Token": token,
        "Authorization": f"Bearer {token}",
    }


def test_callback_replay_is_idempotent_and_drift_or_conflict_never_overwrites(
    advisor_stack, disposable_cluster
):
    board = Board(advisor_stack, disposable_cluster)
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
        **_pin_hashes(frame_pin),
    }

    def post(body: dict) -> httpx.Response:
        return httpx.post(url, json=body, headers=_worker_headers(board.ws, disposable_cluster.run_id), timeout=20.0)

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
    advisor_stack, disposable_cluster
):
    board = Board(advisor_stack, disposable_cluster)
    other = board._call(
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

    draft = board._call(
        "post",
        f"/operations/projects/{other_id}/deliberations/draft",
        json={"title": "No deployment here"},
    )
    assert draft.status_code == 200, draft.text
    frame = board._call(
        "post",
        f"/operations/projects/{other_id}/deliberations/{draft.json()['id']}/frame",
        json={"question": "Can I advise?", "roleKeys": ["cfo"], "expectedVersion": 1},
    )
    assert frame.status_code in (400, 409, 412), frame.text
    assert "EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE" in frame.text


def test_deployment_paused_after_frame_blocks_execution_before_any_model_call(
    advisor_stack, disposable_cluster
):
    board = Board(advisor_stack, disposable_cluster)
    delib_id, _ = board.frame()

    # Founder tạm dừng deployment sau khi frame, trước khi worker kịp chạy. (Chưa có route
    # public pause cho deployment nên đổi trạng thái trực tiếp ở DB Company — cùng cơ chế seed
    # SQL của identity kit, không phải mock.)
    import psycopg2

    conn = psycopg2.connect(disposable_cluster.workspace_migrator_url, connect_timeout=5)
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

    runs = _fetch_one(
        disposable_cluster.agent_app_url,
        "SELECT count(*) FROM agent.runs WHERE workspace_id = %s",
        (board.ws,),
    )
    assert runs == 0, "a paused deployment must never reach the model"


def test_worker_restart_between_frame_and_execution_still_yields_one_pinned_analysis(
    advisor_stack, disposable_cluster
):
    from tests.e2e.stack.subprocess_stack import restart_api_and_worker

    board = Board(advisor_stack, disposable_cluster)
    delib_id, _ = board.frame()

    # Kill THẬT rồi respawn api + worker (Postgres/scheduler giữ nguyên): frame + outbox +
    # task đã durable nên analysis vẫn phải đến, đúng 1 bản, cùng pin.
    advisor_stack.handles = restart_api_and_worker(
        advisor_stack.handles,
        disposable_cluster,
        extra_py_env={"COSA_FAKE_MODEL_TEXT": json.dumps(FAKE_ANALYSIS)},
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
