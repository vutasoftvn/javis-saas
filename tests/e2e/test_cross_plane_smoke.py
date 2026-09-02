"""Tầng 1 — cross-plane smoke. 4 vùng thật, model=fake, chặn PR.

KHÔNG mock, KHÔNG skip, KHÔNG transport giả (scripts/check_mvp_e2e_purity.py).
Thiếu tiền đề -> fixture pytest.fail, không skip.

File này sẽ chứa S1–S4; hiện chỉ có S1 (auth + cô lập tenant).
"""

from __future__ import annotations

from tests.e2e.scenarios import auth_tenant_isolation
from tests.e2e.seed import identity


def test_s1_auth_tenant_isolation(real_cosa_stack, disposable_cluster) -> None:
    # `seed_workspace` cần `cluster` để INSERT hàng `core.workspace_memberships`
    # cho member (xem tests/e2e/seed/identity.py::add_member).
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    auth_tenant_isolation.run(real_cosa_stack, seeded)
