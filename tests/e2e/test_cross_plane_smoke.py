"""Tầng 1 — cross-plane smoke. 4 vùng thật, model=fake, chặn PR.

KHÔNG mock, KHÔNG skip, KHÔNG transport giả (scripts/check_mvp_e2e_purity.py).
Thiếu tiền đề -> fixture pytest.fail, không skip.

File này sẽ chứa S1–S4; hiện chỉ có S1 (auth + cô lập tenant).
"""

from __future__ import annotations

import pytest

from tests.e2e.scenarios import (
    auth_tenant_isolation,
    capability_governance,
    dispatch_worker_result,
    outbox_relay,
    policy_snapshot_tenant,
)
from tests.e2e.seed import entitlement, identity

# Toàn bộ file cần Encore CLI + disposable Postgres cluster + PGPASSWORD —
# chỉ job `e2e-cross-plane-smoke` cung cấp. Loại khỏi `e2e-golden-path` /
# `make e2e-test` bằng `-m "not cross_plane"`.
pytestmark = pytest.mark.cross_plane


def test_s1_auth_tenant_isolation(real_cosa_stack, disposable_cluster) -> None:
    # `seed_workspace` cần `cluster` để INSERT hàng `core.workspace_memberships`
    # cho member (xem tests/e2e/seed/identity.py::add_member).
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    auth_tenant_isolation.run(real_cosa_stack, seeded)


def test_s2_dispatch_worker_result(real_cosa_stack, disposable_cluster) -> None:
    # S2: apps/cosa lên lịch task "run" durable ở control-plane cosa → tiến
    # trình worker THẬT claim + chạy → run_events thật trong agent DB + signal
    # projection idempotent sang company (workspace DB).
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    dispatch_worker_result.run(real_cosa_stack, seeded, disposable_cluster)


def test_s3_capability_governance(real_cosa_stack, disposable_cluster) -> None:
    # S3: entitlement `cosa.workspace_agent_policy` ghi thật cross-plane (keyed
    # theo workspace company); biên auth apps/cosa trước capability pipeline;
    # governance path FAIL CLOSED khi policy snapshot không lấy được (B5) — kể
    # cả khi đã có hàng ALLOW, run vẫn `run.failed{policy_snapshot_unavailable}`,
    # không ngầm execute capability.
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    capability_governance.run(real_cosa_stack, seeded, disposable_cluster)


def test_s4_outbox_relay(real_cosa_stack, disposable_cluster) -> None:
    # S4: mutation company (`POST /operations/tasks`) ghi domain event vào
    # `integration.event_outbox` cùng transaction → `POST /events/relay/tick`
    # ký HMAC và đẩy sang apps/cosa `/agent/internal/events` → INSERT idempotent
    # vào `event_inbox` (agent DB), duplicate delivery không tạo hàng thứ hai.
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    outbox_relay.run(real_cosa_stack, seeded, disposable_cluster)


def test_s7_policy_snapshot_tenant(real_cosa_stack, disposable_cluster) -> None:
    # S7: cô lập tenant của policy snapshot. `register_user` + `login` mint cosa
    # platform token THẬT (qua gateway `verifyPlatformToken`); 3 workspace company
    # với nội dung `cosa.workspace_agent_policy` khác nhau (operations / finance /
    # không grant). B5-independent: gateway auth gate + fail-closed tại chặng
    # verify membership cross-plane. Nhánh 200 (cô lập `rules` theo tenant qua
    # wire) là DORMANT tới khi cầu nối token cosa<->company landed — xem docstring
    # `tests/e2e/scenarios/policy_snapshot_tenant.py`.
    _uid, email, password = identity.register_user(real_cosa_stack.platform.base_url)
    cosa_token = identity.login(real_cosa_stack.platform.base_url, email, password)

    seeded_ops = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    seeded_fin = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    seeded_bare = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    entitlement.grant_entitlement(disposable_cluster, seeded_ops.workspace_id, "operations")
    entitlement.grant_entitlement(disposable_cluster, seeded_fin.workspace_id, "finance")

    policy_snapshot_tenant.run(
        real_cosa_stack,
        disposable_cluster,
        cosa_token,
        seeded_ops,
        seeded_fin,
        seeded_bare,
    )
