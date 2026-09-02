"""Tầng 1 — cross-plane smoke. 4 vùng thật, model=fake, chặn PR.

KHÔNG mock, KHÔNG skip, KHÔNG transport giả (scripts/check_mvp_e2e_purity.py).
Thiếu tiền đề -> fixture pytest.fail, không skip.

File này sẽ chứa S1–S4; hiện chỉ có S1 (auth + cô lập tenant).
"""

from __future__ import annotations

from tests.e2e.scenarios import (
    auth_tenant_isolation,
    capability_governance,
    dispatch_worker_result,
)
from tests.e2e.seed import identity


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
