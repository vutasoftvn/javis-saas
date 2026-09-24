"""Helper dùng chung cho E2E advisor board: Board (workspace + Project deployment + office role +
compliance) trên stack 4 plane thật. Không mock transport."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx

from apps.cosa.agents.catalog import CATALOG_BY_PROFILE
from apps.cosa.agents.executive_advisor_roles_generated import EXECUTIVE_ROLE_CATALOG
from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity

FAKE_ANALYSIS = {
    "conclusion": "Runway 10 tháng nếu giữ nguyên burn rate.",
    "options": [{"title": "Giữ nguyên chi tiêu", "trade_off": "Không cần huy động thêm ngay"}],
    "evidence_claims": [{"claim": "Cash hiện tại", "source_ref": "object://finance/cash"}],
    "confidence": 0.8,
}
FAKE_TEXT = json.dumps(FAKE_ANALYSIS)
WAIT_S = 60.0


def fetch_one(cluster_url: str, sql: str, params: tuple) -> Any:
    row = fetch_row(cluster_url, sql, params, required=False)
    return row[0] if row else None


def fetch_row(cluster_url: str, sql: str, params: tuple, *, required: bool = True):
    import psycopg2

    conn = psycopg2.connect(cluster_url, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            assert row is not None or not required, "expected a durable row"
            return row
    finally:
        conn.close()


def pin_hashes(frame_pin: dict) -> dict[str, str]:
    from apps.cosa.worker.executive_board_handler import parse_selected_advisor_pin

    pin = parse_selected_advisor_pin(frame_pin)
    return {
        "deployment_pin_hash": pin.deployment.identity_hash(),
        "overlay_pin_hash": pin.overlay.identity_hash(),
    }


def worker_headers(ws: str, run_id: str) -> dict[str, str]:
    # Cùng loại JWT `worker_service` mà stack cấp cho worker thật.
    from tests.e2e.stack.subprocess_stack import _mint_worker_token

    token = _mint_worker_token(run_id)
    return {"X-Workspace-Id": ws, "X-Service-Token": token, "Authorization": f"Bearer {token}"}


def profile_for_role(role_key: str) -> str:
    return EXECUTIVE_ROLE_CATALOG[role_key].required_profile_key


class Board:
    """Workspace + Project mặc định với Workspace Agent của `profile_key` đã deploy vào Project,
    tuỳ chọn kích hoạt office role và compliance APPROVED — đi qua đường HTTP thật."""

    def __init__(
        self,
        stack: MvpStack,
        cluster,
        *,
        profile_key: str = "finance",
        activate_role: str | None = "cfo",
        seed_compliance: bool = True,
        deploy: bool = True,
    ) -> None:
        self.stack = stack
        self.cluster = cluster
        self.company = stack.company
        self.profile_key = profile_key
        self.spec = CATALOG_BY_PROFILE[profile_key].agent_spec
        seeded = identity.seed_workspace(stack, cluster)
        self.seeded = seeded
        self.token = seeded.owner_token
        self.ws = seeded.workspace_id
        self.owner_user_id = seeded.owner_user_id
        self.project_id = str(seeded.default_project_id)
        self.deployment_id: str | None = None
        self.headers = {"Authorization": f"Bearer {self.token}", "X-Workspace-Id": self.ws}
        if profile_key:
            self.activate_profile()
        if deploy:
            self.deploy()
        if activate_role:
            self.activate_role(activate_role)
        if seed_compliance:
            self.seed_compliance()

    def call(self, method: str, path: str, **kw) -> httpx.Response:
        return getattr(self.company, method)(path, token=self.token, workspace_id=self.ws, **kw)

    def activate_profile(self) -> None:
        r = self.call(
            "post",
            f"/operations/projects/{self.project_id}/startup-team/{self.profile_key}/activate",
            json={"expectedVersion": 1},
        )
        assert r.status_code == 200, r.text

    def deploy(self) -> None:
        agent_id = fetch_one(
            self.cluster.workspace_app_url,
            "SELECT id FROM operating.workspace_agents WHERE workspace_id = %s AND agent_asset_id = %s",
            (int(self.ws), self.spec.id),
        )
        assert agent_id is not None, "activating the profile must create a Workspace Agent"
        r = self.call(
            "post",
            f"/operations/projects/{self.project_id}/agent-deployments",
            json={"workspaceAgentId": str(agent_id), "idempotencyKey": f"e2e-deploy-{self.ws}"},
        )
        assert r.status_code == 200, r.text
        self.deployment_id = str(r.json()["id"])

    def activate_role(self, role_key: str, *, expected_version: int = 1) -> httpx.Response:
        r = self.call(
            "post",
            f"/operations/workspaces/{self.ws}/executive-roles/{role_key}/activate",
            json={"expectedVersion": expected_version},
        )
        assert r.status_code == 200, r.text
        return r

    def seed_compliance(self) -> None:
        resp = httpx.post(
            f"{self.company.base_url}/finance-legal/ai-compliance/_e2e/seed",
            json={
                "scenario": "approved",
                "systemKey": self.spec.id,
                "workspaceId": self.ws,
                "founderMemberId": self.owner_user_id,
            },
            timeout=30.0,
        )
        assert resp.status_code == 200, resp.text

    def roles(self) -> dict[str, dict]:
        r = self.call("get", f"/operations/projects/{self.project_id}/executive-roles")
        assert r.status_code == 200, r.text
        return {row["roleKey"]: row for row in r.json()["roles"]}

    def draft(self, title: str = "Advisor board E2E", project_id: str | None = None) -> str:
        r = self.call(
            "post",
            f"/operations/projects/{project_id or self.project_id}/deliberations/draft",
            json={"title": title},
        )
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def frame_raw(
        self, delib_id: str, question: str, roles: list[str], *, project_id: str | None = None
    ) -> httpx.Response:
        return self.call(
            "post",
            f"/operations/projects/{project_id or self.project_id}/deliberations/{delib_id}/frame",
            json={"question": question, "roleKeys": roles, "expectedVersion": 1},
        )

    def frame(self, question: str = "Runway còn bao lâu?", roles=("cfo",)) -> tuple[str, dict]:
        delib_id = self.draft()
        r = self.frame_raw(delib_id, question, list(roles))
        assert r.status_code == 200, r.text
        return delib_id, r.json()

    def deliberation(self, delib_id: str, *, headers: dict | None = None) -> dict:
        r = self.call("get", f"/operations/projects/{self.project_id}/deliberations/{delib_id}")
        assert r.status_code == 200, r.text
        return r.json()

    def callback(self, delib_id: str, body: dict, *, ws: str | None = None) -> httpx.Response:
        return httpx.post(
            f"{self.company.base_url}/internal/operations/projects/{self.project_id}"
            f"/deliberations/{delib_id}/callback",
            json=body,
            headers=worker_headers(ws or self.ws, self.cluster.run_id),
            timeout=20.0,
        )

    def authority(self, delib_id: str, role_key: str) -> httpx.Response:
        return httpx.get(
            f"{self.company.base_url}/internal/operations/projects/{self.project_id}"
            f"/deliberations/{delib_id}/authority",
            params={"roleKey": role_key},
            headers=worker_headers(self.ws, self.cluster.run_id),
            timeout=20.0,
        )

    def completed_callback(
        self, delib_id: str, role_key: str, *, frame_version: int = 1, conclusion: str = "ok"
    ) -> httpx.Response:
        """Callback hoàn tất đúng như worker thật: mang hash 2 pin đọc từ frame đã persist."""
        frame_pin = next(
            p
            for p in self.deliberation(delib_id)["activeFrame"]["selectedRoles"]
            if p["roleKey"] == role_key
        )
        return self.callback(
            delib_id,
            {
                "kind": "executive.analysis.completed.v1",
                "deliberation_id": delib_id,
                "frame_version": frame_version,
                "role_key": role_key,
                "descriptor": {"run_id": f"run_{role_key}_e2e", "conclusion": conclusion},
                **pin_hashes(frame_pin),
            },
        )

    def wait_for_analyses(self, delib_id: str, *, count: int = 1) -> dict:
        deadline = time.monotonic() + WAIT_S
        details: dict = {}
        while time.monotonic() < deadline:
            self.company.post("/events/relay/tick")
            details = self.deliberation(delib_id)
            if len(details.get("analyses") or []) >= count:
                return details
            time.sleep(2.0)
        return details

    def latest_run(self) -> tuple:
        return fetch_row(
            self.cluster.agent_app_url,
            "SELECT run_id, status, error_details::text, final_output::text FROM agent.runs "
            "WHERE workspace_id = %s ORDER BY created_at DESC LIMIT 1",
            (self.ws,),
        )

    def diagnostics(self, delib_id: str) -> str:
        outbox = fetch_one(
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


_STAGES = [
    "P0_DISCOVERY",
    "P1_PROBLEM_VALIDATION",
    "P2_SOLUTION_VALIDATION",
    "P3_BUILD_VALIDATE",
    "P4_GO_TO_MARKET",
    "P5_OPERATE_GROWTH",
]
# Stage tối thiểu để role non-persistent được tư vấn (executive-board-stage-presets.ts).
ROLE_STAGE = {
    "chief_of_staff": "P0_DISCOVERY",
    "cfo": "P0_DISCOVERY",
    "cmo": "P0_DISCOVERY",
    "cpo": "P0_DISCOVERY",
    "coo": "P2_SOLUTION_VALIDATION",
    "vpe": "P2_SOLUTION_VALIDATION",
    "ciso": "P2_SOLUTION_VALIDATION",
    "gc": "P2_SOLUTION_VALIDATION",
    "cdo": "P2_SOLUTION_VALIDATION",
    "caio": "P2_SOLUTION_VALIDATION",
    "cro": "P4_GO_TO_MARKET",
    "cco": "P4_GO_TO_MARKET",
    "chro": "P5_OPERATE_GROWTH",
}


def advance_to(board: Board, stage: str) -> None:
    """Chuyển Project qua từng lifecycle stage thủ công tới `stage` (không gate, không tự động)."""
    state = board.call("get", f"/operations/projects/{board.project_id}/lifecycle/events")
    assert state.status_code == 200, state.text
    current, version = "P0_DISCOVERY", 0
    project = board.call("get", f"/operations/projects/{board.project_id}")
    if project.status_code == 200:
        current = project.json().get("lifecycleStage", current)
        version = project.json().get("stageVersion", version)
    for nxt in _STAGES[_STAGES.index(current) + 1 : _STAGES.index(stage) + 1]:
        r = board.call(
            "patch",
            f"/operations/projects/{board.project_id}/lifecycle",
            json={"toStage": nxt, "expectedStageVersion": version},
        )
        assert r.status_code == 200, r.text
        version = r.json()["stageVersion"]


def run_role_lifecycle(stack: MvpStack, cluster, role_key: str, question: str) -> None:
    """Đường đầy đủ của 1 executive role: profile chưa active -> office chưa kích hoạt được;
    profile active -> office ACTIVE nhưng chưa có deployment; deploy -> stage gate; đúng stage ->
    frame thành công và pin overlay `cosa.executive.<role>`. Cross-tenant bị từ chối."""
    profile = profile_for_role(role_key)
    board = _bare_board(stack, cluster, profile)

    row = board.roles()[role_key]
    assert row["requiredProfileKey"] == profile
    assert row["officeState"] == "UNAVAILABLE"
    assert row["disabledReason"] == "UNDERLYING_PROFILE_UNAVAILABLE"

    # Office chưa kích hoạt được khi profile nền chưa active.
    early = board.call(
        "post",
        f"/operations/workspaces/{board.ws}/executive-roles/{role_key}/activate",
        json={"expectedVersion": 1},
    )
    assert early.status_code in (400, 412), early.text

    # Cross-tenant: Workspace B không đọc/kích hoạt được board của Project A.
    other = identity.seed_workspace(stack, cluster)
    foreign_headers = {"Authorization": f"Bearer {other.owner_token}", "X-Workspace-Id": other.workspace_id}
    foreign = httpx.get(
        f"{board.company.base_url}/operations/projects/{board.project_id}/executive-roles",
        headers=foreign_headers,
        timeout=20.0,
    )
    assert foreign.status_code in (403, 404), foreign.text

    board.activate_profile()
    assert board.roles()[role_key]["officeState"] == "AVAILABLE_NOT_ACTIVATED"

    board.activate_role(role_key)
    row = board.roles()[role_key]
    assert row["officeState"] == "ACTIVE"
    assert row["effectiveState"] == "DEPLOYMENT_INACTIVE"

    delib = board.draft()
    target = ROLE_STAGE[role_key]
    # Thứ tự gate của Company: office -> stage -> deployment.
    if target != "P0_DISCOVERY":
        stage_blocked = board.frame_raw(delib, question, [role_key])
        assert stage_blocked.status_code in (400, 412), stage_blocked.text
        assert "EXECUTIVE_ROLE_STAGE_FORBIDDEN" in stage_blocked.text
        advance_to(board, target)

    blocked = board.frame_raw(delib, question, [role_key])
    assert blocked.status_code in (400, 412), blocked.text
    assert "EXECUTIVE_ROLE_PROJECT_DEPLOYMENT_INACTIVE" in blocked.text

    board.deploy()
    board.seed_compliance()

    framed = board.frame_raw(delib, question, [role_key])
    assert framed.status_code == 200, framed.text
    assert framed.json()["state"] == "ANALYSIS_QUEUED"
    pin = board.deliberation(delib)["activeFrame"]["selectedRoles"][0]
    assert pin["overlay"]["overlaySpecId"] == f"cosa.executive.{role_key}"
    assert pin["deployment"]["profileKey"] == profile
    assert pin["deployment"]["projectAgentDeploymentId"] == board.deployment_id


def _bare_board(stack: MvpStack, cluster, profile: str) -> Board:
    """Board chỉ có workspace + Project mặc định (chưa activate/deploy/office/compliance)."""
    board = Board.__new__(Board)
    seeded = identity.seed_workspace(stack, cluster)
    board.stack, board.cluster, board.company = stack, cluster, stack.company
    board.profile_key = profile
    board.spec = CATALOG_BY_PROFILE[profile].agent_spec
    board.seeded = seeded
    board.token, board.ws = seeded.owner_token, seeded.workspace_id
    board.owner_user_id = seeded.owner_user_id
    board.project_id = str(seeded.default_project_id)
    board.deployment_id = None
    board.headers = {"Authorization": f"Bearer {board.token}", "X-Workspace-Id": board.ws}
    return board
