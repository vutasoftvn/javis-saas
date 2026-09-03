"""Golden-path E2E runner — chạy lại thư viện scenario với target NGOÀI.

Khác `test_cross_plane_smoke.py` (Tier-1, boot 4 process subprocess + Postgres
disposable, mang marker `cross_plane` → bị `-m "not cross_plane"` loại khỏi job
`e2e-golden-path`), file này KHÔNG boot gì. Nó chỉ chạy KHI cả ba biến
`E2E_BASE_URL_COMPANY` / `_COSA` / `_API` được set — tức khi một stack 4 vùng đã
chạy sẵn ở ngoài (`docker compose --profile e2e` do `scripts/e2e/run-golden-path.sh`
dựng, hoặc staging). Không marker `cross_plane` → job `e2e-golden-path` nhặt nó.

Guard `pytest.skip(allow_module_level=True)` ở đầu module LÀ hợp lệ ở đây:
`scripts/check_mvp_e2e_purity.py::run_check` chỉ glob `test_mvp_*.py`,
`test_cross_plane_smoke.py`, `scenarios/*.py`, `stack/*.py`, `seed/*.py` — KHÔNG
đụng `test_golden_path.py`. (Đã xác nhận `_CROSS_PLANE_GLOBS`.)

Scenario chạy: **S1** (`auth_tenant_isolation`), **S4** (`outbox_relay`), **S7**
(`policy_snapshot_tenant`) — cả ba đều B5-independent (xem
`docs/testing/cross-plane-e2e.md`). BỎ QUA:

- **S2** (`dispatch_worker_result`) / **S3** (`capability_governance`): nhánh
  `run.completed` phụ thuộc cầu nối delegation token cosa↔company (bug B5,
  `ADR-COSA-DELEGATION-002`). Nhánh `run.failed` fail-closed của chúng cần
  `DisposableCluster` scope theo `run_id` để đọc `agent.runs` / `agent.run_events`
  — thứ mà bộ DSN của stack ngoài (dùng chung, không per-run) không cấp được.
- **S5 / S6 / S8 / P4-live (DeepSeek thật)**: follow-up, xem plan
  `docs/superpowers/plans/2026-09-02-cross-plane-e2e-harness.md` Task 17.

`DisposableCluster` không tồn tại với target ngoài (DB là DB dùng chung của
stack, không tạo/drop per-run). `ExternalClusterDsns` bên dưới là bộ giữ DSN
tối thiểu có ĐÚNG các thuộc tính mà S1/S4/S7 + seed kit đọc
(`workspace_app_url`, `agent_app_url`, `cosa_app_url`), map thẳng từ ba biến
`WORKSPACE_DATABASE_URL` / `AGENT_DATABASE_URL` / `COSA_DATABASE_URL` mà
`run-golden-path.sh` (`source .env.e2e`) export vào môi trường pytest.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pytest

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.scenarios import (
    auth_tenant_isolation,
    outbox_relay,
    policy_snapshot_tenant,
)
from tests.e2e.seed import entitlement, identity

_URLS = {k: os.environ.get(f"E2E_BASE_URL_{k}", "").strip() for k in ("COMPANY", "COSA", "API")}
_URLS_SET_COUNT = sum(1 for v in _URLS.values() if v)

# Cả BA biến hoặc KHÔNG biến nào — đây là guard hợp lệ duy nhất. Set thiếu (1
# hoặc 2 trong 3) là lỗi cấu hình của caller (`run-golden-path.sh` đã đổi trigger
# external-branch để yêu cầu đủ cả ba — xem I-2 review round), không phải điều
# kiện skip hợp lệ: skip im lặng ở đây từng khiến job báo xanh dù 3 test golden
# path chưa chạy gì cả ("a skipped test is not a green release gate").
if _URLS_SET_COUNT == 0:
    pytest.skip(
        "golden-path needs E2E_BASE_URL_COMPANY/_COSA/_API",
        allow_module_level=True,
    )
elif _URLS_SET_COUNT < 3:
    pytest.fail(
        "partial E2E_BASE_URL_* set (need all 3 or none): "
        f"COMPANY={_URLS['COMPANY'] or '<unset>'} COSA={_URLS['COSA'] or '<unset>'} API={_URLS['API'] or '<unset>'}",
        pytrace=False,
    )


def _libpq_dsn(raw: str) -> str:
    """Hạ scheme SQLAlchemy `postgresql+asyncpg://` về libpq thuần cho psycopg2.

    `.env.e2e` khai báo `AGENT_DATABASE_URL=postgresql+asyncpg://...` (driver bất
    đồng bộ của packages/agent). Seed kit / scenario S4 dùng psycopg2 (đồng bộ)
    nên phải bỏ hậu tố driver. `cosa` / `workspace` URL vốn đã là libpq thuần.
    """
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://", "postgresql+psycopg2://"):
        if raw.startswith(prefix):
            return "postgresql://" + raw[len(prefix) :]
    return raw


@dataclass
class ExternalClusterDsns:
    """Thay `DisposableCluster` khi chạy với stack NGOÀI.

    S1/S4/S7 + seed kit chỉ đọc ba thuộc tính DSN:

    | thuộc tính          | bảng chạm tới                                   | biến nguồn              |
    |---------------------|------------------------------------------------|-------------------------|
    | `workspace_app_url` | `core.workspace_memberships`, `integration.event_outbox` | `WORKSPACE_DATABASE_URL` |
    | `agent_app_url`     | `event_inbox`                                   | `AGENT_DATABASE_URL`    |
    | `cosa_app_url`      | `cosa.workspace_agent_policy`, `cosa.workspaces`, `cosa.users` | `COSA_DATABASE_URL`     |

    (Các thuộc tính `*_migrator_url` / `run_id` của `DisposableCluster` KHÔNG
    được scenario nào trong S1/S4/S7 dùng — cố ý không expose ở đây.)
    """

    workspace_app_url: str
    agent_app_url: str
    cosa_app_url: str

    @classmethod
    def from_env(cls) -> ExternalClusterDsns:
        pairs = {
            "workspace_app_url": "WORKSPACE_DATABASE_URL",
            "agent_app_url": "AGENT_DATABASE_URL",
            "cosa_app_url": "COSA_DATABASE_URL",
        }
        resolved: dict[str, str] = {}
        missing: list[str] = []
        for attr, env_name in pairs.items():
            value = os.environ.get(env_name, "").strip()
            if not value:
                missing.append(env_name)
            else:
                resolved[attr] = _libpq_dsn(value)
        if missing:
            pytest.fail(
                "golden-path scenario cần DSN DB của stack ngoài nhưng thiếu: "
                + ", ".join(missing)
                + " — `scripts/e2e/run-golden-path.sh` phải `source .env.e2e` (set -a) "
                "để export chúng vào môi trường pytest."
            )
        return cls(**resolved)


@pytest.fixture(scope="module")
def stack() -> MvpStack:
    return MvpStack.from_base_urls(
        company=_URLS["COMPANY"],
        platform=_URLS["COSA"],
        agent=_URLS["API"],
        apps_cosa=_URLS["API"],
        worker_health_url=f"{_URLS['API']}/healthz",
    )


@pytest.fixture(scope="module")
def cluster() -> ExternalClusterDsns:
    return ExternalClusterDsns.from_env()


def test_golden_s1_auth_tenant_isolation(stack: MvpStack, cluster: ExternalClusterDsns) -> None:
    # S1: đăng ký/đăng nhập thật qua services/company → 2 workspace độc lập →
    # cô lập tenant qua wire (200 ở workspace mình, 404 cross-tenant, 401 anon,
    # 403 thiếu membership). Toàn bộ HTTP thật; `cluster.workspace_app_url` chỉ
    # dùng để INSERT hàng `core.workspace_memberships` cho member seed.
    seeded = identity.seed_workspace(stack, cluster, with_member=True)
    auth_tenant_isolation.run(stack, seeded)


def test_golden_s4_outbox_relay(stack: MvpStack, cluster: ExternalClusterDsns) -> None:
    # S4: `POST /operations/tasks` ghi `integration.event_outbox` cùng transaction
    # → `POST /events/relay/tick` ký HMAC, đẩy sang apps/cosa `/agent/internal/events`
    # → INSERT idempotent `event_inbox` (agent DB). Deadline loop, giao trùng
    # không tạo hàng thứ hai.
    seeded = identity.seed_workspace(stack, cluster)
    outbox_relay.run(stack, seeded, cluster)


def test_golden_s7_policy_snapshot_tenant(stack: MvpStack, cluster: ExternalClusterDsns) -> None:
    # S7: `GET /platform/auth/me/agent-policy-snapshot` — gateway auth gate
    # (401 khi thiếu/rác bearer) + FAIL-CLOSED tại hop verify membership
    # cross-plane (cosa platform token hợp lệ → 403 `permission_denied` đồng nhất
    # trên 3 workspace có nội dung policy khác nhau, KHÔNG rò "rỗng = allow").
    # Nhánh 200 (cô lập `rules` theo tenant) là DORMANT tới khi cầu nối B5 landed.
    _uid, email, password = identity.register_user(stack.platform.base_url)
    cosa_token = identity.login(stack.platform.base_url, email, password)

    seeded_ops = identity.seed_workspace(stack, cluster)
    seeded_fin = identity.seed_workspace(stack, cluster)
    seeded_bare = identity.seed_workspace(stack, cluster)
    entitlement.grant_entitlement(cluster, seeded_ops.workspace_id, "operations")
    entitlement.grant_entitlement(cluster, seeded_fin.workspace_id, "finance")

    policy_snapshot_tenant.run(
        stack,
        cluster,
        cosa_token,
        seeded_ops,
        seeded_fin,
        seeded_bare,
    )
