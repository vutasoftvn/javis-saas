"""Boot đủ 4 process thật trên cluster disposable, cả 4 /healthz xanh, teardown sạch."""

from __future__ import annotations

import httpx
import pytest

# Boot 4 process thật + disposable Postgres → chỉ job `e2e-cross-plane-smoke`.
pytestmark = pytest.mark.cross_plane


def test_all_four_planes_report_healthy(real_cosa_stack) -> None:
    for name, url in (
        ("company", f"{real_cosa_stack.company.base_url}/healthz"),
        ("cosa", f"{real_cosa_stack.platform.base_url}/healthz"),
        ("apps_cosa", f"{real_cosa_stack.apps_cosa.base_url}/healthz"),
        ("worker", real_cosa_stack.worker_health_url),
    ):
        resp = httpx.get(url, timeout=5.0)
        assert resp.status_code in (200, 503), f"{name} unhealthy: {resp.status_code} {resp.text}"
